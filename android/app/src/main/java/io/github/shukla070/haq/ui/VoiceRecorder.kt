package io.github.shukla070.haq.ui

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Build
import android.os.SystemClock
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import java.io.File
import kotlinx.coroutines.delay

private const val MAX_SECONDS = 5 * 60

/**
 * Records a voice note with the microphone and hands the finished file back.
 * The file is a small mono m4a in the app's cache; the caller uploads it.
 */
@Composable
fun VoiceRecorder(onFinished: (File) -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    val context = LocalContext.current
    var recording by remember { mutableStateOf(false) }
    var seconds by remember { mutableIntStateOf(0) }
    var denied by remember { mutableStateOf(false) }
    var problem by remember { mutableStateOf<String?>(null) }
    var recorder by remember { mutableStateOf<MediaRecorder?>(null) }
    var output by remember { mutableStateOf<File?>(null) }
    val currentRecorder by rememberUpdatedState(recorder)
    DisposableEffect(Unit) {
        onDispose {
            try {
                currentRecorder?.release()
            } catch (_: Exception) {
                // already released or never started
            }
        }
    }

    // Not named start/stop: in an apply { } on the recorder, start() would call this, not MediaRecorder.start().
    fun startRecording() {
        problem = null
        val dir = File(context.cacheDir, "voice").apply { mkdirs() }
        val file = File(dir, "voice-${System.currentTimeMillis()}.m4a")
        val fresh = newRecorder(context)
        try {
            fresh.setAudioSource(MediaRecorder.AudioSource.MIC)
            fresh.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            fresh.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            fresh.setAudioChannels(1)
            fresh.setAudioSamplingRate(16_000)
            fresh.setAudioEncodingBitRate(64_000)
            fresh.setOutputFile(file.absolutePath)
            fresh.prepare()
            fresh.start()
            recorder = fresh
            output = file
            seconds = 0
            recording = true
        } catch (_: Exception) {
            fresh.release()
            file.delete()
            problem = "Couldn't start recording. Please try again."
        }
    }

    fun stopRecording() {
        val active = recorder
        val file = output
        recorder = null
        output = null
        recording = false
        if (active == null || file == null) return
        val saved = try {
            active.stop()
            true
        } catch (_: Exception) {
            false
        }
        try {
            active.release()
        } catch (_: Exception) {
            // stop() already failed; nothing more to do
        }
        if (saved && file.length() > 0) onFinished(file)
        else {
            file.delete()
            problem = "That recording didn't work. Please try again."
        }
    }

    val askPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startRecording() else denied = true
    }

    fun onRecord() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startRecording()
        } else {
            askPermission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    LaunchedEffect(recording) {
        if (!recording) return@LaunchedEffect
        val started = SystemClock.elapsedRealtime()
        while (true) {
            delay(500)
            val elapsed = ((SystemClock.elapsedRealtime() - started) / 1000).toInt()
            seconds = elapsed
            if (elapsed >= MAX_SECONDS) {
                stopRecording()
                break
            }
        }
    }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        if (recording) {
            Text(
                "Recording… ${seconds / 60}:${(seconds % 60).toString().padStart(2, '0')}",
                style = MaterialTheme.typography.bodyMedium,
            )
            OutlinedButton(onClick = ::stopRecording) { Text("Stop") }
        } else {
            OutlinedButton(onClick = ::onRecord, enabled = enabled) { Text("Record a voice note") }
        }
        Text("Speak in Hindi, English or both.", style = MaterialTheme.typography.bodySmall)
        if (denied) {
            Text(
                "Voice notes need the microphone. Typing still works.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
        problem?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }
    }
}

/** MediaRecorder(context) exists only on API 31+; older phones use the no-arg constructor. */
@Suppress("DEPRECATION")
private fun newRecorder(context: Context): MediaRecorder =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context) else MediaRecorder()
