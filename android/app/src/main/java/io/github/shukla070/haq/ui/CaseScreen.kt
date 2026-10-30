package io.github.shukla070.haq.ui

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
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
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.CaseView
import io.github.shukla070.haq.Draft
import io.github.shukla070.haq.HaqViewModel
import io.github.shukla070.haq.day
import io.github.shukla070.haq.rupees
import io.github.shukla070.haq.statusLabel

@Composable
fun CaseScreen(model: HaqViewModel, id: String) {
    val case = model.current
    var confirmDelete by rememberSaveable { mutableStateOf(false) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TextButton(onClick = model::goHome) { Text("← Your cases") }
        if (case == null || case.id != id) {
            CircularProgressIndicator()
            return@Column
        }
        if (case.running) {
            Working(case)
        } else {
            Text(statusLabel(case.status), style = MaterialTheme.typography.headlineSmall)
            Owed(case)
            when (case.status) {
                "draft_ready" -> case.draft?.let { DraftReady(model, it) }
                "waiting", "resolved", "sent" -> case.hold?.let { Waiting(it.until, it.message) }
                "needs_input" -> Question(model, case.question ?: "")
                "referred" -> case.referral?.let { Referred(it.reason, it.where) }
                "filed" -> Text("You sent your complaint to the RBI Ombudsman. Keep its acknowledgement and reference number.")
                "paused", "new" -> Paused(model)
            }
        }
        Evidence(case)
        if (!case.running) {
            TextButton(onClick = { confirmDelete = true }) {
                Text("Delete this case", color = MaterialTheme.colorScheme.error)
            }
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

@Composable
private fun Working(case: CaseView) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        CircularProgressIndicator(Modifier.size(28.dp))
        Text(case.progress?.current ?: "Starting", style = MaterialTheme.typography.titleMedium)
    }
    val steps = case.progress?.steps.orEmpty()
    steps.dropLast(1).forEach { Text("✓  $it", style = MaterialTheme.typography.bodyMedium) }
    Text(
        "This usually takes one to two minutes. Haq checks every fact against your proof and every rule against RBI's own text.",
        style = MaterialTheme.typography.bodySmall,
    )
}

@Composable
private fun Owed(case: CaseView) {
    val owed = case.entitlement?.compensationOwed ?: return
    if (owed <= 0) return
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text("Compensation owed so far", style = MaterialTheme.typography.labelLarge)
            Text(rupees(owed), style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
            val e = case.entitlement
            val late = e.daysLate?.let { "$it days late" }
            val growing = if (e.stillGrowing) "growing by ₹100 every day until the money is back" else null
            listOfNotNull(late, growing).takeIf { it.isNotEmpty() }?.let {
                Text(it.joinToString(", "), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun DraftReady(model: HaqViewModel, draft: Draft) {
    val context = LocalContext.current
    Text("To: ${draft.recipient}", style = MaterialTheme.typography.bodyMedium)
    Text(draft.subject, style = MaterialTheme.typography.titleMedium)
    Card {
        SelectionContainer {
            Text(draft.body, Modifier.padding(16.dp), style = MaterialTheme.typography.bodyMedium)
        }
    }
    Text(
        "Checked before you see it: every fact against your proof, every rule against the official text, every amount against your evidence.",
        style = MaterialTheme.typography.bodySmall,
    )
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(onClick = { copy(context, draft.subject + "\n\n" + draft.body) }) { Text("Copy") }
        OutlinedButton(onClick = { email(context, draft) }) { Text("Send by email") }
    }
    Button(onClick = model::markSent, modifier = Modifier.fillMaxWidth()) { Text("I've sent it") }
    if (draft.nextSteps.isNotBlank()) Text("Next: ${draft.nextSteps}", style = MaterialTheme.typography.bodyMedium)
}

@Composable
private fun Waiting(until: String?, message: String) {
    until?.let { Text("Until ${day(it)}", style = MaterialTheme.typography.titleMedium) }
    Text(message, style = MaterialTheme.typography.bodyLarge)
}

@Composable
private fun Question(model: HaqViewModel, question: String) {
    var answer by rememberSaveable { mutableStateOf("") }
    Text(question, style = MaterialTheme.typography.bodyLarge)
    OutlinedTextField(value = answer, onValueChange = { answer = it }, modifier = Modifier.fillMaxWidth())
    Button(onClick = { model.answer(answer.trim()) }, enabled = answer.isNotBlank() && model.busy == null) {
        Text("Send answer")
    }
}

@Composable
private fun Referred(reason: String, where: String) {
    val context = LocalContext.current
    Text(reason, style = MaterialTheme.typography.bodyLarge)
    Text(where, style = MaterialTheme.typography.bodyLarge)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedButton(onClick = { dial(context, "1930") }) { Text("Call 1930 (cyber fraud)") }
        OutlinedButton(onClick = { dial(context, "14448") }) { Text("Call 14448 (RBI)") }
    }
}

@Composable
private fun Paused(model: HaqViewModel) {
    Text("Haq was interrupted before it finished. Your case and evidence are saved.", style = MaterialTheme.typography.bodyLarge)
    Button(onClick = model::retry, enabled = model.busy == null) { Text("Try again") }
}

@Composable
private fun Evidence(case: CaseView) {
    if (case.evidence.isEmpty()) return
    Text("Your proof", style = MaterialTheme.typography.titleMedium)
    case.evidence.forEach { item ->
        val notes = listOfNotNull(
            "sensitive numbers hidden".takeIf { item.masked },
            "contains text trying to instruct an AI; ignored".takeIf { item.flagged },
        )
        Text(
            "${item.name}" + if (notes.isEmpty()) "" else "  ·  " + notes.joinToString(", "),
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

private fun copy(context: Context, text: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText("Complaint", text))
    Toast.makeText(context, "Copied", Toast.LENGTH_SHORT).show()
}

/** Opens the customer's email app with the complaint filled in; they choose the address and send it. */
private fun email(context: Context, draft: Draft) {
    val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:"))
        .putExtra(Intent.EXTRA_SUBJECT, draft.subject)
        .putExtra(Intent.EXTRA_TEXT, draft.body)
    try {
        context.startActivity(intent)
    } catch (e: ActivityNotFoundException) {
        Toast.makeText(context, "No email app found. Use Copy instead.", Toast.LENGTH_LONG).show()
    }
}

private fun dial(context: Context, number: String) {
    context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$number")))
}
