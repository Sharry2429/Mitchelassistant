package com.systemmcp.companion

import android.accessibilityservice.AccessibilityService
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class MCPAccessibilityService : AccessibilityService() {

    companion object {
        var instance: MCPAccessibilityService? = null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // We can capture events here, but for now we just dump tree on demand
    }

    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        instance = null
    }

    // --- Exposed Capabilities ---

    fun getClipboardData(): String {
        var text = ""
        // Clipboard must be accessed from the main thread
        val handler = Handler(Looper.getMainLooper())
        val lock = java.lang.Object()
        
        handler.post {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            if (clipboard.hasPrimaryClip()) {
                val clip = clipboard.primaryClip
                if (clip != null && clip.itemCount > 0) {
                    text = clip.getItemAt(0).text?.toString() ?: ""
                }
            }
            synchronized(lock) {
                lock.notify()
            }
        }
        
        synchronized(lock) {
            lock.wait(2000)
        }
        return text
    }

    fun setClipboardData(text: String) {
        val handler = Handler(Looper.getMainLooper())
        handler.post {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("SystemMCP", text)
            clipboard.setPrimaryClip(clip)
        }
    }

    fun dumpTree(): Map<String, Any> {
        val rootNode = rootInActiveWindow ?: return mapOf("error" to "No active window")
        return serializeNode(rootNode)
    }

    private fun serializeNode(node: AccessibilityNodeInfo?): Map<String, Any> {
        if (node == null) return emptyMap()

        val map = mutableMapOf<String, Any>()
        map["class"] = node.className?.toString() ?: ""
        map["text"] = node.text?.toString() ?: ""
        map["description"] = node.contentDescription?.toString() ?: ""
        map["clickable"] = node.isClickable
        map["scrollable"] = node.isScrollable
        map["enabled"] = node.isEnabled
        
        val bounds = android.graphics.Rect()
        node.getBoundsInScreen(bounds)
        map["bounds"] = listOf(bounds.left, bounds.top, bounds.right, bounds.bottom)

        val children = mutableListOf<Map<String, Any>>()
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                children.add(serializeNode(child))
                child.recycle()
            }
        }
        if (children.isNotEmpty()) {
            map["children"] = children
        }

        return map
    }
}
