package com.systemmcp.companion

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class AgentLoop(private val context: Context) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val TAG = "AgentLoop"
    private val API_URL = "https://api.aicredits.in/v1/chat/completions"

    private val conversationHistory = JsonArray()

    init {
        val systemPrompt = JsonObject().apply {
            addProperty("role", "system")
            addProperty("content", "You are Mitchell AI, a standalone Android God-Mode assistant. You can control the device and execute shell commands using Shizuku. Keep answers short and concise.")
        }
        conversationHistory.add(systemPrompt)
    }

    fun sendMessage(userMessage: String, onUpdate: (String) -> Unit) {
        val apiKey = ApiKeyManager.getApiKey(context)
        if (apiKey.isNullOrEmpty()) {
            onUpdate("Error: API Key not set. Please set it in the Dashboard.")
            return
        }

        val userMsgObj = JsonObject().apply {
            addProperty("role", "user")
            addProperty("content", userMessage)
        }
        conversationHistory.add(userMsgObj)

        executeLLMCall(apiKey, onUpdate)
    }

    private fun executeLLMCall(apiKey: String, onUpdate: (String) -> Unit) {
        // Build the request body with tool definitions
        val requestBody = JsonObject().apply {
            addProperty("model", "gpt-4o-mini") // Adjust model as necessary
            add("messages", conversationHistory)
            
            // Define tools (just an example for shizuku_shell and get_clipboard)
            val toolsArray = JsonArray()
            
            val shizukuTool = JsonObject().apply {
                addProperty("type", "function")
                val functionObj = JsonObject().apply {
                    addProperty("name", "shizuku_shell")
                    addProperty("description", "Execute an ADB shell command locally.")
                    val params = JsonObject().apply {
                        addProperty("type", "object")
                        val props = JsonObject().apply {
                            val cmdObj = JsonObject().apply {
                                addProperty("type", "string")
                            }
                            add("command", cmdObj)
                        }
                        add("properties", props)
                        val reqArray = JsonArray().apply { add("command") }
                        add("required", reqArray)
                    }
                    add("parameters", params)
                }
                add("function", functionObj)
            }
            toolsArray.add(shizukuTool)
            add("tools", toolsArray)
        }

        val body = requestBody.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(API_URL)
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "LLM API Call failed", e)
                onUpdate("Network Error: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!response.isSuccessful) {
                        onUpdate("API Error: ${response.code}")
                        return
                    }

                    val responseBodyStr = response.body?.string()
                    if (responseBodyStr != null) {
                        try {
                            val responseJson = gson.fromJson(responseBodyStr, JsonObject::class.java)
                            val choice = responseJson.getAsJsonArray("choices").get(0).asJsonObject
                            val message = choice.getAsJsonObject("message")
                            
                            conversationHistory.add(message) // add assistant message to history

                            if (message.has("tool_calls")) {
                                val toolCalls = message.getAsJsonArray("tool_calls")
                                onUpdate("Executing tool...")
                                handleToolCalls(toolCalls, apiKey, onUpdate)
                            } else {
                                val content = message.get("content").asString
                                onUpdate(content)
                            }

                        } catch (e: Exception) {
                            Log.e(TAG, "Error parsing response", e)
                            onUpdate("Error parsing response")
                        }
                    }
                }
            }
        })
    }

    private fun handleToolCalls(toolCalls: JsonArray, apiKey: String, onUpdate: (String) -> Unit) {
        Thread {
            for (i in 0 until toolCalls.size()) {
                val toolCall = toolCalls.get(i).asJsonObject
                val id = toolCall.get("id").asString
                val function = toolCall.getAsJsonObject("function")
                val name = function.get("name").asString
                val args = gson.fromJson(function.get("arguments").asString, JsonObject::class.java)

                Log.d(TAG, "Executing tool: $name with args $args")
                
                // We use coroutines properly in production, using runBlocking here for simplicity
                val resultObj = kotlinx.coroutines.runBlocking {
                    ToolRegistry.execute(name, args)
                }

                val toolMessage = JsonObject().apply {
                    addProperty("role", "tool")
                    addProperty("tool_call_id", id)
                    addProperty("content", resultObj.toString())
                }
                conversationHistory.add(toolMessage)
            }
            // Once all tools are executed, call LLM again to get final response
            executeLLMCall(apiKey, onUpdate)
        }.start()
    }
}
