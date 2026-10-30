package io.github.shukla070.haq

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import android.webkit.MimeTypeMap
import androidx.core.content.IntentCompat
import java.io.File
import java.io.FileOutputStream

/**
 * Content shared from another app ("Share to Haq"). Everything is copied into
 * private cache at once, because the sender's URI permission can expire.
 */
object SharedFiles {
    fun collect(context: Context, intent: Intent, existing: List<Attachment>): List<Attachment> {
        val dir = File(context.cacheDir, "shared").apply { mkdirs() }
        val streams = when (intent.action) {
            Intent.ACTION_SEND ->
                listOfNotNull(IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java))
            Intent.ACTION_SEND_MULTIPLE ->
                IntentCompat.getParcelableArrayListExtra(intent, Intent.EXTRA_STREAM, Uri::class.java).orEmpty()
            else -> return emptyList()
        }
        if (streams.isNotEmpty()) {
            return streams.mapIndexedNotNull { index, uri -> copy(context, dir, uri, intent.type, index) }
        }
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)
        if (text.isNullOrBlank()) return emptyList()
        val n = existing.count { it.name.startsWith("Shared message") } + 1
        val name = "Shared message $n.txt"
        val file = unique(dir, name)
        file.writeText(text)
        return listOf(Attachment(Uri.fromFile(file), name, "text/plain"))
    }

    private fun copy(context: Context, dir: File, uri: Uri, mime: String?, index: Int): Attachment? {
        val resolver = context.contentResolver
        val type = resolver.getType(uri) ?: mime ?: "application/octet-stream"
        val ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(type)
        val name = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        }?.substringAfterLast("/")?.trimStart('.').takeUnless { it.isNullOrBlank() }
            ?: "Shared file ${System.currentTimeMillis()}-$index" + (ext?.let { ".$it" } ?: "")
        val file = unique(dir, name)
        try {
            resolver.openInputStream(uri)?.use { input ->
                FileOutputStream(file).use { output -> input.copyTo(output) }
            } ?: return null
        } catch (_: Exception) {
            file.delete()
            return null
        }
        return Attachment(Uri.fromFile(file), name, type)
    }

    /** A free file name in [dir], keeping the display name unless it is taken. */
    private fun unique(dir: File, name: String): File {
        var file = File(dir, name)
        var copy = 2
        while (file.exists()) {
            file = if ("." in name) {
                File(dir, name.substringBeforeLast(".") + " ($copy)." + name.substringAfterLast("."))
            } else {
                File(dir, "$name ($copy)")
            }
            copy++
        }
        return file
    }
}
