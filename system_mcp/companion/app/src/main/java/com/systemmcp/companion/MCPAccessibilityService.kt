package com.systemmcp.companion

import android.accessibilityservice.AccessibilityService
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Rect
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.accessibilityservice.GestureDescription
import android.graphics.Path

class MCPAccessibilityService : AccessibilityService() {

    companion object {
        @Volatile
        var instance: MCPAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) {
            instance = null
        }
    }

    private var isRecording = false
    private val recordedEvents = mutableListOf<Map<String, Any?>>()

    fun startRecording() {
        recordedEvents.clear()
        isRecording = true
    }

    fun stopRecording(): List<Map<String, Any?>> {
        isRecording = false
        return recordedEvents.toList()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!isRecording || event == null) return
        
        val eventType = event.eventType
        if (eventType == AccessibilityEvent.TYPE_VIEW_CLICKED ||
            eventType == AccessibilityEvent.TYPE_VIEW_LONG_CLICKED ||
            eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED ||
            eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            
            val eventMap = mutableMapOf<String, Any?>()
            eventMap["eventType"] = eventType
            eventMap["className"] = event.className?.toString() ?: ""
            eventMap["packageName"] = event.packageName?.toString() ?: ""
            eventMap["text"] = event.text.joinToString(" ")
            
            val node = try { event.source } catch (e: Exception) { null }
            if (node != null) {
                eventMap["viewIdResourceName"] = node.viewIdResourceName ?: ""
                val bounds = Rect()
                node.getBoundsInScreen(bounds)
                eventMap["boundsInScreen"] = bounds.flattenToString()
                node.recycle()
            }
            recordedEvents.add(eventMap)
        }
    }

    override fun onInterrupt() {
        // Handle interruption
    }

    fun getClipboard(): String {
        return try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clipData = clipboard.primaryClip
            if (clipData != null && clipData.itemCount > 0) {
                clipData.getItemAt(0).coerceToText(this).toString()
            } else {
                ""
            }
        } catch (e: Exception) {
            "Error getting clipboard: ${e.message}"
        }
    }

    fun setClipboard(text: String): Boolean {
        return try {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = ClipData.newPlainText("System-MCP Clipboard", text)
            clipboard.setPrimaryClip(clip)
            true
        } catch (e: Exception) {
            false
        }
    }

    fun performTap(x: Float, y: Float): Boolean {
        val path = Path()
        path.moveTo(x, y)
        val gestureBuilder = GestureDescription.Builder()
        val strokeDescription = GestureDescription.StrokeDescription(path, 0, 50)
        gestureBuilder.addStroke(strokeDescription)
        return dispatchGesture(gestureBuilder.build(), null, null)
    }

    fun performSwipe(x1: Float, y1: Float, x2: Float, y2: Float, duration: Long): Boolean {
        val path = Path()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        val gestureBuilder = GestureDescription.Builder()
        val strokeDescription = GestureDescription.StrokeDescription(path, 0, duration)
        gestureBuilder.addStroke(strokeDescription)
        return dispatchGesture(gestureBuilder.build(), null, null)
    }

    fun dumpAccessibilityTree(): Map<String, Any?>? {
        val rootNode = rootInActiveWindow ?: return null
        return try {
            parseNode(rootNode)
        } finally {
            rootNode.recycle()
        }
    }

    private fun parseNode(node: AccessibilityNodeInfo?): Map<String, Any?>? {
        if (node == null) return null

        val nodeMap = mutableMapOf<String, Any?>()
        nodeMap["className"] = node.className?.toString() ?: ""
        nodeMap["packageName"] = node.packageName?.toString() ?: ""
        nodeMap["text"] = node.text?.toString() ?: ""
        nodeMap["contentDescription"] = node.contentDescription?.toString() ?: ""
        nodeMap["viewIdResourceName"] = node.viewIdResourceName ?: ""

        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        nodeMap["boundsInScreen"] = bounds.flattenToString()

        nodeMap["isClickable"] = node.isClickable
        nodeMap["isEnabled"] = node.isEnabled
        nodeMap["isFocused"] = node.isFocused
        nodeMap["isScrollable"] = node.isScrollable

        val childrenList = mutableListOf<Map<String, Any?>>()
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                val childMap = parseNode(child)
                if (childMap != null) {
                    childrenList.add(childMap)
                }
                child.recycle()
            }
        }
        if (childrenList.isNotEmpty()) {
            nodeMap["children"] = childrenList
        }

        return nodeMap
    }
}
