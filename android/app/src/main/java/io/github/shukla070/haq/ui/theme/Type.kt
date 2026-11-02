package io.github.shukla070.haq.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import io.github.shukla070.haq.R

// Both families cover Hindi and English, so a complaint in either reads the same.
val Rozha = FontFamily(Font(R.font.rozha_one))
val Hind = FontFamily(
    Font(R.font.hind_regular, FontWeight.Normal),
    Font(R.font.hind_medium, FontWeight.Medium),
    Font(R.font.hind_semibold, FontWeight.SemiBold),
)

private fun display(size: Int, line: Int) = TextStyle(fontFamily = Rozha, fontSize = size.sp, lineHeight = line.sp)
private fun text(size: Int, line: Int, weight: FontWeight = FontWeight.Normal) =
    TextStyle(fontFamily = Hind, fontWeight = weight, fontSize = size.sp, lineHeight = line.sp)

val Typography = Typography(
    displayLarge = display(72, 76),
    displayMedium = display(56, 62),
    displaySmall = display(36, 42),
    headlineLarge = display(32, 38),
    headlineMedium = display(28, 34),
    headlineSmall = display(26, 32),
    titleLarge = text(20, 26, FontWeight.SemiBold),
    titleMedium = text(17, 24, FontWeight.SemiBold),
    titleSmall = text(15, 21, FontWeight.SemiBold),
    bodyLarge = text(17, 25),
    bodyMedium = text(15, 22),
    bodySmall = text(13, 18),
    labelLarge = text(15, 20, FontWeight.SemiBold),
    labelMedium = text(13, 18, FontWeight.SemiBold),
    labelSmall = text(12, 16, FontWeight.Medium),
)
