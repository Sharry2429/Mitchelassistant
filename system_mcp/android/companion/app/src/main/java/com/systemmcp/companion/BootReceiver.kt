package com.systemmcp.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.d("SystemMCP", "Boot completed. Enabling adb_wifi_enabled.")
            try {
                // Requires WRITE_SECURE_SETTINGS permission
                Settings.Global.putInt(context.contentResolver, "adb_wifi_enabled", 1)
                Log.d("SystemMCP", "Wireless debugging re-enabled successfully.")
            } catch (e: SecurityException) {
                Log.e("SystemMCP", "Failed to enable wireless debugging: Missing WRITE_SECURE_SETTINGS permission.")
            }
        }
    }
}
