package io.github.shukla070.haq

import android.app.Application
import android.content.Intent
import android.net.Uri
import android.util.Log
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

sealed interface Screen {
    data object Home : Screen
    data object NewCase : Screen
    data class Case(val id: String) : Screen
}

/** A file the customer picked, before it is uploaded. */
data class Attachment(val uri: Uri, val name: String, val mimeType: String)

/** Photo-picker names like "36.png": digits plus an extension, nothing else. */
private val NUMBERED_NAME = Regex("^[0-9]+[.]([A-Za-z0-9]+)$")

class HaqViewModel(app: Application) : AndroidViewModel(app) {
    private val api = HaqApi(BuildConfig.SERVER_URL, Device.token(app))
    private var polling: Job? = null

    var screen by mutableStateOf<Screen>(Screen.Home)
        private set
    var cases by mutableStateOf<List<CaseCard>>(emptyList())
        private set
    var current by mutableStateOf<CaseView?>(null)
        private set
    var busy by mutableStateOf<String?>(null) // what the app is doing, for a spinner
        private set
    var error by mutableStateOf<String?>(null)

    /** The new case's attachments. The new-case screen reads this; shares land here too. */
    val newCaseAttachments = mutableStateListOf<Attachment>()

    init {
        // A new view model has no attachments, so recordings and shares left in the cache are orphans.
        listOf("voice", "shared").forEach { File(app.cacheDir, it).deleteRecursively() }
        refresh()
    }

    fun goHome() {
        polling?.cancel()
        current = null
        screen = Screen.Home
        refresh()
    }

    fun newCase() {
        screen = Screen.NewCase
    }

    fun open(id: String) {
        current = null
        screen = Screen.Case(id)
        poll(id)
    }

    fun refresh() = work(null) { cases = io { api.listCases() } }

    fun attachment(uri: Uri): Attachment {
        val resolver = getApplication<Application>().contentResolver
        var name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: uri.lastPathSegment ?: "evidence"
        NUMBERED_NAME.matchEntire(name)?.let { match ->
            val n = newCaseAttachments.count { it.name.startsWith("Screenshot ") } + 1
            name = "Screenshot $n.${match.groupValues[1]}"
        }
        return Attachment(uri, name, resolver.getType(uri) ?: "application/octet-stream")
    }

    fun addAttachment(item: Attachment) {
        newCaseAttachments += item
    }

    fun removeAttachment(item: Attachment) {
        newCaseAttachments -= item
    }

    /** A finished voice-note file becomes an attachment named "Voice note N.m4a". */
    fun addVoiceNote(file: File) {
        val n = newCaseAttachments.count { it.name.startsWith("Voice note ") } + 1
        newCaseAttachments += Attachment(Uri.fromFile(file), "Voice note $n.m4a", "audio/mp4")
    }

    /** Files or text shared from another app become new-case attachments. */
    fun receiveShare(intent: Intent) {
        if (intent.action != Intent.ACTION_SEND && intent.action != Intent.ACTION_SEND_MULTIPLE) return
        work(null) {
            val files = io { SharedFiles.collect(getApplication<Application>(), intent, newCaseAttachments.toList()) }
            files.forEach { newCaseAttachments += it }
            if (files.isNotEmpty()) {
                polling?.cancel()
                current = null
                screen = Screen.NewCase
            } else {
                error = "Haq couldn't read what was shared. Try adding it from a new case instead."
            }
        }
    }

    /** True when the customer can start without typing: they told the story in a voice note. */
    val hasVoiceNote get() = newCaseAttachments.any { it.mimeType.startsWith("audio/") }

    /** Create the case, upload each piece of evidence, start the agent, and watch it work. */
    fun start(story: String) = work("Creating your case") {
        val files = newCaseAttachments.toList()
        val told = story.ifBlank { "I explained what happened in my voice note." }
        val case = io { api.createCase(told) }
        val resolver = getApplication<Application>().contentResolver
        files.forEachIndexed { index, file ->
            busy = "Reading ${file.name} (${index + 1} of ${files.size})"
            val bytes = io { resolver.openInputStream(file.uri)?.use { it.readBytes() } }
                ?: throw IllegalStateException("Could not open ${file.name}")
            io { api.addEvidence(case.id, file.name, file.mimeType, bytes) }
        }
        io { api.run(case.id) }
        io { cleanupCache(files) }
        newCaseAttachments.clear()
        open(case.id)
    }

    fun answer(text: String) = caseAction("Sending your answer") { id ->
        api.answer(id, text)
        null
    }

    /** Answer the open question with a voice note: upload it, then answer naming it. */
    fun answerWithVoice(file: File) = caseAction("Sending your voice note") { id ->
        val result = api.addEvidence(id, "Voice answer.m4a", "audio/mp4", file.readBytes())
        file.delete()
        api.answer(id, "I recorded a voice note with my answer (${result.optString("id")}).")
        null
    }

    fun retry() = caseAction("Starting again") { id ->
        api.run(id)
        null
    }

    fun markSent() = caseAction("Saving") { id -> api.markSent(id) }

    fun delete() = work("Deleting") {
        val id = (screen as? Screen.Case)?.id ?: return@work
        polling?.cancel()
        io { api.delete(id) }
        goHome()
    }

    /** Delete the voice notes and shared files this start uploaded; the server has them now. */
    private fun cleanupCache(files: List<Attachment>) {
        val cache = getApplication<Application>().cacheDir
        val roots = setOf(File(cache, "voice"), File(cache, "shared"))
        files.forEach { item ->
            if (item.uri.scheme != "file") return@forEach
            val file = File(item.uri.path ?: return@forEach)
            val parent = file.parentFile
            if (parent != null && parent in roots) file.delete()
        }
    }

    /** Run an action on the open case, then show its new state (or poll if the agent restarted). */
    private fun caseAction(label: String, action: (String) -> CaseView?) = work(label) {
        val id = (screen as? Screen.Case)?.id ?: return@work
        val updated = io { action(id) }
        if (updated != null) current = updated else poll(id)
    }

    private fun poll(id: String) {
        polling?.cancel()
        polling = viewModelScope.launch {
            while (isActive) {
                try {
                    val view = io { api.getCase(id) }
                    current = view
                    error = null
                    if (!view.running) break
                } catch (e: Exception) {
                    error = message(e)
                }
                delay(2_500)
            }
        }
    }

    private fun work(label: String?, block: suspend () -> Unit) {
        viewModelScope.launch {
            busy = label
            error = null
            try {
                block()
            } catch (e: Exception) {
                error = message(e)
            } finally {
                busy = null
            }
        }
    }

    private fun message(e: Exception): String {
        Log.w("Haq", "request failed", e)
        return when (e) {
            is HaqApi.ApiError -> e.message ?: "Something went wrong"
            is java.io.IOException -> "Can't reach the Haq server. Check your connection and try again."
            else -> e.message ?: "Something went wrong"
        }
    }

    private suspend fun <T> io(block: () -> T): T = withContext(Dispatchers.IO) { block() }
}
