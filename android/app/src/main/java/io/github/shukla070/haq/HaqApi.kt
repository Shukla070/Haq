package io.github.shukla070.haq

import org.json.JSONArray
import org.json.JSONObject
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/**
 * The Haq server's API (docs/APP_API.md), over plain HttpURLConnection so the app needs no
 * networking library. Every call blocks: run them off the main thread.
 */
class HaqApi(private val baseUrl: String, private val device: String) {

    class ApiError(val code: Int, message: String) : Exception(message)

    fun listCases(): List<CaseCard> = JSONArray(request("GET", "/cases")).objects().map(CaseCard::from)

    fun createCase(story: String): CaseView =
        CaseView.from(JSONObject(request("POST", "/cases", JSONObject().put("story", story))))

    fun getCase(id: String): CaseView = CaseView.from(JSONObject(request("GET", "/cases/$id")))

    fun run(id: String) {
        request("POST", "/cases/$id/run")
    }

    fun answer(id: String, text: String) {
        request("POST", "/cases/$id/answer", JSONObject().put("text", text))
    }

    fun markSent(id: String): CaseView = CaseView.from(JSONObject(request("POST", "/cases/$id/sent", JSONObject())))

    fun delete(id: String) {
        request("DELETE", "/cases/$id")
    }

    /** Uploads one evidence file; the server transcribes it, which takes a few seconds. */
    fun addEvidence(id: String, fileName: String, mimeType: String, bytes: ByteArray, note: String = ""): JSONObject {
        val boundary = "haq-" + UUID.randomUUID()
        val conn = open("POST", "/cases/$id/evidence")
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        val safeName = fileName.replace(Regex("[\"\\r\\n\\\\]"), "_")
        try {
            conn.outputStream.use { out ->
                out.line("--$boundary")
                out.line("Content-Disposition: form-data; name=\"note\"")
                out.line("")
                out.line(note)
                out.line("--$boundary")
                out.line("Content-Disposition: form-data; name=\"file\"; filename=\"$safeName\"")
                out.line("Content-Type: $mimeType")
                out.line("")
                out.write(bytes)
                out.line("")
                out.line("--$boundary--")
            }
            return JSONObject(read(conn))
        } finally {
            conn.disconnect()
        }
    }

    private fun request(method: String, path: String, json: JSONObject? = null): String {
        val conn = open(method, path)
        try {
            if (json != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.outputStream.use { it.write(json.toString().toByteArray()) }
            }
            return read(conn)
        } finally {
            conn.disconnect()
        }
    }

    private fun open(method: String, path: String): HttpURLConnection =
        (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15_000
            readTimeout = 120_000 // evidence uploads wait for transcription
            setRequestProperty("X-Haq-Device", device)
            setRequestProperty("Accept", "application/json")
        }

    private fun read(conn: HttpURLConnection): String {
        val code = conn.responseCode
        val ok = code in 200..299
        val text = (if (ok) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
        if (!ok) {
            val detail = runCatching { JSONObject(text).optString("detail") }.getOrNull()
            throw ApiError(code, detail?.takeIf { it.isNotBlank() } ?: "The server returned an error ($code)")
        }
        return text
    }

    private fun OutputStream.line(text: String) = write((text + "\r\n").toByteArray())
}
