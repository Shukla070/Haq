# Haq for Android

Kotlin and Jetpack Compose. Package `io.github.shukla070.haq`, Android 8.0 (API 26) and up.
It talks to the Haq server described in [docs/APP_API.md](../docs/APP_API.md) and keeps no
case data on the phone beyond its device token.

## Run it

1. Start the server on the laptop (from `server/`): `uvicorn haq.api:app --host 0.0.0.0 --port 8000`
2. Connect the phone by USB with USB debugging on, or start an emulator.
3. Let the device reach the laptop's server at its own `127.0.0.1:8000`:

   ```bash
   adb reverse tcp:8000 tcp:8000
   ```

4. Open this folder in Android Studio and press Run, or from here:

   ```bash
   ./gradlew installDebug
   ```

The command line needs a JDK 25, which Android Studio includes: point `JAVA_HOME` at
Android Studio's `jbr` folder.

To use a hosted server instead, add its https address to `local.properties`:

```
haq.serverUrl=https://your-server.example
```

Debug builds may use plain http only to `127.0.0.1`; release builds use https only.

## Layout

| Path | What it is |
|---|---|
| `HaqApi.kt` | The server API over `HttpURLConnection`; no networking library |
| `Models.kt` | The case view and home list, parsed from JSON |
| `Device.kt` | The install's random device token, in private app storage |
| `HaqViewModel.kt` | App state, actions, and polling while the agent works |
| `SharedFiles.kt` | "Share to Haq": copies shared screenshots, files and SMS text into private cache |
| `ui/HomeScreen.kt` | Your cases |
| `ui/NewCaseScreen.kt` | Tell the story (typed or as a voice note), attach screenshots and files |
| `ui/CaseScreen.kt` | Progress, then the screen for each status |
| `ui/VoiceRecorder.kt` | Records a voice note (m4a, mono) after asking for the microphone |
