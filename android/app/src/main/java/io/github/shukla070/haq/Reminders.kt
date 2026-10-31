package io.github.shukla070.haq

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.util.concurrent.TimeUnit

/**
 * A notification on the day the bank's time to reply ends. WorkManager keeps it across
 * reboots. The text names no bank or amount, because it can show on a locked phone.
 */
object Reminders {
    const val CASE_ID = "case_id"
    private const val PREFS = "haq_reminders" // case id -> the date its reminder is set for
    private const val CHANNEL = "reminders"
    private const val HOUR = 10

    /** Bring the phone's reminders in line with the server's list of cases. */
    fun sync(context: Context, cases: List<CaseCard>) {
        cases.forEach { update(context, it.id, it.status, it.until) }
        val known = cases.map { it.id }.toSet()
        prefs(context).all.keys.filter { it !in known }.forEach { cancel(context, it) }
    }

    /** Set, move or drop one case's reminder. A date already set is left alone, so a passed one fires once. */
    fun update(context: Context, id: String, status: String, until: String?) {
        if (status != "waiting" || until == null) {
            cancel(context, id)
            return
        }
        if (prefs(context).getString(id, null) == until) return
        val at = LocalDate.parse(until).atTime(HOUR, 0).atZone(ZoneId.systemDefault()).toInstant()
        val delay = Duration.between(Instant.now(), at).toMillis().coerceAtLeast(0)
        val work = OneTimeWorkRequestBuilder<ReminderWorker>()
            .setInitialDelay(delay, TimeUnit.MILLISECONDS)
            .setInputData(workDataOf(CASE_ID to id))
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(id, ExistingWorkPolicy.REPLACE, work)
        prefs(context).edit().putString(id, until).apply()
    }

    private fun cancel(context: Context, id: String) {
        if (!prefs(context).contains(id)) return
        WorkManager.getInstance(context).cancelUniqueWork(id)
        NotificationManagerCompat.from(context).cancel(id.hashCode())
        prefs(context).edit().remove(id).apply()
    }

    @SuppressLint("MissingPermission") // areNotificationsEnabled is false without it
    fun show(context: Context, id: String) {
        val manager = NotificationManagerCompat.from(context)
        if (!manager.areNotificationsEnabled()) return
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Reminders", NotificationManager.IMPORTANCE_DEFAULT),
        )
        val open = Intent(context, MainActivity::class.java).putExtra(CASE_ID, id)
        val flags = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Has the bank fixed your complaint?")
            .setContentText("Its reply date has come. Tap to tell Haq what to do next.")
            .setContentIntent(PendingIntent.getActivity(context, id.hashCode(), open, flags))
            .setAutoCancel(true)
            .build()
        manager.notify(id.hashCode(), notification)
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}

class ReminderWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        Reminders.show(applicationContext, inputData.getString(Reminders.CASE_ID) ?: return Result.failure())
        return Result.success()
    }
}
