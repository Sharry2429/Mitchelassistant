package com.systemmcp.companion

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import okhttp3.*
import okio.ByteString
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

class RelayClient(
    private val relayUrl: String,
    private val roomId: String,
    private val cryptoKeyBase64: String // For AES-GCM (Optional for now, but will implement)
) : WebSocketListener() {

    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()
    private val gson = Gson()
    private val TAG = "RelayClient"

    var isConnected = false
        private set

    fun connect() {
        val request = Request.Builder().url(relayUrl).build()
        webSocket = client.newWebSocket(request, this)
    }

    fun disconnect() {
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        isConnected = false
    }

    fun sendQuery(query: String) {
        if (!isConnected) return
        val payloadStr = JsonObject().apply {
            addProperty("type", "assistant_query")
            addProperty("query", query)
        }.toString()

        val replyMsg = JsonObject().apply {
            addProperty("type", "message")
            addProperty("room", roomId)
            addProperty("payload", payloadStr)
        }
        webSocket?.send(replyMsg.toString())
    }

    override fun onOpen(webSocket: WebSocket, response: Response) {
        Log.i(TAG, "Connected to Relay Server: $relayUrl")
        isConnected = true
        
        val registerPayload = JsonObject().apply {
            addProperty("type", "register")
            addProperty("role", "host")
            addProperty("room", roomId)
        }
        webSocket.send(registerPayload.toString())
    }

    override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
        super.onClosed(webSocket, code, reason)
        isConnected = false
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        try {
            val root = gson.fromJson(text, JsonObject::class.java)
            if (root.get("type")?.asString == "message") {
                val payloadStr = root.get("payload")?.asString
                if (payloadStr != null) {
                    val payload = gson.fromJson(payloadStr, JsonObject::class.java)
                    
                    val action = payload.get("action")?.asString
                    if (action != null) {
                        // Launch in coroutine to not block WebSocket thread
                        kotlinx.coroutines.GlobalScope.launch {
                            val response = ToolRegistry.execute(action, payload)
                            val replyMsg = JsonObject().apply {
                                addProperty("type", "message")
                                addProperty("room", roomId)
                                addProperty("payload", response.toString()) 
                            }
                            webSocket.send(replyMsg.toString())
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error processing relay message", e)
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        Log.e(TAG, "Relay Server connection failed", t)
        isConnected = false
    }
}
