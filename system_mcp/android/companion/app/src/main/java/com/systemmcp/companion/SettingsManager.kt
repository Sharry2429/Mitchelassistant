package com.systemmcp.companion

import android.content.Context
import android.provider.Settings
import android.util.Log

object SettingsManager {
    fun writeSetting(context: Context, namespace: String, key: String, value: String): Boolean {
        return try {
            val resolver = context.contentResolver
            when (namespace.lowercase()) {
                "secure" -> Settings.Secure.putString(resolver, key, value)
                "global" -> Settings.Global.putString(resolver, key, value)
                "system" -> Settings.System.putString(resolver, key, value)
                else -> false
            }
        } catch (e: SecurityException) {
            Log.e("SystemMCP", "Failed to write setting: ${e.message}")
            false
        }
    }
}
