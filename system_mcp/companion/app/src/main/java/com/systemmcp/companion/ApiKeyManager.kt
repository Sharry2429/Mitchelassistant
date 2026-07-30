package com.systemmcp.companion

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object ApiKeyManager {
    private const val PREFS_NAME = "secure_mcp_prefs"
    private const val KEY_API_CREDITS = "api_credits_key"

    private fun getPrefs(context: Context) = EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveApiKey(context: Context, key: String) {
        getPrefs(context).edit().putString(KEY_API_CREDITS, key).apply()
    }

    fun getApiKey(context: Context): String? {
        return getPrefs(context).getString(KEY_API_CREDITS, null)
    }
}
