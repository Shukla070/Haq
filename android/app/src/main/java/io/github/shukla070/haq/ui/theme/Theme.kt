package io.github.shukla070.haq.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp

private val LightColors = lightColorScheme(
    primary = Ledger,
    onPrimary = Paper,
    secondary = Marigold,
    onSecondary = Ink,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = Sheet,
    onSurfaceVariant = InkSoft,
    surfaceContainerHigh = Sheet,
    outline = InkSoft,
    outlineVariant = Rule,
    error = StampRed,
)

private val DarkColors = darkColorScheme(
    primary = Marigold,
    onPrimary = Ink,
    secondary = Marigold,
    onSecondary = Ink,
    background = NightPaper,
    onBackground = NightInk,
    surface = NightPaper,
    onSurface = NightInk,
    surfaceVariant = NightSheet,
    onSurfaceVariant = NightInkSoft,
    surfaceContainerHigh = NightSheet,
    outline = NightInkSoft,
    outlineVariant = NightRule,
    error = NightStamp,
)

private val HaqShapes = Shapes(
    extraSmall = RoundedCornerShape(2.dp),
    small = RoundedCornerShape(4.dp),
    medium = RoundedCornerShape(6.dp),
    large = RoundedCornerShape(6.dp),
    extraLarge = RoundedCornerShape(8.dp),
)

@Composable
fun HaqTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = Typography,
        shapes = HaqShapes,
        content = content,
    )
}
