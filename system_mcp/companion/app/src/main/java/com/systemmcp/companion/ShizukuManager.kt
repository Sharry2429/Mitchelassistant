package com.systemmcp.companion

import android.content.pm.PackageManager
import android.util.Log
import rikka.shizuku.Shizuku
import java.io.BufferedReader
import java.io.InputStreamReader

object ShizukuManager {
    private const val TAG = "ShizukuManager"

    fun checkPermission(): Boolean {
        if (!Shizuku.pingBinder()) {
            Log.e(TAG, "Shizuku is not running")
            return false
        }
        
        return if (Shizuku.isPreV11() || Shizuku.getVersion() < 11) {
            false
        } else {
            Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        }
    }

    fun requestPermission(onRequestResult: (Boolean) -> Unit) {
        if (!Shizuku.pingBinder()) {
            onRequestResult(false)
            return
        }
        
        if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
            onRequestResult(true)
            return
        }

        val listener = object : Shizuku.OnRequestPermissionResultListener {
            override fun onRequestPermissionResult(requestCode: Int, grantResult: Int) {
                if (requestCode == 1) {
                    onRequestResult(grantResult == PackageManager.PERMISSION_GRANTED)
                }
                Shizuku.removeRequestPermissionResultListener(this)
            }
        }
        
        Shizuku.addRequestPermissionResultListener(listener)
        Shizuku.requestPermission(1)
    }

    fun executeShellCommand(command: String): String {
        if (!checkPermission()) {
            return "Error: Shizuku permission not granted or service not running."
        }
        
        try {
            val process = Shizuku.newProcess(arrayOf("sh", "-c", command), null, null)
            val reader = BufferedReader(InputStreamReader(process.inputStream))
            val errorReader = BufferedReader(InputStreamReader(process.errorStream))
            
            val output = StringBuilder()
            var line: String?
            
            while (reader.readLine().also { line = it } != null) {
                output.append(line).append("\n")
            }
            
            while (errorReader.readLine().also { line = it } != null) {
                output.append(line).append("\n")
            }
            
            process.waitFor()
            return output.toString().trim()
        } catch (e: Exception) {
            Log.e(TAG, "Error executing Shizuku command: $command", e)
            return "Exception: ${e.message}"
        }
    }
}
