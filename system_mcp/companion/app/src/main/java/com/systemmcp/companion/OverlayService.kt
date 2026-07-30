package com.systemmcp.companion

import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.ViewTreeObserver
import android.view.WindowManager
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.lifecycle.setViewTreeViewModelStoreOwner
import androidx.savedstate.SavedStateRegistry
import androidx.savedstate.SavedStateRegistryController
import androidx.savedstate.SavedStateRegistryOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.google.gson.reflect.TypeToken
import com.systemmcp.companion.ui.theme.MyApplicationTheme

class OverlayService : Service(), LifecycleOwner, SavedStateRegistryOwner, ViewModelStoreOwner {
    companion object {
        var isOverlayVisible = false
        var currentButtons = mutableListOf<Map<String, String>>()
        private var instance: OverlayService? = null
        
        fun showOverlay(context: Context) {
            val intent = Intent(context, OverlayService::class.java)
            context.startService(intent)
        }

        fun hideOverlay(context: Context) {
            val intent = Intent(context, OverlayService::class.java)
            context.stopService(intent)
        }
        
        fun updateButtons(buttons: List<Map<String, String>>) {
            currentButtons.clear()
            currentButtons.addAll(buttons)
        }

        fun registerTools() {
            ToolRegistry.register("overlay_show") {
                val context = MitchellService.instance ?: throw Exception("MitchellService not running")
                showOverlay(context)
                ToolRegistry.successResult(mapOf("message" to "Overlay shown"))
            }

            ToolRegistry.register("overlay_hide") {
                val context = MitchellService.instance ?: throw Exception("MitchellService not running")
                hideOverlay(context)
                ToolRegistry.successResult(mapOf("message" to "Overlay hidden"))
            }

            ToolRegistry.register("overlay_set_buttons") { root ->
                if (!root.has("buttons") || root.get("buttons").isJsonNull) {
                    throw Exception("Missing 'buttons' array")
                }
                val type = object : TypeToken<List<Map<String, String>>>() {}.type
                val buttons: List<Map<String, String>> = ToolRegistry.gson.fromJson(root.get("buttons"), type)
                updateButtons(buttons)
                ToolRegistry.successResult(mapOf("message" to "Buttons updated"))
            }

            ToolRegistry.register("overlay_get_buttons") {
                ToolRegistry.successResult(mapOf("buttons" to currentButtons))
            }
        }
    }

    private lateinit var windowManager: WindowManager
    private lateinit var composeView: ComposeView
    
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val savedStateRegistryController = SavedStateRegistryController.create(this)
    private val _viewModelStore = ViewModelStore()
    
    override val savedStateRegistry: SavedStateRegistry get() = savedStateRegistryController.savedStateRegistry
    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val viewModelStore: ViewModelStore get() = _viewModelStore

    override fun onCreate() {
        super.onCreate()
        instance = this
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)

        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or 
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or 
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
            WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
            PixelFormat.TRANSLUCENT
        )

        params.gravity = Gravity.CENTER

        composeView = ComposeView(this).apply {
            setContent {
                MyApplicationTheme {
                    AssistantOverlay(onDismiss = { hideOverlay(this@OverlayService) })
                }
            }
        }

        // Setup ViewTree dependencies for Compose
        composeView.setViewTreeLifecycleOwner(this)
        composeView.setViewTreeSavedStateRegistryOwner(this)
        composeView.setViewTreeViewModelStoreOwner(this)

        windowManager.addView(composeView, params)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
        isOverlayVisible = true
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
        if (this::composeView.isInitialized) {
            windowManager.removeView(composeView)
        }
        isOverlayVisible = false
        if (instance == this) instance = null
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
