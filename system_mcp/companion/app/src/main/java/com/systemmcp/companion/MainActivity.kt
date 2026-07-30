package com.systemmcp.companion

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.systemmcp.companion.ui.theme.MyApplicationTheme
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        // Handle post-request
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    DashboardScreen(
                        modifier = Modifier.padding(innerPadding),
                        requestPermissions = { perms -> requestPermissionLauncher.launch(perms) }
                    )
                }
            }
        }
    }
}

// Data class for StreamDeck Buttons
data class StreamDeckButton(val id: Int, val label: String, val toolName: String)

@Composable
fun DashboardScreen(modifier: Modifier = Modifier, requestPermissions: (Array<String>) -> Unit) {
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current
    var isConnected by remember { mutableStateOf(MitchellService.isRunning()) }
    
    // We mock the stream deck buttons here to match OverlayService's currentButtons
    // In a real app we'd map OverlayService.currentButtons to StreamDeckButton
    var streamDeckButtons by remember {
        mutableStateOf(
            OverlayService.currentButtons.mapIndexed { index, map ->
                StreamDeckButton(index, map["label"] ?: "Btn", map["tool_name"] ?: "tool")
            }
        )
    }

    var isAssistantRole by remember { mutableStateOf(false) }
    var isOverlayGranted by remember { mutableStateOf(Settings.canDrawOverlays(context)) }
    var isCallPhoneGranted by remember { 
        mutableStateOf(context.checkSelfPermission(android.Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) 
    }

    LaunchedEffect(Unit) {
        while (true) {
            delay(1000)
            isConnected = MitchellService.isRunning()
            isOverlayGranted = Settings.canDrawOverlays(context)
            isCallPhoneGranted = context.checkSelfPermission(android.Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED
            // Check assistant role (naive check by getting default assistant)
            val secureSettings = Settings.Secure.getString(context.contentResolver, "assistant")
            isAssistantRole = secureSettings?.contains(context.packageName) == true
        }
    }

    var currentTab by remember { mutableStateOf("dashboard") }

    Column(modifier = modifier.fillMaxSize()) {
        if (currentTab == "dashboard") {
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .background(MaterialTheme.colorScheme.background)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(24.dp)
            ) {
                item {
                    HeaderSection(isConnected = isConnected) {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        if (isConnected) {
                            MitchellService.stopCompanion(context)
                        } else {
                            MitchellService.startCompanion(context, "system_mcp_secret")
                        }
                        isConnected = !isConnected
                    }
                }

                item {
                    PermissionsSection(
                        isAssistantRole = isAssistantRole,
                        isOverlayGranted = isOverlayGranted,
                        isCallPhoneGranted = isCallPhoneGranted,
                        onRequestAssistant = {
                            val intent = Intent(Settings.ACTION_VOICE_INPUT_SETTINGS)
                            context.startActivity(intent)
                        },
                        onRequestOverlay = {
                            val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                            context.startActivity(intent)
                        },
                        onRequestCallPhone = {
                            requestPermissions(arrayOf(android.Manifest.permission.CALL_PHONE, android.Manifest.permission.READ_CALL_LOG, android.Manifest.permission.RECORD_AUDIO))
                        }
                    )
                }
            }
        } else {
            androidx.compose.ui.viewinterop.AndroidView(
                modifier = Modifier.weight(1f),
                factory = { ctx ->
                    android.webkit.WebView(ctx).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        webViewClient = android.webkit.WebViewClient()
                        loadUrl("file:///android_asset/www/index.html")
                    }
                }
            )
        }

        // Bottom Navigation
        NavigationBar {
            NavigationBarItem(
                icon = { Icon(Icons.Default.CheckCircle, contentDescription = "Dashboard") },
                label = { Text("Dashboard") },
                selected = currentTab == "dashboard",
                onClick = { currentTab = "dashboard" }
            )
            NavigationBarItem(
                icon = { Icon(Icons.Default.Call, contentDescription = "Remote") },
                label = { Text("Remote") },
                selected = currentTab == "remote",
                onClick = { currentTab = "remote" }
            )
        }
    }
}

