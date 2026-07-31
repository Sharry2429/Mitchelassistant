package com.systemmcp.companion

import android.content.Context

object Prefs {
    private const val FILE = "mcp_prefs"

    fun isEnabled(context: Context): Boolean =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getBoolean("enabled", true)

    fun setEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .edit().putBoolean("enabled", enabled).apply()
    }
}
