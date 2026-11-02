package io.github.shukla070.haq

import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private val india = Locale.forLanguageTag("en-IN")
private val dayMonthYear = DateTimeFormatter.ofPattern("d MMM yyyy", india)

/** ₹1,00,000 style. */
fun rupees(amount: Int): String = "₹" + NumberFormat.getIntegerInstance(india).format(amount)

/** "2026-11-29" → "29 Nov 2026"; anything unparseable is shown as it is. */
fun day(iso: String): String = runCatching { LocalDate.parse(iso).format(dayMonthYear) }.getOrDefault(iso)

fun caseKind(disputeType: String?): String = when (disputeType) {
    "upi_failed_debit" -> "Failed UPI payment"
    "ecommerce_refund" -> "Online order refund"
    else -> "Your case"
}

/** One line under the status saying what it means for the customer. */
fun statusHelp(status: String): String? = when (status) {
    "working" -> "Haq is reading your proof and writing your complaint."
    "draft_ready" -> "Your complaint is written and checked. Read it, then send it yourself."
    "waiting" -> "You sent your complaint, so now they have time to reply."
    "needs_input" -> "Haq needs one more detail from you before it can finish."
    "referred" -> "Haq can't take this case, but these services can help."
    "resolved" -> "You told Haq this has been fixed."
    "filed" -> "You took your complaint to the next step. Keep its acknowledgement and reference number."
    "sent" -> "You sent your complaint. Tell Haq whether it has been fixed."
    "paused" -> "Haq stopped before it finished. Your case and proof are saved."
    else -> null
}

/** What a piece of proof is, since a file name often doesn't say. */
fun proofKind(kind: String): String = when (kind) {
    "image" -> "Photo or screenshot"
    "text" -> "Text file"
    "pdf" -> "PDF"
    "voice" -> "Your voice note"
    "marked_image" -> "Your photo, with the damage marked by Haq"
    else -> "File"
}

fun statusLabel(status: String): String = when (status) {
    "new" -> "Not started"
    "working" -> "Working on it"
    "draft_ready" -> "Complaint ready"
    "waiting" -> "Waiting for a reply"
    "needs_input" -> "Needs your answer"
    "referred" -> "Go elsewhere"
    "resolved" -> "Resolved"
    "filed" -> "Escalated"
    "sent" -> "Complaint sent"
    "paused" -> "Interrupted"
    else -> status
}