@Composable
fun HeaderSection(isConnected: Boolean, onToggleConnection: () -> Unit) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )
    val pulseOpacity by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseOpacity"
    )

    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 12.dp).clickable { onToggleConnection() }) {
        Text(
            text = "BRIDGE CONNECTION",
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.sp,
                color = MaterialTheme.colorScheme.primary
            )
        )
        Spacer(modifier = Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .clip(CircleShape)
                    .background(if (isConnected) MaterialTheme.colorScheme.primary.copy(alpha = pulseOpacity) else Color.Red.copy(alpha = pulseOpacity))
                    .scale(if (isConnected) pulseScale else 1f),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(if (isConnected) MaterialTheme.colorScheme.primary else Color.Red)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Mitchell AI",
                style = MaterialTheme.typography.titleLarge.copy(
                    fontWeight = FontWeight.Medium
                ),
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "v2.5",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun PermissionsSection(
    isAssistantRole: Boolean,
    isOverlayGranted: Boolean,
    isCallPhoneGranted: Boolean,
    onRequestAssistant: () -> Unit,
    onRequestOverlay: () -> Unit,
    onRequestCallPhone: () -> Unit
) {
    val haptic = LocalHapticFeedback.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(28.dp))
            .background(MaterialTheme.colorScheme.surface)
            .border(1.dp, MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(28.dp))
            .padding(20.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "System Permissions",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = "System Healthy",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                color = Color(0xFF34D399),
                modifier = Modifier
                    .background(Color(0x1A34D399), CircleShape)
                    .border(1.dp, Color(0x3334D399), CircleShape)
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            )
        }
        PermissionItem(
            name = "Assistant Role", 
            subtitle = "Required for voice trigger", 
            icon = Icons.Default.Mic, 
            isGranted = isAssistantRole, 
            haptic = haptic, 
            tintColor = MaterialTheme.colorScheme.primary,
            onRequest = onRequestAssistant
        )
        Spacer(modifier = Modifier.height(12.dp))
        PermissionItem(
            name = "System Overlay", 
            subtitle = "Display floating controls", 
            icon = Icons.Default.Warning, 
            isGranted = isOverlayGranted, 
            haptic = haptic, 
            tintColor = MaterialTheme.colorScheme.tertiary,
            onRequest = onRequestOverlay
        )
        Spacer(modifier = Modifier.height(12.dp))
        PermissionItem(
            name = "Call Phone & Mic", 
            subtitle = if (isCallPhoneGranted) "Granted" else "Permission missing", 
            icon = Icons.Default.Call, 
            isGranted = isCallPhoneGranted, 
            haptic = haptic, 
            tintColor = Color(0xFFF87171),
            onRequest = onRequestCallPhone
        )
    }
}

@Composable
fun PermissionItem(
    name: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    isGranted: Boolean,
    haptic: androidx.compose.ui.hapticfeedback.HapticFeedback,
    tintColor: Color,
    onRequest: () -> Unit
) {
    var pressed by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(targetValue = if (pressed) 0.95f else 1f, label = "scale")

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .scale(scale)
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(
                1.dp,
                if (!isGranted) tintColor.copy(alpha = 0.2f) else Color.Transparent,
                RoundedCornerShape(16.dp)
            )
            .clickable {
                if (!isGranted) {
                    haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                    pressed = true
                    onRequest()
                }
            }
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(tintColor.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = tintColor,
                    modifier = Modifier.size(24.dp)
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(text = name, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium), color = MaterialTheme.colorScheme.onBackground)
                Text(text = subtitle, style = MaterialTheme.typography.labelSmall, color = if (!isGranted) tintColor.copy(alpha = 0.8f) else MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        if (isGranted) {
            Box(
                modifier = Modifier
                    .size(24.dp)
                    .clip(CircleShape)
                    .background(Color(0x3334D399)),
                contentAlignment = Alignment.Center
            ) {
                Icon(imageVector = Icons.Default.CheckCircle, contentDescription = "Granted", tint = Color(0xFF34D399), modifier = Modifier.size(16.dp))
            }
        } else {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(tintColor.copy(alpha = 0.1f))
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            ) {
                Text("GRANT", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = tintColor)
            }
        }
    }
    
    LaunchedEffect(pressed) {
        if (pressed) {
            kotlinx.coroutines.delay(100)
            pressed = false
        }
    }
}

@Composable
fun StreamDeckEditorSection(buttons: List<StreamDeckButton>, onAdd: () -> Unit, onDelete: (Int) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(28.dp))
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.2f),
                        MaterialTheme.colorScheme.tertiary.copy(alpha = 0.2f)
                    )
                )
            )
            .border(1.dp, MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(28.dp))
            .padding(20.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Bridge Registry",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Active",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Medium),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "StreamDeck Tools",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            IconButton(
                onClick = onAdd,
                modifier = Modifier.size(24.dp)
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Button", tint = MaterialTheme.colorScheme.primary)
            }
        }

        buttons.forEach { button ->
            StreamDeckEditItem(button, onDelete)
            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

@Composable
fun StreamDeckEditItem(button: StreamDeckButton, onDelete: (Int) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, Color(0x1AFFFFFF), RoundedCornerShape(16.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column {
            Text(text = button.label, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium), color = MaterialTheme.colorScheme.onBackground)
            Text(text = button.toolName, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Row {
            IconButton(onClick = { /* Edit Action */ }, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Default.Edit, contentDescription = "Edit", tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
            }
            IconButton(onClick = { onDelete(button.id) }, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFF87171), modifier = Modifier.size(16.dp))
            }
        }
    }
}
