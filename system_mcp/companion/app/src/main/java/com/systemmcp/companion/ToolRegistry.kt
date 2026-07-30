package com.systemmcp.companion

import com.google.gson.Gson
import com.google.gson.JsonObject
import java.util.concurrent.ConcurrentHashMap

object ToolRegistry {
    private val tools = ConcurrentHashMap<String, suspend (JsonObject) -> JsonObject>()
    val gson = Gson()

    fun register(name: String, handler: suspend (JsonObject) -> JsonObject) {
        tools[name] = handler
    }

    suspend fun execute(name: String, params: JsonObject): JsonObject {
        val handler = tools[name]
        return if (handler != null) {
            try {
                handler.invoke(params)
            } catch (e: Exception) {
                errorResult("TOOL_EXECUTION_ERROR", e.message ?: "Unknown error")
            }
        } else {
            errorResult("UNKNOWN_TOOL", "Tool not found: $name")
        }
    }

    fun successResult(data: Map<String, Any?> = emptyMap()): JsonObject {
        val response = mutableMapOf<String, Any?>("status" to "ok")
        response.putAll(data)
        return gson.toJsonTree(response).asJsonObject
    }

    fun errorResult(code: String, message: String): JsonObject {
        val response = mapOf(
            "status" to "error",
            "code" to code,
            "message" to message
        )
        return gson.toJsonTree(response).asJsonObject
    }
}
