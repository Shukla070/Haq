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

fun statusLabel(status: String): String = when (status) {
    "new" -> "Not started"
    "working" -> "Working on it"
    "draft_ready" -> "Complaint ready"
    "waiting" -> "Waiting for the bank"
    "needs_input" -> "Needs your answer"
    "referred" -> "Go elsewhere"
    "resolved" -> "Resolved"
    "filed" -> "Sent to the Ombudsman"
    "sent" -> "Complaint sent"
    "paused" -> "Interrupted"
    else -> status
}
