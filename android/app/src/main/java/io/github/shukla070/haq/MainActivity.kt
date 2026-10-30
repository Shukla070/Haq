package io.github.shukla070.haq

import android.content.Intent
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
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import io.github.shukla070.haq.ui.CaseScreen
import io.github.shukla070.haq.ui.HomeScreen
import io.github.shukla070.haq.ui.NewCaseScreen
import io.github.shukla070.haq.ui.theme.HaqTheme

class MainActivity : ComponentActivity() {
    private lateinit var model: HaqViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        model = ViewModelProvider(this)[HaqViewModel::class.java]
        // Only a fresh share: not after rotation, nor when reopened from recents with the old intent.
        val fromHistory = intent.flags and Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY != 0
        if (savedInstanceState == null && !fromHistory) model.receiveShare(intent)
        enableEdgeToEdge()
        setContent {
            HaqTheme {
                HaqApp()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        model.receiveShare(intent)
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
