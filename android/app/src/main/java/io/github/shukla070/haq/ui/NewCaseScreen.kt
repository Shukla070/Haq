package io.github.shukla070.haq.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.HaqViewModel

/** Tell the story, attach proof, or record a voice note. Shared files arrive already attached. */
@Composable
fun NewCaseScreen(model: HaqViewModel) {
    var story by rememberSaveable { mutableStateOf("") }
    val attachments = model.newCaseAttachments
    val pickMedia = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(5)) { uris ->
        uris.forEach { model.addAttachment(model.attachment(it)) }
    }
    val pickFiles = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        uris.forEach { model.addAttachment(model.attachment(it)) }
    }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TextButton(onClick = model::goHome) { Text("← Back") }
        Text("What happened?", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(
            value = story,
            onValueChange = { story = it },
            modifier = Modifier.fillMaxWidth().heightIn(min = 160.dp),
            placeholder = { Text("For example: On 12 October I sent Rs 4,500 on UPI. The app said failed but the money was cut from my account.") },
        )
        Text("Your proof", style = MaterialTheme.typography.titleMedium)
        Text(
            "Screenshots of the payment, bank SMS, statements (PDF) or a voice note. Card numbers, " +
                "Aadhaar and OTPs are hidden before anything reads them.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = {
                pickMedia.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            }) { Text("Add screenshots") }
            OutlinedButton(onClick = { pickFiles.launch(arrayOf("application/pdf", "text/plain", "audio/*")) }) {
                Text("Add files")
            }
        }
        VoiceRecorder(onFinished = model::addVoiceNote, enabled = model.busy == null)
        attachments.forEach { file ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(file.name, Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                TextButton(onClick = { model.removeAttachment(file) }) { Text("Remove") }
            }
        }
        OutlinedTextField(
            value = model.customerName,
            onValueChange = { model.customerName = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Your name, as your bank knows it") },
            supportingText = { Text("Haq signs your complaint with it.") },
            singleLine = true,
        )
        Button(
            onClick = { model.start(story.trim()) },
            enabled = (story.isNotBlank() || model.hasVoiceNote) && model.customerName.isNotBlank() && model.busy == null,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Get my money back") }
    }
}
