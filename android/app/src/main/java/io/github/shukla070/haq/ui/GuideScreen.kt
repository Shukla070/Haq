package io.github.shukla070.haq.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.HaqViewModel

private val STEPS = listOf(
    "Tell Haq what happened" to "Type it, or record a voice note in Hindi, English or both.",
    "Add your proof" to "Screenshots, bank SMS, invoices, statements, or a photo of a damaged item.",
    "Read your complaint" to "In a minute or two, Haq works out what the rules give you and writes the complaint. " +
        "It checks every fact against your proof and every rule against the official text.",
    "Send it yourself" to "Your email app opens with the complaint and proof filled in. Haq never sends anything. " +
        "Then tap I've sent it, and Haq reminds you when the company's time is up and helps with the next step.",
)

/** The user manual: shown once on first launch, and any time from the home screen. */
@Composable
fun GuideScreen(model: HaqViewModel) {
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("How Haq works", style = MaterialTheme.typography.headlineLarge)
        STEPS.forEachIndexed { index, (title, detail) ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "${index + 1}",
                    Modifier.width(36.dp),
                    style = MaterialTheme.typography.displaySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                Column(Modifier.weight(1f)) {
                    Text(title, style = MaterialTheme.typography.titleMedium)
                    Text(detail, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        PaperSheet {
            Text("What Haq can help with", style = MaterialTheme.typography.titleMedium)
            Text("A failed UPI payment that took your money, and refunds for online orders.", style = MaterialTheme.typography.bodyMedium)
            Text(
                "Lost money to a scam or fraud? Call 1930 right away. Haq can't help with that.",
                Modifier.padding(top = 8.dp),
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        PaperSheet {
            Text("Your data", style = MaterialTheme.typography.titleMedium)
            Text(
                "What you add goes to Meta's AI models and is kept on Haq's server until you delete the case. " +
                    "Never share a PIN, password or OTP.",
                style = MaterialTheme.typography.bodyMedium,
            )
            TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(PRIVACY_POLICY))) }) {
                Text("Privacy policy")
            }
        }
        Text(
            "Haq is not a lawyer and can make mistakes, and it can't promise you'll get your money back. Read your complaint before you send it.",
            style = MaterialTheme.typography.bodySmall,
        )
        MainButton("Got it", model::goHome, Modifier.fillMaxWidth())
    }
}
