package io.github.shukla070.haq

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import io.github.shukla070.haq.ui.CaseScreen
import io.github.shukla070.haq.ui.HomeScreen
import io.github.shukla070.haq.ui.NewCaseScreen
import io.github.shukla070.haq.ui.theme.HaqTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            HaqTheme {
                HaqApp()
            }
        }
    }
}

@Composable
fun HaqApp(model: HaqViewModel = viewModel()) {
    BackHandler(enabled = model.screen != Screen.Home) { model.goHome() }
    Scaffold(modifier = Modifier.fillMaxSize()) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            model.busy?.let { label ->
                LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(label, Modifier.padding(horizontal = 16.dp, vertical = 4.dp), style = MaterialTheme.typography.bodySmall)
            }
            model.error?.let { message ->
                Text(
                    message,
                    Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            Box(Modifier.fillMaxSize()) {
                when (val screen = model.screen) {
                    Screen.Home -> HomeScreen(model)
                    Screen.NewCase -> NewCaseScreen(model)
                    is Screen.Case -> CaseScreen(model, screen.id)
                }
            }
        }
    }
}
