package com.systemmcp.companion

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import okhttp3.*
import okio.ByteString

class RelayClient(
    private val relayUrl: String,
    private val roomId: String,
    private val cryptoKeyBase64: String // For AES-GCM (Optional for now, but will implement)
) : WebSocketListener() {

    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()
    private val gson = Gson()
    private val TAG = "RelayClient"

    fun connect() {
        val request = Request.Builder().url(relayUrl).build()
        webSocket = client.newWebSocket(request, this)
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
    }

    override fun onOpen(webSocket: WebSocket, response: Response) {
        Log.i(TAG, "Connected to Relay Server: $relayUrl")
        
        // Register as host (The companion app is acting as the host for commands)
        val registerPayload = JsonObject().apply {
            addProperty("type", "register")
            addProperty("role", "host")
            addProperty("room", roomId)
        }
        webSocket.send(registerPayload.toString())
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        try {
            val root = gson.fromJson(text, JsonObject::class.java)
            if (root.get("type")?.asString == "message") {
                val payloadStr = root.get("payload")?.asString
                if (payloadStr != null) {
                    // TODO: Implement AES-GCM Decryption matching JS/Python
                    // For now, assume the payload is JSON string if testing without encryption
                    val payload = gson.fromJson(payloadStr, JsonObject::class.java)
                    
                    val action = payload.get("action")?.asString
                    if (action != null) {
                        val response = ToolRegistry.execute(action, payload)
                        
                        // Send back response
                        val replyMsg = JsonObject().apply {
                            addProperty("type", "message")
                            addProperty("room", roomId)
                            // TODO: Encrypt response
                            addProperty("payload", response.toString()) 
                        }
                        webSocket.send(replyMsg.toString())
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing relay message", e)
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        Log.e(TAG, "Relay Server connection failed", t)
    }
}
