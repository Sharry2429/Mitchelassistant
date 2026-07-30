package com.systemmcp.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import androidx.core.app.NotificationCompat
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.EOFException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.ConcurrentHashMap

class MitchellService : Service() {

    private var authToken: String? = null
    private var serverSocket: ServerSocket? = null
    @Volatile
    private var isServerRunning = false
    private val activeClients = ConcurrentHashMap.newKeySet<DataOutputStream>()
    private val gson = Gson()
    private val serviceJob = Job()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    private var startTime: Long = 0
    private var totalRequests: Int = 0

    companion object {
        @Volatile
        var instance: MitchellService? = null
            private set

        @Volatile
        var isNotificationStreamingEnabled: Boolean = false

        fun broadcastNotification(payload: Map<String, Any?>) {
            val currentInstance = instance ?: return
            if (!isNotificationStreamingEnabled) return

            val jsonStr = currentInstance.gson.toJson(payload)
            currentInstance.broadcastToAllClients(jsonStr)
        }

        fun isRunning(): Boolean = instance?.isServerRunning == true
        fun getActiveToken(): String? = instance?.authToken
        fun getConnectedClientsCount(): Int = instance?.activeClients?.size ?: 0
        fun getTotalRequests(): Int = instance?.totalRequests ?: 0
        
        fun getUptimeMillis(): Long {
            val inst = instance ?: return 0
            return if (inst.isServerRunning) System.currentTimeMillis() - inst.startTime else 0
        }

        fun startCompanion(context: Context, token: String? = null) {
            val intent = Intent(context, MitchellService::class.java)
            if (!token.isNullOrEmpty()) {
                intent.putExtra("token", token)
                val prefs = context.getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE)
                prefs.edit().putString("auth_token", token).apply()
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stopCompanion(context: Context) {
            val intent = Intent(context, MitchellService::class.java)
            context.stopService(intent)
        }
    }

    private var wakeWordService: WakeWordService? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        registerBaseTools()
        OverlayService.registerTools()
        AudioStreamService.registerTools()
        AudioPlaybackService.registerTools()
        MitchellInCallService.registerTools()
        MitchellVoiceInteractionSession.registerTools()
        
        wakeWordService = WakeWordService(this)
        
        ToolRegistry.register("start_wake_word") {
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                wakeWordService?.startListening()
            }
            ToolRegistry.successResult(mapOf("message" to "Wake word listening started"))
        }

