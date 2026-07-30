package com.systemmcp.companion

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            try {
                // Automatically write adb_wifi_enabled = 1 to Settings.Global using pre-granted WRITE_SECURE_SETTINGS
                Settings.Global.putInt(context.contentResolver, "adb_wifi_enabled", 1)
            } catch (e: Exception) {
                e.printStackTrace()
            }

            // Start the MitchellService automatically
            MitchellService.startCompanion(context)
        }
    }
}
