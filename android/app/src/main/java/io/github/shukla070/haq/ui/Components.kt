package io.github.shukla070.haq.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

private val BUTTON_PADDING = PaddingValues(horizontal = 16.dp, vertical = 10.dp)

/** The one marigold action on a screen. */
@Composable
fun MainButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    Button(
        onClick = onClick,
        modifier = modifier.heightIn(min = 48.dp),
        enabled = enabled,
        shape = MaterialTheme.shapes.medium,
        contentPadding = BUTTON_PADDING,
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.secondary,
            contentColor = MaterialTheme.colorScheme.onSecondary,
        ),
    ) { Text(text) }
}

@Composable
fun SecondButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    icon: Int? = null,
    color: Color = MaterialTheme.colorScheme.primary,
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 48.dp),
        enabled = enabled,
        shape = MaterialTheme.shapes.medium,
        contentPadding = BUTTON_PADDING,
        border = BorderStroke(1.5.dp, if (enabled) color else MaterialTheme.colorScheme.outlineVariant),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = color),
    ) {
        icon?.let { Icon(painterResource(it), null, Modifier.padding(end = 6.dp).size(18.dp)) }
        Text(text)
    }
}

/** A heading that starts a part of the screen. */
@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier.padding(top = 8.dp), style = MaterialTheme.typography.titleLarge)
}

/** A small label saying what the text under it is. */
@Composable
fun FieldLabel(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

/** A label and its value on one line, so no number or date stands alone. */
@Composable
fun InfoRow(label: String, value: String, modifier: Modifier = Modifier, valueColor: Color = Color.Unspecified) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(
            label,
            Modifier.weight(1f).padding(end = 12.dp),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(value, style = MaterialTheme.typography.titleSmall, color = valueColor, textAlign = TextAlign.End)
    }
}

/** What a case's date means depends on where the case stands. */
fun untilLabel(status: String): String = if (status == "waiting") "Reply due by" else "Next step on"

/** A sheet of paper on the page, for what the customer reads closely. */
@Composable
fun PaperSheet(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surfaceVariant,
        contentColor = MaterialTheme.colorScheme.onSurface,
        shape = MaterialTheme.shapes.extraSmall,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) { Column(Modifier.padding(16.dp), content = content) }
}

/** Lands once, like a rubber stamp, when the complaint first appears. */
@Composable
fun Stamp(text: String, modifier: Modifier = Modifier) {
    val landing = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        landing.animateTo(1f, spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessMediumLow))
    }
    val color = MaterialTheme.colorScheme.error
    Text(
        text,
        modifier
            .alpha(landing.value.coerceIn(0f, 1f))
            .scale(1.7f - 0.7f * landing.value)
            .rotate(-5f)
            .border(2.dp, color, MaterialTheme.shapes.small)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        color = color,
        style = MaterialTheme.typography.labelMedium,
    )
}