        ToolRegistry.register("stop_wake_word") {
            android.os.Handler(android.os.Looper.getMainLooper()).post {
                wakeWordService?.stopListening()
            }
            ToolRegistry.successResult(mapOf("message" to "Wake word listening stopped"))
        }
    }

    private fun registerBaseTools() {
        ToolRegistry.register("get_clipboard") {
            val service = MCPAccessibilityService.instance
                ?: throw Exception("MCPAccessibilityService is not enabled/connected")
            ToolRegistry.successResult(mapOf("text" to service.getClipboard()))
        }

        ToolRegistry.register("set_clipboard") { root ->
            val text = if (root.has("text") && !root.get("text").isJsonNull) root.get("text").asString else ""
            val service = MCPAccessibilityService.instance
                ?: throw Exception("MCPAccessibilityService is not enabled/connected")
            if (service.setClipboard(text)) {
                ToolRegistry.successResult(mapOf("message" to "Clipboard updated"))
            } else {
                ToolRegistry.errorResult("CLIPBOARD_FAILED", "Failed to update clipboard")
            }
        }

        ToolRegistry.register("write_setting") { root ->
            val type = if (root.has("type") && !root.get("type").isJsonNull) root.get("type").asString.lowercase() else "global"
            val key = if (root.has("key") && !root.get("key").isJsonNull) root.get("key").asString else throw Exception("Missing 'key'")
            val value = if (root.has("value") && !root.get("value").isJsonNull) root.get("value").asString else throw Exception("Missing 'value'")

            try {
                val success = when (type) {
                    "global" -> Settings.Global.putString(contentResolver, key, value)
                    "secure" -> Settings.Secure.putString(contentResolver, key, value)
                    "system" -> Settings.System.putString(contentResolver, key, value)
                    else -> false
                }
                if (success) {
                    ToolRegistry.successResult(mapOf("message" to "Setting '\$key' written successfully to \$type"))
                } else {
                    ToolRegistry.errorResult("SETTING_FAILED", "Failed to write setting '\$key' to \$type")
                }
            } catch (e: SecurityException) {
                ToolRegistry.errorResult("SECURITY_EXCEPTION", "WRITE_SECURE_SETTINGS permission required: \${e.message}")
            }
        }

        ToolRegistry.register("get_accessibility_tree") {
            val service = MCPAccessibilityService.instance
                ?: throw Exception("MCPAccessibilityService is not enabled/connected")
            val tree = service.dumpAccessibilityTree()
            if (tree != null) {
                ToolRegistry.successResult(mapOf("tree" to tree))
            } else {
                ToolRegistry.errorResult("EMPTY_TREE", "Active window root node is null or empty")
            }
        }

        ToolRegistry.register("stream_notifications") { root ->
            val enable = if (root.has("enable") && !root.get("enable").isJsonNull) root.get("enable").asBoolean else true
            isNotificationStreamingEnabled = enable
            ToolRegistry.successResult(
                mapOf(
                    "streaming" to enable,
                    "listenerConnected" to (MCPNotificationListener.instance != null)
                )
            )
        }

        ToolRegistry.register("start_macro_recording") {
            val service = MCPAccessibilityService.instance
                ?: throw Exception("MCPAccessibilityService is not enabled/connected")
            service.startRecording()
            ToolRegistry.successResult(mapOf("message" to "Macro recording started"))
        }

        ToolRegistry.register("stop_macro_recording") {
            val service = MCPAccessibilityService.instance
                ?: throw Exception("MCPAccessibilityService is not enabled/connected")
            val events = service.stopRecording()
            ToolRegistry.successResult(mapOf("events" to events))
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        var tokenFromIntent = intent?.getStringExtra("token")
            ?: intent?.getStringExtra("EXTRA_TOKEN")

        if (tokenFromIntent.isNullOrEmpty()) {
            val prefs = getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE)
            tokenFromIntent = prefs.getString("auth_token", null)
        } else {
            val prefs = getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE)
            prefs.edit().putString("auth_token", tokenFromIntent).apply()
        }

        authToken = tokenFromIntent
        startForegroundNotification()

        if (!isServerRunning) {
            isServerRunning = true
            startSocketServer()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        isServerRunning = false
        serviceJob.cancel()
        try {
            serverSocket?.close()
        } catch (_: Exception) {}
        if (instance == this) {
            instance = null
        }
    }

    private fun startForegroundNotification() {
        val channelId = "system_mcp_companion_channel"
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Mitchell AI Service",
                NotificationManager.IMPORTANCE_LOW
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification: Notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("Mitchell AI Active")
            .setContentText("Headless daemon listening on port 5000")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1001, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(1001, notification)
        }
    }

    private fun startSocketServer() {
        startTime = System.currentTimeMillis()
        totalRequests = 0
        serviceScope.launch {
            try {
                serverSocket = ServerSocket(5000, 50, InetAddress.getByName("127.0.0.1"))
                while (isServerRunning) {
                    val clientSocket = serverSocket?.accept() ?: break
                    serviceScope.launch {
                        handleClientConnection(clientSocket)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isServerRunning = false
            }
        }
    }

    private suspend fun handleClientConnection(socket: Socket) {
        var authenticated = authToken.isNullOrEmpty()
        var inputStream: DataInputStream? = null
        var outputStream: DataOutputStream? = null

        try {
            inputStream = DataInputStream(BufferedInputStream(socket.getInputStream()))
            outputStream = DataOutputStream(BufferedOutputStream(socket.getOutputStream()))
            activeClients.add(outputStream)

            while (isServerRunning && !socket.isClosed) {
                val length = try {
                    inputStream.readInt()
                } catch (_: EOFException) { break } catch (_: Exception) { break }

                if (length <= 0 || length > 10 * 1024 * 1024) break

                val buffer = ByteArray(length)
                inputStream.readFully(buffer)
                val jsonRequestStr = String(buffer, Charsets.UTF_8)
                
                totalRequests++
                
                val root = try {
                    gson.fromJson(jsonRequestStr, JsonObject::class.java)
                } catch (e: Exception) {
                    sendFrame(outputStream, ToolRegistry.errorResult("INVALID_JSON", "Invalid JSON payload").toString())
                    continue
                }

                if (root == null) {
                    sendFrame(outputStream, ToolRegistry.errorResult("INVALID_JSON", "Invalid JSON payload").toString())
                    continue
                }

                val action = root.get("action")?.asString
                if (action == null) {
                    sendFrame(outputStream, ToolRegistry.errorResult("MISSING_ACTION", "Missing 'action' field").toString())
                    continue
                }

                if (action == "handshake") {
                    val token = root.get("token")?.asString ?: ""
                    if (authToken.isNullOrEmpty() || token == authToken) {
                        authenticated = true
                        sendFrame(outputStream, ToolRegistry.successResult(mapOf("message" to "Handshake successful")).toString())
                    } else {
                        sendFrame(outputStream, ToolRegistry.errorResult("AUTH_FAILED", "Invalid authentication token").toString())
                    }
                    continue
                }

                if (!authenticated) {
                    sendFrame(outputStream, ToolRegistry.errorResult("UNAUTHORIZED", "Unauthorized. Send handshake first.").toString())
                    continue
                }

                val jsonResponse = ToolRegistry.execute(action, root)
                sendFrame(outputStream, jsonResponse.toString())
            }
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            if (outputStream != null) activeClients.remove(outputStream)
            try { socket.close() } catch (_: Exception) {}
        }
    }

    @Synchronized
    private fun sendFrame(dos: DataOutputStream, message: String) {
        val bytes = message.toByteArray(Charsets.UTF_8)
        dos.writeInt(bytes.size)
        dos.write(bytes)
        dos.flush()
    }

    fun broadcastToAllClients(jsonMsg: String) {
        val deadClients = mutableListOf<DataOutputStream>()
        for (clientDos in activeClients) {
            try {
                sendFrame(clientDos, jsonMsg)
            } catch (_: Exception) {
                deadClients.add(clientDos)
            }
        }
        if (deadClients.isNotEmpty()) {
            activeClients.removeAll(deadClients.toSet())
        }
    }
}
