package io.github.shukla070.haq.ui

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import io.github.shukla070.haq.CaseView
import io.github.shukla070.haq.Draft
import io.github.shukla070.haq.Evidence
import io.github.shukla070.haq.HaqViewModel
import io.github.shukla070.haq.caseKind
import io.github.shukla070.haq.day
import io.github.shukla070.haq.proofKind
import io.github.shukla070.haq.rupees
import io.github.shukla070.haq.statusHelp
import io.github.shukla070.haq.statusLabel
import java.time.LocalDate

@Composable
fun CaseScreen(model: HaqViewModel, id: String) {
    val case = model.current
    var confirmDelete by rememberSaveable { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SecondButton("← Your cases", model::goHome)
        if (case == null || case.id != id) {
            CircularProgressIndicator()
            return@Column
        }
        About(case)
        if (case.running) {
            Working(case)
        } else {
            Status(case.status)
            if (case.status != "resolved") Owed(case)
            when (case.status) {
                "draft_ready" -> case.draft?.let { DraftReady(model, it, case.evidence) }
                "waiting", "resolved", "sent" -> case.hold?.let { Waiting(model, case.status, it.until, it.message) }
                "needs_input" -> Question(model, case.question ?: "")
                "referred" -> case.referral?.let { Referred(it.where) }
                "paused", "new" -> Paused(model)
            }
            if (case.status != "draft_ready" && case.wasSent) case.draft?.let { SentComplaint(it) }
        }
        Evidence(model, case)
        if (!case.running) {
            SecondButton(
                "Delete this case",
                { confirmDelete = true },
                Modifier.padding(top = 8.dp),
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("Delete this case?") },
            text = { Text("The case and your evidence are removed from Haq's server. This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = { confirmDelete = false; model.delete() }) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Keep") } },
        )
    }
}

