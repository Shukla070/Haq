package io.github.shukla070.haq

import org.json.JSONObject

/** What the server sends, as docs/APP_API.md describes it. Only the fields the app uses. */

data class CaseCard(
    val id: String,
    val status: String,
    val running: Boolean,
    val title: String,
    val compensationOwed: Int?,
    val until: String?,
) {
    companion object {
        fun from(json: JSONObject) = CaseCard(
            id = json.getString("id"),
            status = json.getString("status"),
            running = json.optBoolean("running"),
            title = json.str("title") ?: "",
            compensationOwed = json.int("compensation_owed"),
            until = json.str("until"),
        )
    }
}

data class Progress(val current: String, val steps: List<String>)

data class Draft(
    val step: String,
    val recipient: String,
    val subject: String,
    val body: String,
    val nextSteps: String,
)

data class Entitlement(val reversalDueBy: String?, val daysLate: Int?, val compensationOwed: Int?, val stillGrowing: Boolean)

data class Hold(val until: String?, val message: String)

data class Referral(val reason: String, val where: String)

data class Evidence(val id: String, val kind: String, val name: String, val masked: Boolean, val flagged: Boolean, val attachable: Boolean)

data class CaseView(
    val id: String,
    val status: String,
    val running: Boolean,
    val progress: Progress?,
    val evidence: List<Evidence>,
    val entitlement: Entitlement?,
    val draft: Draft?,
    val question: String?,
    val hold: Hold?,
    val referral: Referral?,
) {
    companion object {
        fun from(json: JSONObject) = CaseView(
            id = json.getString("id"),
            status = json.getString("status"),
            running = json.optBoolean("running"),
            progress = json.optJSONObject("progress")?.let { p ->
                Progress(p.str("current") ?: "", p.optJSONArray("steps").strings())
            },
            evidence = json.optJSONArray("evidence").objects().map { e ->
                Evidence(
                    id = e.getString("id"),
                    kind = e.str("kind") ?: "",
                    name = e.str("original_name") ?: e.getString("id"),
                    masked = e.optBoolean("masked"),
                    flagged = (e.optJSONArray("instruction_like")?.length() ?: 0) > 0,
                    attachable = e.optBoolean("attachable"),
                )
            },
            entitlement = json.optJSONObject("entitlement")?.let { e ->
                Entitlement(e.str("reversal_due_by"), e.int("days_late"), e.int("compensation_owed"), e.optBoolean("compensation_still_growing"))
            },
            draft = json.optJSONObject("draft")?.let { d ->
                Draft(
                    step = d.str("step") ?: "",
                    recipient = d.str("recipient") ?: "",
                    subject = d.str("subject") ?: "",
                    body = d.str("body") ?: "",
                    nextSteps = d.str("next_steps") ?: "",
                )
            },
            question = json.optJSONObject("question")?.str("question"),
            hold = json.optJSONObject("hold")?.let { h -> Hold(h.str("until"), h.str("message") ?: "") },
            referral = json.optJSONObject("referral")?.let { r -> Referral(r.str("reason") ?: "", r.str("where") ?: "") },
        )
    }
}

// org.json turns JSON null into the string "null" and 0; these keep null as null.
internal fun JSONObject.str(key: String): String? = if (isNull(key)) null else optString(key)

internal fun JSONObject.int(key: String): Int? = if (isNull(key)) null else optInt(key)

internal fun org.json.JSONArray?.strings(): List<String> =
    if (this == null) emptyList() else (0 until length()).map { getString(it) }

internal fun org.json.JSONArray?.objects(): List<JSONObject> =
    if (this == null) emptyList() else (0 until length()).map { getJSONObject(it) }
