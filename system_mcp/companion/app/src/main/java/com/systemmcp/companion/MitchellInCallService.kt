package com.systemmcp.companion

import android.telecom.Call
import android.telecom.InCallService
import java.util.concurrent.ConcurrentHashMap

class MitchellInCallService : InCallService() {

    companion object {
        val activeCalls = ConcurrentHashMap<String, Call>()

        fun registerTools() {
            ToolRegistry.register("call_answer") { root ->
                val callId = if (root.has("call_id") && !root.get("call_id").isJsonNull) root.get("call_id").asString else activeCalls.keys.firstOrNull() ?: throw Exception("No active call")
                val call = activeCalls[callId] ?: throw Exception("Call not found")
                call.answer(0) // VideoProfile.STATE_AUDIO_ONLY = 0
                ToolRegistry.successResult(mapOf("message" to "Call answered"))
            }

            ToolRegistry.register("call_reject") { root ->
                val callId = if (root.has("call_id") && !root.get("call_id").isJsonNull) root.get("call_id").asString else activeCalls.keys.firstOrNull() ?: throw Exception("No active call")
                val call = activeCalls[callId] ?: throw Exception("Call not found")
                call.reject(false, null)
                ToolRegistry.successResult(mapOf("message" to "Call rejected"))
            }

            ToolRegistry.register("call_hangup") { root ->
                val callId = if (root.has("call_id") && !root.get("call_id").isJsonNull) root.get("call_id").asString else activeCalls.keys.firstOrNull() ?: throw Exception("No active call")
                val call = activeCalls[callId] ?: throw Exception("Call not found")
                call.disconnect()
                ToolRegistry.successResult(mapOf("message" to "Call disconnected"))
            }
        }
    }

    private val callCallback = object : Call.Callback() {
        override fun onStateChanged(call: Call, state: Int) {
            super.onStateChanged(call, state)
            broadcastCallState(call, state)
        }
    }

    override fun onCallAdded(call: Call) {
        super.onCallAdded(call)
        val callId = call.details.handle?.schemeSpecificPart ?: call.hashCode().toString()
        activeCalls[callId] = call
        call.registerCallback(callCallback)
        broadcastCallState(call, call.state)
    }

    override fun onCallRemoved(call: Call) {
        super.onCallRemoved(call)
        val callId = call.details.handle?.schemeSpecificPart ?: call.hashCode().toString()
        activeCalls.remove(callId)
        call.unregisterCallback(callCallback)

        val payload = mapOf(
            "event" to "call_removed",
            "call_id" to callId
        )
        MitchellService.broadcastNotification(payload)
    }

    private fun broadcastCallState(call: Call, state: Int) {
        val callId = call.details.handle?.schemeSpecificPart ?: call.hashCode().toString()
        val callerName = call.details.callerDisplayName ?: "Unknown"
        val stateName = when (state) {
            Call.STATE_RINGING -> "RINGING"
            Call.STATE_ACTIVE -> "ACTIVE"
            Call.STATE_DIALING -> "DIALING"
            Call.STATE_DISCONNECTED -> "DISCONNECTED"
            Call.STATE_HOLDING -> "HOLDING"
            Call.STATE_NEW -> "NEW"
            else -> "UNKNOWN"
        }
        val payload = mapOf(
            "event" to "call_state_changed",
            "call_id" to callId,
            "state" to stateName,
            "caller_name" to callerName
        )
        MitchellService.broadcastNotification(payload)
    }
}
