package io.github.shukla070.haq.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.shukla070.haq.CaseCard
import io.github.shukla070.haq.HaqViewModel
import io.github.shukla070.haq.R
import io.github.shukla070.haq.caseKind
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
            Column(Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("Your cases", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
                    SecondButton("Refresh", { model.refresh() }, enabled = model.busy == null, icon = R.drawable.ic_refresh)
                }
                if (model.cases.isEmpty()) {
                    Text(
                        when {
                            model.casesLoaded -> "No cases yet. When you start one, it appears here with its status and what you're owed."
                            model.error != null -> "Your cases couldn't load. They're still saved, so tap Refresh to try again."
                            else -> "Loading your cases…"
                        },
                        style = MaterialTheme.typography.bodyMedium,
                    )
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
            ) { Text("Privacy policy", textDecoration = TextDecoration.Underline) }
        }
    }
}

@Composable
private fun Header(model: HaqViewModel) {
    Column(Modifier.fillMaxWidth().background(Ledger).padding(start = 20.dp, end = 20.dp, top = 20.dp, bottom = 20.dp)) {
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
        OutlinedButton(
            onClick = model::showGuide,
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp).heightIn(min = 48.dp),
            shape = MaterialTheme.shapes.medium,
            border = BorderStroke(1.5.dp, Paper),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Paper),
        ) {
            Icon(painterResource(R.drawable.ic_help), null, Modifier.size(20.dp))
            Text("How Haq works", Modifier.weight(1f).padding(start = 8.dp))
            Icon(painterResource(R.drawable.ic_chevron), null, Modifier.size(20.dp))
        }
    }
}

/** One file in the drawer: what it is about, then each detail with its label. */
@Composable
private fun CaseRow(case: CaseCard, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth().clickable(onClick = onClick),
        color = MaterialTheme.colorScheme.surfaceVariant,
        contentColor = MaterialTheme.colorScheme.onSurface,
        shape = MaterialTheme.shapes.extraSmall,
    ) {
        Row(Modifier.height(IntrinsicSize.Min)) {
            Box(Modifier.width(6.dp).fillMaxHeight().background(MaterialTheme.colorScheme.primary))
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(caseKind(case.disputeType), Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                    Icon(
                        painterResource(R.drawable.ic_chevron),
                        "Open case",
                        Modifier.size(22.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
                Text(
                    case.title,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                HorizontalDivider(Modifier.padding(vertical = 2.dp), color = MaterialTheme.colorScheme.outlineVariant)
                InfoRow(
                    "Current status",
                    if (case.running) "Working on it" else statusLabel(case.status),
                    valueColor = MaterialTheme.colorScheme.primary,
                )
                case.compensationOwed?.takeIf { it > 0 }?.let {
                    InfoRow("Compensation owed so far", rupees(it), valueColor = MaterialTheme.colorScheme.error)
                }
                case.until?.let { InfoRow(untilLabel(case.status), day(it)) }
            }
        }
    }
}
