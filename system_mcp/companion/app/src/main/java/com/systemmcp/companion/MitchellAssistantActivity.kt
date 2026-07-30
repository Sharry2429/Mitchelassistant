package com.systemmcp.companion

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.systemmcp.companion.ui.theme.MyApplicationTheme

class MitchellAssistantActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Notify Python that the assistant was invoked
        val payload = mapOf("event" to "assistant_triggered")
        MitchellService.broadcastNotification(payload)

        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                AssistantOverlay(onDismiss = { finish() })
            }
        }
    }
}