/** What the case is about, in the customer's own words. */
@Composable
private fun About(case: CaseView) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(caseKind(case.disputeType), style = MaterialTheme.typography.headlineLarge)
        if (case.title.isNotBlank()) {
            FieldLabel("What you told Haq", Modifier.padding(top = 4.dp))
            Text(case.title, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun Status(status: String) {
    PaperSheet {
        FieldLabel("Current status")
        Text(statusLabel(status), style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        statusHelp(status)?.let { Text(it, Modifier.padding(top = 2.dp), style = MaterialTheme.typography.bodyMedium) }
    }
}

@Composable
private fun Working(case: CaseView) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        CircularProgressIndicator(Modifier.size(28.dp))
        Text(case.progress?.current ?: "Starting", style = MaterialTheme.typography.titleMedium)
    }
    val steps = case.progress?.steps.orEmpty()
    steps.dropLast(1).forEach { Text("✓  $it", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyMedium) }
    Text(
        "This usually takes one to two minutes. Haq checks every fact against your proof and every rule against the official text.",
        style = MaterialTheme.typography.bodySmall,
    )
}

@Composable
private fun Owed(case: CaseView) {
    val owed = case.entitlement?.compensationOwed ?: return
    if (owed <= 0) return
    PaperSheet {
        FieldLabel("Compensation owed so far")
        Text(rupees(owed), style = MaterialTheme.typography.displaySmall, color = MaterialTheme.colorScheme.error)
        val e = case.entitlement
        val why = listOfNotNull(
            e.reversalDueBy?.let { "Your money should have been back by ${day(it)}." },
            e.daysLate?.let { "RBI rules give you ₹100 for each day it's late, and it's $it days late." },
            "This grows by ₹100 every day until the money is back.".takeIf { e.stillGrowing },
        )
        if (why.isNotEmpty()) Text(why.joinToString(" "), Modifier.padding(top = 2.dp), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun DraftReady(model: HaqViewModel, draft: Draft, evidence: List<Evidence>) {
    val context = LocalContext.current
    val attached = evidence.filter { it.attachable }.map { it.name }
    val heldBack = evidence.filter { it.masked && it.kind != "voice" }.map { it.name }
    SectionTitle("Your complaint")
    PaperSheet {
        ComplaintText(draft)
        Stamp("Checked against your proof", Modifier.align(Alignment.End).padding(top = 12.dp))
    }
    Text(
        "Checked before you see it: every fact against your proof, every rule against the official text, every amount against your evidence.",
        style = MaterialTheme.typography.bodySmall,
    )
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        MainButton(
            "Send by email",
            { model.emailProof { proof -> email(context, draft, proof) } },
            Modifier.weight(1f),
            enabled = model.busy == null,
        )
        SecondButton("Copy", { copy(context, draft.subject + "\n\n" + draft.body) })
    }
    Text(
        "Your email app opens with this filled in, but you add the address yourself. Look for the grievance officer " +
            "or customer care email on the company's website or app.",
        style = MaterialTheme.typography.bodySmall,
    )
    if (attached.isNotEmpty()) {
        Text("The email attaches: ${attached.joinToString(", ")}.", style = MaterialTheme.typography.bodySmall)
    }
    if (heldBack.isNotEmpty()) {
        Text(
            "Not attached: ${heldBack.joinToString(", ")}. It shows a card number, Aadhaar or OTP. " +
                "Cover that number, then attach it yourself.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
    SecondButton("I've sent it", model::markSent, Modifier.fillMaxWidth())
    if (draft.nextSteps.isNotBlank()) {
        SectionTitle("What to do next")
        Text(draft.nextSteps, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ComplaintText(draft: Draft) {
    FieldLabel("Send it to")
    Text(draft.recipient, Modifier.padding(bottom = 8.dp), style = MaterialTheme.typography.bodyMedium)
    FieldLabel("Subject")
    Text(draft.subject, Modifier.padding(bottom = 8.dp), style = MaterialTheme.typography.titleSmall)
    FieldLabel("Message")
    SelectionContainer {
        Text(draft.body, style = MaterialTheme.typography.bodyMedium)
    }
}

/** The complaint stays readable after sending: the customer may need it when they follow up. */
@Composable
private fun SentComplaint(draft: Draft) {
    val context = LocalContext.current
    var open by rememberSaveable { mutableStateOf(false) }
    SecondButton(if (open) "Hide your complaint" else "See the complaint you sent", { open = !open }, Modifier.fillMaxWidth())
    if (open) {
        PaperSheet { ComplaintText(draft) }
        SecondButton("Copy", { copy(context, draft.subject + "\n\n" + draft.body) })
    }
}

@Composable
private fun Waiting(model: HaqViewModel, status: String, until: String?, message: String) {
    SectionTitle("What happens next")
    until?.let { InfoRow(untilLabel(status), day(it)) }
    Text(message, style = MaterialTheme.typography.bodyMedium)
    if (status == "waiting" && until != null && LocalDate.parse(until) >= LocalDate.now()) ReminderNote(until)
    if (status != "resolved") {
        SectionTitle("Has this been fixed?")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MainButton("Yes, it's fixed", model::fixed, Modifier.weight(1f), enabled = model.busy == null)
            SecondButton("No, not fixed", model::notFixed, Modifier.weight(1f), enabled = model.busy == null)
        }
    }
}

/** Says when the reminder comes, asking once for the permission Android 13 and up needs. */
@Composable
private fun ReminderNote(until: String) {
    val context = LocalContext.current
    var allowed by remember { mutableStateOf(NotificationManagerCompat.from(context).areNotificationsEnabled()) }
    var asked by rememberSaveable { mutableStateOf(false) }
    val ask = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { allowed = it }
    LaunchedEffect(Unit) {
        if (!allowed && !asked && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            asked = true
            ask.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
    Text(
        if (allowed) "Haq will remind you on ${day(until)}."
        else "Notifications are off, so Haq can't remind you. Put ${day(until)} in your calendar.",
        style = MaterialTheme.typography.bodyMedium,
    )
}

@Composable
private fun Question(model: HaqViewModel, question: String) {
    var answer by rememberSaveable { mutableStateOf("") }
    SectionTitle("Haq's question")
    PaperSheet { Text(question, style = MaterialTheme.typography.bodyMedium) }
    OutlinedTextField(
        value = answer,
        onValueChange = { answer = it },
        modifier = Modifier.fillMaxWidth(),
        label = { Text("Your answer") },
    )
    MainButton("Send answer", { model.answer(answer.trim()) }, enabled = answer.isNotBlank() && model.busy == null)
    Text("Or answer with a voice note", style = MaterialTheme.typography.bodyMedium)
    VoiceRecorder(onFinished = model::answerWithVoice, enabled = model.busy == null)
}

@Composable
private fun Referred(where: String) {
    val context = LocalContext.current
    // Only where to go: the agent's reason is a note in its own words, not written for the customer.
    SectionTitle("What to do now")
    Text(where, style = MaterialTheme.typography.bodyMedium)
    SecondButton("Call 1930 (cyber fraud)", { dial(context, "1930") })
    SecondButton("Call 1915 (consumer helpline)", { dial(context, "1915") })
    SecondButton("Call 14448 (RBI)", { dial(context, "14448") })
}

@Composable
private fun Paused(model: HaqViewModel) {
    MainButton("Try again", model::retry, enabled = model.busy == null)
}

@Composable
private fun Evidence(model: HaqViewModel, case: CaseView) {
    if (case.evidence.isEmpty()) return
    SectionTitle("Your proof")
    case.evidence.forEach { item ->
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        val notes = listOfNotNull(
            "sensitive numbers hidden".takeIf { item.masked },
            "contains text trying to instruct an AI; ignored".takeIf { item.flagged },
        )
        Column {
            Text(item.name, style = MaterialTheme.typography.titleSmall)
            Text((listOf(proofKind(item.kind)) + notes).joinToString("  ·  "), style = MaterialTheme.typography.bodySmall)
        }
        if (item.kind == "marked_image") MarkedPhoto(model, case.id, item.id)
    }
}

/** Haq's mark can be wrong and it goes out with the complaint, so the customer sees it first. */
@Composable
private fun MarkedPhoto(model: HaqViewModel, caseId: String, evidenceId: String) {
    val photo by produceState<ImageBitmap?>(null, caseId, evidenceId) { value = model.markedPhoto(caseId, evidenceId) }
    photo?.let {
        Image(it, "Your photo with the damage marked", Modifier.fillMaxWidth())
        Text(
            "Haq's AI marked this copy. If the mark is wrong, delete this attachment from your email before you send it.",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

private fun copy(context: Context, text: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("Complaint", text))
    Toast.makeText(context, "Copied", Toast.LENGTH_SHORT).show()
}

/** Opens the customer's email app with the complaint and proof filled in; they choose the address and send it. */
private fun email(context: Context, draft: Draft, proof: List<Uri>) {
    val mailApp = Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:"))
    val intent = when (proof.size) {
        0 -> mailApp
        1 -> Intent(Intent.ACTION_SEND).putExtra(Intent.EXTRA_STREAM, proof[0])
        else -> Intent(Intent.ACTION_SEND_MULTIPLE).putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(proof))
    }
    intent.putExtra(Intent.EXTRA_SUBJECT, draft.subject).putExtra(Intent.EXTRA_TEXT, draft.body)
    if (proof.isNotEmpty()) {
        // Only email apps, not every app that can receive a file. A type here would stop the selector matching any app.
        intent.selector = mailApp
        intent.clipData = ClipData.newRawUri("Proof", proof[0]).apply { proof.drop(1).forEach { addItem(ClipData.Item(it)) } }
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    try {
        context.startActivity(intent)
    } catch (e: ActivityNotFoundException) {
        Toast.makeText(context, "No email app found. Use Copy instead.", Toast.LENGTH_LONG).show()
    }
}

private fun dial(context: Context, number: String) {
    context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$number")))
}
