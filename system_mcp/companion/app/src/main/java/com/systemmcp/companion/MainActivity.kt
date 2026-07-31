package com.systemmcp.companion

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.systemmcp.companion.ui.theme.MyApplicationTheme
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {}

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MyApplicationTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    SimpleDashboard(
                        requestPermissions = { perms -> requestPermissionLauncher.launch(perms) }
                    )
                }
            }
        }
    }
}

@Composable
fun SimpleDashboard(requestPermissions: (Array<String>) -> Unit) {
    val context = LocalContext.current
    var isConnected by remember { mutableStateOf(MitchellService.isRunning()) }
    var isEnabled by remember { mutableStateOf(Prefs.isEnabled(context)) }
    var authToken by remember { 
        mutableStateOf(
            context.getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE).getString("auth_token", null) ?: run {
                val newToken = java.util.UUID.randomUUID().toString().substring(0, 16)
                context.getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE).edit().putString("auth_token", newToken).apply()
                newToken
            }
        )
    }
    
    var isAssistantRole by remember { mutableStateOf(false) }
    var isOverlayGranted by remember { mutableStateOf(Settings.canDrawOverlays(context)) }
    var isCallPhoneGranted by remember { mutableStateOf(context.checkSelfPermission(android.Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) }
    var isBatteryExempt by remember { 
        mutableStateOf(
            (context.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager).isIgnoringBatteryOptimizations(context.packageName)
        )
    }

    LaunchedEffect(Unit) {
        while (true) {
            delay(1000)
            isConnected = MitchellService.isRunning()
            isOverlayGranted = Settings.canDrawOverlays(context)
            isCallPhoneGranted = context.checkSelfPermission(android.Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED
            val secureSettings = Settings.Secure.getString(context.contentResolver, "assistant")
            isAssistantRole = secureSettings?.contains(context.packageName) == true
            isBatteryExempt = (context.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager).isIgnoringBatteryOptimizations(context.packageName)
        }
    }

    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Mitchell AI Service: ${if (isConnected) "Running" else "Stopped"}", style = MaterialTheme.typography.titleLarge)
        
        Button(
            onClick = {
                val newState = !isConnected
                isEnabled = newState
                Prefs.setEnabled(context, newState)
                if (newState) {
                    MitchellService.startCompanion(context, authToken)
                } else {
                    MitchellService.stopCompanion(context)
                }
            },
            colors = ButtonDefaults.buttonColors(
                containerColor = if (isConnected) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
            ),
            modifier = Modifier.fillMaxWidth().height(64.dp)
        ) {
            Text(if (isConnected) "Stop Mitchell AI" else "Start Mitchell AI", style = MaterialTheme.typography.titleMedium)
        }

        OutlinedTextField(
            value = authToken,
            onValueChange = { 
                authToken = it
                context.getSharedPreferences("mcp_prefs", Context.MODE_PRIVATE).edit().putString("auth_token", it).apply()
            },
            label = { Text("Auth Token") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Divider()
        Text("Permissions", style = MaterialTheme.typography.titleMedium)

        PermissionRow("Assistant Role", isAssistantRole) {
            context.startActivity(Intent(Settings.ACTION_VOICE_INPUT_SETTINGS))
        }
        PermissionRow("System Overlay", isOverlayGranted) {
            context.startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION))
        }
        PermissionRow("Call Phone & Mic", isCallPhoneGranted) {
            requestPermissions(arrayOf(android.Manifest.permission.CALL_PHONE, android.Manifest.permission.READ_CALL_LOG, android.Manifest.permission.RECORD_AUDIO))
        }
        PermissionRow("Battery Exemption", isBatteryExempt) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = android.net.Uri.parse("package:${context.packageName}")
            }
            context.startActivity(intent)
        }
    }
}

@Composable
fun PermissionRow(name: String, isGranted: Boolean, onRequest: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
        Text(name)
        if (isGranted) {
            Text("Granted", color = MaterialTheme.colorScheme.primary)
        } else {
            Button(onClick = onRequest) { Text("Grant") }
        }
    }
}
