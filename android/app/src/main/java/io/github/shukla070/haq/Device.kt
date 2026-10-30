package io.github.shukla070.haq

import android.content.Context
import android.util.Base64
import java.security.SecureRandom

/**
 * This install's device token. Made once from 32 random bytes and kept in private app
 * storage; the server knows a case's owner only by a hash of it. There are no accounts,
 * so clearing the app's data loses access to its cases.
 */
object Device {
    private const val PREFS = "haq"
    private const val KEY = "device_token"

    fun token(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.getString(KEY, null)?.let { return it }
        val bytes = ByteArray(32).also { SecureRandom().nextBytes(it) }
        val token = Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
        prefs.edit().putString(KEY, token).apply()
        return token
    }

    /** The customer's name for signing complaints, remembered for the next case. */
    fun name(context: Context): String =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(NAME, null).orEmpty()

    fun saveName(context: Context, name: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(NAME, name).apply()
    }

    private const val NAME = "customer_name"
}
