package com.systemmcp.companion

import android.content.Context
import android.util.Log

class MitchellRouter(private val context: Context) {
    private val standaloneAgent = AgentLoop(context)
    private val TAG = "MitchellRouter"

    fun processQuery(query: String, onUpdate: (String) -> Unit) {
        standaloneAgent.sendMessage(query, onUpdate)
    }
}
