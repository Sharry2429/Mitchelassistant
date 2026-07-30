package com.systemmcp.companion

import android.app.assist.AssistStructure
import android.content.Context
import android.os.Bundle
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService

class MitchellVoiceInteractionSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: Bundle?): VoiceInteractionSession {
        return MitchellVoiceInteractionSession(this)
    }
}

class MitchellVoiceInteractionSession(context: Context) : VoiceInteractionSession(context) {
    companion object {
        var lastScreenContext: String = ""
        
        fun registerTools() {
            ToolRegistry.register("assistant_screen_context") {
                ToolRegistry.successResult(mapOf("screen_text" to lastScreenContext))
            }
        }
    }

    override fun onHandleAssist(
        data: Bundle?,
        structure: AssistStructure?,
        content: android.app.assist.AssistContent?
    ) {
        super.onHandleAssist(data, structure, content)
        
        if (structure != null) {
            lastScreenContext = parseAssistStructure(structure)
        } else {
            lastScreenContext = ""
        }
        
        // Notify python side that assistant was triggered
        val payload = mutableMapOf<String, Any?>("event" to "assistant_triggered")
        
        // Very basic parsing of structure could go here, or just send a signal
        // so Python side can call get_accessibility_tree
        payload["has_structure"] = structure != null
        payload["screen_text"] = lastScreenContext
        
        MitchellService.broadcastNotification(payload)
        
        // Close the session immediately so we don't block the screen
        hide()
    }

    private fun parseAssistStructure(structure: AssistStructure): String {
        val builder = java.lang.StringBuilder()
        val nodeCount = structure.windowNodeCount
        for (i in 0 until nodeCount) {
            val windowNode = structure.getWindowNodeAt(i)
            val rootNode = windowNode.rootViewNode
            if (rootNode != null) {
                traverseNode(rootNode, builder)
            }
        }
        return builder.toString()
    }

    private fun traverseNode(node: AssistStructure.ViewNode, builder: java.lang.StringBuilder) {
        if (node.text != null) {
            builder.append(node.text).append("\n")
        }
        if (node.contentDescription != null) {
            builder.append(node.contentDescription).append("\n")
        }
        for (i in 0 until node.childCount) {
            val child = node.getChildAt(i)
            if (child != null) {
                traverseNode(child, builder)
            }
        }
    }
}
