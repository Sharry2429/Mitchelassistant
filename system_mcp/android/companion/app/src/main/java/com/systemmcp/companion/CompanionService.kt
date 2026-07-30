package com.systemmcp.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import com.google.gson.Gson
import java.io.InputStream
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import java.nio.ByteBuffer
import kotlin.concurrent.thread

class CompanionService : Service() {

    private val port = 5000
    private var serverSocket: ServerSocket? = null
    private var isRunning = false
    private var secureToken = ""
    private val gson = Gson()

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        val notification = Notification.Builder(this, "system_mcp_channel")
            .setContentTitle("System MCP")
            .setContentText("Background service active")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()
        startForeground(1, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val intentToken = intent?.getStringExtra("token")
        if (intentToken != null) {
            secureToken = intentToken
            Log.d("SystemMCP", "Token registered.")
        }

        if (!isRunning) {
            isRunning = true
            thread { startServer() }
        }
        return START_STICKY
    }

    private fun startServer() {
        try {
            serverSocket = ServerSocket(port)
            Log.d("SystemMCP", "Server started on port $port")
            while (isRunning) {
                val client = serverSocket?.accept()
                if (client != null) {
                    thread { handleClient(client) }
                }
            }
        } catch (e: Exception) {
            Log.e("SystemMCP", "Server socket error: ${e.message}")
        }
    }

    private fun handleClient(client: Socket) {
        try {
            val input = client.getInputStream()
            val output = client.getOutputStream()

            while (isRunning) {
                val requestPayload = readFramedMessage(input) ?: break
                
                // Parse Request
                val requestMap = try {
                    gson.fromJson(requestPayload, Map::class.java) as Map<String, Any>
                } catch (e: Exception) {
                    sendFramedMessage(output, mapOf("success" to false, "error" to "Invalid JSON"))
                    continue
                }

                val action = requestMap["action"] as? String ?: ""
                val token = requestMap["token"] as? String ?: ""

                // Authenticate
                if (token != secureToken && secureToken.isNotEmpty()) {
                    sendFramedMessage(output, mapOf("success" to false, "error" to "Invalid Token"))
                    continue
                }

                // Route Actions
                when (action) {
                    "handshake" -> {
                        sendFramedMessage(output, mapOf(
                            "success" to true, 
                            "version" to "1.0.0"
                        ))
                    }
                    "get_clipboard" -> {
                        val text = MCPAccessibilityService.instance?.getClipboardData() ?: ""
                        sendFramedMessage(output, mapOf("success" to true, "data" to text))
                    }
                    "set_clipboard" -> {
                        val text = requestMap["text"] as? String ?: ""
                        MCPAccessibilityService.instance?.setClipboardData(text)
                        sendFramedMessage(output, mapOf("success" to true))
                    }
                    "write_setting" -> {
                        val ns = requestMap["namespace"] as? String ?: ""
                        val key = requestMap["key"] as? String ?: ""
                        val value = requestMap["value"] as? String ?: ""
                        val success = SettingsManager.writeSetting(this, ns, key, value)
                        sendFramedMessage(output, mapOf("success" to success))
                    }
                    "get_accessibility_tree" -> {
                        val tree = MCPAccessibilityService.instance?.dumpTree() ?: mapOf("error" to "Service not running")
                        sendFramedMessage(output, mapOf("success" to true, "data" to tree))
                    }
                    "stream_notifications" -> {
                        // Takes over the socket for streaming
                        MCPNotificationListener.streamCallback = { notifData ->
                            try {
                                sendFramedMessage(output, notifData)
                            } catch (e: Exception) {
                                // client disconnected
                                MCPNotificationListener.streamCallback = null
                            }
                        }
                        // Block thread to keep socket open for streaming
                        while (MCPNotificationListener.streamCallback != null && isRunning) {
                            Thread.sleep(1000)
                        }
                        break 
                    }
                    else -> {
                        sendFramedMessage(output, mapOf("success" to false, "error" to "Unknown action"))
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("SystemMCP", "Client error: ${e.message}")
        } finally {
            client.close()
        }
    }

    private fun readFramedMessage(input: InputStream): String? {
        val lenBuf = ByteArray(4)
        var bytesRead = 0
        while (bytesRead < 4) {
            val count = input.read(lenBuf, bytesRead, 4 - bytesRead)
            if (count == -1) return null
            bytesRead += count
        }
        val length = ByteBuffer.wrap(lenBuf).int
        if (length > 10 * 1024 * 1024) return null // 10MB limit

        val payloadBuf = ByteArray(length)
        bytesRead = 0
        while (bytesRead < length) {
            val count = input.read(payloadBuf, bytesRead, length - bytesRead)
            if (count == -1) return null
            bytesRead += count
        }
        return String(payloadBuf, Charsets.UTF_8)
    }

    private fun sendFramedMessage(output: OutputStream, payload: Map<String, Any?>) {
        val jsonBytes = gson.toJson(payload).toByteArray(Charsets.UTF_8)
        val lenBuf = ByteBuffer.allocate(4).putInt(jsonBytes.size).array()
        output.write(lenBuf)
        output.write(jsonBytes)
        output.flush()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            "system_mcp_channel",
            "System MCP Background Service",
            NotificationManager.IMPORTANCE_LOW
        )
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    override fun onDestroy() {
        isRunning = false
        serverSocket?.close()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
