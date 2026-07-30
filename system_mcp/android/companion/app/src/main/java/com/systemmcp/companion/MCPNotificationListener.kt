package com.systemmcp.companion

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class MCPNotificationListener : NotificationListenerService() {

    companion object {
        var instance: MCPNotificationListener? = null
        var streamCallback: ((Map<String, Any>) -> Unit)? = null
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        instance = this
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        instance = null
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        sbn?.let {
            val extras = it.notification.extras
            val title = extras.getString("android.title") ?: ""
            val text = extras.getCharSequence("android.text")?.toString() ?: ""
            
            val notifData = mapOf(
                "package" to it.packageName,
                "title" to title,
                "text" to text,
                "postTime" to it.postTime
            )
            
            streamCallback?.invoke(notifData)
        }
    }
}
