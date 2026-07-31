package com.systemmcp.companion

import android.app.assist.AssistStructure
import android.content.Context
import android.os.Bundle
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import android.view.View
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.unit.dp
import com.systemmcp.companion.ui.theme.MyApplicationTheme

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

    override fun onCreateContentView(): View {
        return ComposeView(context).apply {
            setContent {
                MyApplicationTheme {
                    AssistantOverlayUI(onClose = { hide() })
                }
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
        
        // Notify python/kotlin side that assistant was triggered
        val payload = mutableMapOf<String, Any?>("event" to "assistant_triggered")
        payload["has_structure"] = structure != null
        payload["screen_text"] = lastScreenContext
        
        MitchellService.broadcastNotification(payload)
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

@Composable
fun AssistantOverlayUI(onClose: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var query by remember { mutableStateOf("") }
    
    // Dynamic routing states
    val subtitleText = "Standalone LLM Active"
    val placeholderText = "Ask Mitchell..."
    val indicatorColor = Color(0xFF60A5FA)

    var responseText by remember { mutableStateOf(subtitleText) }
    val router = remember { MitchellRouter(context) }
    
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.BottomCenter) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.4f))
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                .background(MaterialTheme.colorScheme.surface)
                .padding(24.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .clip(androidx.compose.foundation.shape.CircleShape)
                        .background(indicatorColor)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Mitchell AI (God-Mode)",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(text = responseText, style = MaterialTheme.typography.bodyLarge)
            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text(placeholderText) },
                shape = RoundedCornerShape(16.dp)
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Button(onClick = onClose) {
                    Text("Close")
                }
                Button(onClick = {
                    if (query.isNotEmpty()) {
                        responseText = "Routing query..."
                        val q = query
                        query = ""
                        router.processQuery(q) { update ->
                            if (context is android.app.Activity) {
                                context.runOnUiThread { responseText = update }
                            } else {
                                responseText = update
                            }
                        }
                    }
                }) {
                    Text("Send")
                }
            }
        }
    }
}
