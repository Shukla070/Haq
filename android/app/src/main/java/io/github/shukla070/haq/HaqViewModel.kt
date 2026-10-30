package io.github.shukla070.haq

import android.app.Application
import android.net.Uri
import android.util.Log
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
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

    init {
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
        val name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: uri.lastPathSegment ?: "evidence"
        return Attachment(uri, name, resolver.getType(uri) ?: "application/octet-stream")
    }

    /** Create the case, upload each piece of evidence, start the agent, and watch it work. */
    fun start(story: String, attachments: List<Attachment>) = work("Creating your case") {
        val case = io { api.createCase(story) }
        val resolver = getApplication<Application>().contentResolver
        attachments.forEachIndexed { index, file ->
            busy = "Reading ${file.name} (${index + 1} of ${attachments.size})"
            val bytes = io { resolver.openInputStream(file.uri)?.use { it.readBytes() } }
                ?: throw IllegalStateException("Could not open ${file.name}")
            io { api.addEvidence(case.id, file.name, file.mimeType, bytes) }
        }
        io { api.run(case.id) }
        open(case.id)
    }

    fun answer(text: String) = caseAction("Sending your answer") { id ->
        api.answer(id, text)
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
