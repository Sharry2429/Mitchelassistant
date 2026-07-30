package com.systemmcp.companion

import android.content.Context
import android.util.Log

class MitchellRouter(private val context: Context) {
    private val standaloneAgent = AgentLoop(context)
    private val TAG = "MitchellRouter"

    fun processQuery(query: String, onUpdate: (String) -> Unit) {
        if (MitchellService.isRelayConnected()) {
            Log.i(TAG, "Routing query to PC via Relay: $query")
            // In a real app we'd wait for a callback from WebSocket to update UI
            // For now, we simulate handing off the query
            MitchellService.sendRemoteQuery(query)
            onUpdate("Sent to PC Mitchell...")
        } else {
            Log.i(TAG, "Routing query to Standalone LLM: $query")
            standaloneAgent.sendMessage(query, onUpdate)
        }
    }
}
