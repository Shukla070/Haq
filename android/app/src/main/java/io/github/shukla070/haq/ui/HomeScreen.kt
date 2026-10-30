package io.github.shukla070.haq.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.CaseCard
import io.github.shukla070.haq.HaqViewModel
import io.github.shukla070.haq.day
import io.github.shukla070.haq.rupees
import io.github.shukla070.haq.statusLabel

@Composable
fun HomeScreen(model: HaqViewModel) {
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(Modifier.padding(top = 24.dp, bottom = 8.dp)) {
                Text("Haq", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
                Text(
                    "Get back money a company owes you. Tell us what happened, share your proof, " +
                        "and Haq writes the complaint the rules entitle you to.",
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
            Button(onClick = model::newCase, modifier = Modifier.fillMaxWidth()) {
                Text("Start a new case")
            }
        }
        // Always offer Refresh: it is also how the customer retries after a connection error.
        item {
            Row(Modifier.fillMaxWidth().padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Your cases", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                TextButton(onClick = { model.refresh() }, enabled = model.busy == null) { Text("Refresh") }
            }
            if (model.cases.isEmpty()) {
                Text("No cases yet.", style = MaterialTheme.typography.bodyMedium)
            }
        }
        items(model.cases, key = { it.id }) { case ->
            CaseRow(case) { model.open(case.id) }
        }
    }
}

@Composable
private fun CaseRow(case: CaseCard, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(case.title, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge)
            Text(
                if (case.running) "Working on it" else statusLabel(case.status),
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelLarge,
            )
            case.compensationOwed?.takeIf { it > 0 }?.let {
                Text("${rupees(it)} compensation owed so far", style = MaterialTheme.typography.bodyMedium)
            }
            case.until?.let { Text("Next step on ${day(it)}", style = MaterialTheme.typography.bodySmall) }
        }
    }
}
