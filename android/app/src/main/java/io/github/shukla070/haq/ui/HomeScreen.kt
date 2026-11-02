package io.github.shukla070.haq.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.CaseCard
import io.github.shukla070.haq.HaqViewModel
import io.github.shukla070.haq.day
import io.github.shukla070.haq.rupees
import io.github.shukla070.haq.statusLabel
import io.github.shukla070.haq.ui.theme.Ledger
import io.github.shukla070.haq.ui.theme.Marigold
import io.github.shukla070.haq.ui.theme.Paper

const val PRIVACY_POLICY = "https://github.com/Shukla070/Haq/blob/main/docs/PRIVACY.md"

@Composable
fun HomeScreen(model: HaqViewModel) {
    val context = LocalContext.current
    LazyColumn(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Header(model) }
        // Always offer Refresh: it is also how the customer retries after a connection error.
        item {
            Column(Modifier.padding(horizontal = 20.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("Your cases", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                    TextButton(onClick = { model.refresh() }, enabled = model.busy == null) { Text("Refresh") }
                }
                if (model.cases.isEmpty()) {
                    Text("Your cases will appear here.", style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        items(model.cases, key = { it.id }) { case ->
            CaseRow(case, Modifier.padding(horizontal = 20.dp)) { model.open(case.id) }
        }
        item {
            TextButton(
                onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(PRIVACY_POLICY))) },
                modifier = Modifier.padding(horizontal = 8.dp),
            ) { Text("Privacy policy") }
        }
    }
}

@Composable
private fun Header(model: HaqViewModel) {
    Column(Modifier.fillMaxWidth().background(Ledger).padding(start = 20.dp, end = 20.dp, top = 20.dp, bottom = 12.dp)) {
        Text("हक़", style = MaterialTheme.typography.displayLarge, color = Marigold)
        Text(
            "Get back money a company owes you.",
            Modifier.padding(top = 8.dp),
            style = MaterialTheme.typography.headlineMedium,
            color = Paper,
        )
        Text(
            "Tell us what happened and share your proof. Haq writes the complaint the rules entitle you to.",
            Modifier.padding(top = 8.dp, bottom = 16.dp),
            style = MaterialTheme.typography.bodyLarge,
            color = Paper,
        )
        MainButton("Start a new case", model::newCase, Modifier.fillMaxWidth())
        TextButton(onClick = model::showGuide, modifier = Modifier.padding(top = 4.dp)) {
            Text("How Haq works", color = Paper)
        }
    }
}

/** One file in the drawer, with the money it is about at the front. */
@Composable
private fun CaseRow(case: CaseCard, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth().clickable(onClick = onClick),
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = MaterialTheme.shapes.extraSmall,
    ) {
        Row(Modifier.height(IntrinsicSize.Min)) {
            Box(Modifier.width(6.dp).fillMaxHeight().background(MaterialTheme.colorScheme.primary))
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(case.title, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall)
                Text(
                    if (case.running) "Working on it" else statusLabel(case.status),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.labelMedium,
                )
                case.compensationOwed?.takeIf { it > 0 }?.let {
                    Text(rupees(it), style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.error)
                    Text("compensation owed so far", style = MaterialTheme.typography.bodySmall)
                }
                case.until?.let { Text("Next step on ${day(it)}", style = MaterialTheme.typography.bodySmall) }
            }
        }
    }
}
