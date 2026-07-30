package com.systemmcp.companion

import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Composable
fun AssistantOverlay(onDismiss: () -> Unit) {
    var isVisible by remember { mutableStateOf(false) }
    
    LaunchedEffect(Unit) {
        isVisible = true
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                detectTapGestures(onTap = { 
                    isVisible = false
                })
            },
        contentAlignment = Alignment.BottomCenter
    ) {
        AnimatedVisibility(
            visible = isVisible,
            enter = fadeIn(tween(400)) + slideInVertically(initialOffsetY = { it / 2 }, animationSpec = tween(400, easing = EaseOutExpo)),
            exit = fadeOut(tween(300)) + slideOutVertically(targetOffsetY = { it }, animationSpec = tween(300, easing = EaseInExpo))
        ) {
            OverlayContent(onDismiss = onDismiss)
        }
    }
    
    LaunchedEffect(isVisible) {
        if (!isVisible) {
            delay(300)
            onDismiss()
        }
    }
}

@Composable
fun OverlayContent(onDismiss: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 32.dp)
            .clip(RoundedCornerShape(40.dp))
            .background(Color(0x99000000)) // Translucent black background for visibility
            .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(40.dp))
            .pointerInput(Unit) { detectTapGestures(onTap = { /* consume taps to not dismiss */ }) }
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .width(48.dp)
                .height(6.dp)
                .clip(CircleShape)
                .background(Color(0x4DFFFFFF))
        )
        Spacer(modifier = Modifier.height(16.dp))
        FloatingOrb()
        Spacer(modifier = Modifier.height(24.dp))
        StreamDeckGrid()
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "HOLD TO LISTEN",
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Medium, letterSpacing = 2.sp),
            color = Color(0x99FFFFFF)
        )
    }
}

enum class AssistantState {
    IDLE, LISTENING, THINKING
}

@Composable
fun FloatingOrb() {
    var state by remember { mutableStateOf(AssistantState.IDLE) }
    val haptic = LocalHapticFeedback.current
    val context = LocalContext.current

    val infiniteTransition = rememberInfiniteTransition(label = "orbPulse")
    
    val idleScale by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = EaseInOutSine),
            repeatMode = RepeatMode.Reverse
        ),
        label = "idleScale"
    )
    
    val morphRotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "morphRotation"
    )
    
    val morphScale by infiniteTransition.animateFloat(
        initialValue = 1.1f,
        targetValue = 1.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = EaseInOutQuad),
            repeatMode = RepeatMode.Reverse
        ),
        label = "morphScale"
    )

    val currentScale = when (state) {
        AssistantState.IDLE -> idleScale
        AssistantState.LISTENING -> morphScale
        AssistantState.THINKING -> morphScale * 0.9f
    }
    
    val currentRotation = if (state != AssistantState.IDLE) morphRotation else 0f

    val color1 = MaterialTheme.colorScheme.primary
    val color2 = MaterialTheme.colorScheme.secondary
    val color3 = MaterialTheme.colorScheme.tertiary
    
    Box(
        modifier = Modifier
            .size(80.dp)
            .scale(currentScale)
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = {
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        state = AssistantState.LISTENING
                        
                        // Fire wake word start
                        ToolRegistry.execute("start_wake_word", com.google.gson.JsonObject())
                        
                        tryAwaitRelease()
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        state = AssistantState.THINKING
                        
                        // Fire wake word stop
                        ToolRegistry.execute("stop_wake_word", com.google.gson.JsonObject())
                        
                        delay(2000)
                        state = AssistantState.IDLE
                    }
                )
            }
            .pointerInput(Unit) {
                var dragOffset = androidx.compose.ui.geometry.Offset.Zero
                detectDragGestures(
                    onDragStart = { dragOffset = androidx.compose.ui.geometry.Offset.Zero },
                    onDragEnd = {
                        val threshold = 50f
                        if (dragOffset.x > threshold) {
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            Toast.makeText(context, "Switched Profile", Toast.LENGTH_SHORT).show()
                        } else if (dragOffset.x < -threshold) {
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            Toast.makeText(context, "Context Cleared", Toast.LENGTH_SHORT).show()
                        }
                    },
                    onDrag = { change, dragAmount -> 
                        change.consume()
                        dragOffset += dragAmount
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .clip(CircleShape)
                .background(
                    if (state == AssistantState.LISTENING) color3.copy(alpha = 0.4f)
                    else if (state == AssistantState.THINKING) color2.copy(alpha = 0.4f)
                    else color1.copy(alpha = 0.3f)
                )
        )
        
        Box(
            modifier = Modifier
                .fillMaxSize()
                .clip(CircleShape)
                .background(
                    Brush.linearGradient(
                        colors = listOf(color1, color2, color3)
                    )
                )
                .graphicsLayer { rotationZ = currentRotation }
                .border(2.dp, Color(0x33FFFFFF), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(CircleShape)
                    .background(Color(0x33000000)),
                contentAlignment = Alignment.Center
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (state == AssistantState.IDLE) {
                        Box(
                            modifier = Modifier
                                .width(32.dp)
                                .height(4.dp)
                                .clip(CircleShape)
                                .background(Color(0x99FFFFFF))
                        )
                    } else {
                        val heights = if (state == AssistantState.LISTENING) 
                            listOf(0.6f, 1.0f, 0.5f, 0.9f, 0.7f) 
                        else 
                            listOf(0.4f, 0.4f, 0.4f, 0.4f, 0.4f)
                            
                        heights.forEachIndexed { index, fl ->
                            val infiniteBarTransition = rememberInfiniteTransition(label = "bar_$index")
                            val barHeight by infiniteBarTransition.animateFloat(
                                initialValue = fl * 12f,
                                targetValue = if (state == AssistantState.THINKING) fl * 12f else fl * 24f,
                                animationSpec = infiniteRepeatable(
                                    animation = tween(if (state == AssistantState.THINKING) 1000 else 400 + (index * 100), easing = EaseInOutSine),
                                    repeatMode = RepeatMode.Reverse
                                ),
                                label = "barHeight"
                            )
                            Box(
                                modifier = Modifier
                                    .width(4.dp)
                                    .height(barHeight.dp)
                                    .clip(CircleShape)
                                    .background(Color(0x99FFFFFF))
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StreamDeckGrid() {
    var buttons by remember { 
        mutableStateOf(OverlayService.currentButtons.mapIndexed { index, map -> 
            StreamDeckButton(index, map["label"] ?: "Btn", map["tool_name"] ?: "tool")
        })
    }

    // Refresh if external list changes
    LaunchedEffect(OverlayService.currentButtons) {
        while(true) {
            delay(1000)
            if (buttons.size != OverlayService.currentButtons.size) {
                 buttons = OverlayService.currentButtons.mapIndexed { index, map -> 
                    StreamDeckButton(index, map["label"] ?: "Btn", map["tool_name"] ?: "tool")
                 }
            }
        }
    }

    if (buttons.isEmpty()) {
        Text("No buttons configured.", color = Color.White)
        return
    }

    LazyVerticalGrid(
        columns = GridCells.Fixed(3),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        items(buttons) { button ->
            StreamDeckWidget(button)
        }
    }
}

@Composable
fun StreamDeckWidget(button: StreamDeckButton) {
    val haptic = LocalHapticFeedback.current
    var pressed by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(targetValue = if (pressed) 0.92f else 1f, label = "buttonScale", animationSpec = tween(150, easing = EaseOutExpo))

    val iconText = when (button.toolName) {
        "smart_home" -> "🚀"
        "media_player" -> "🎵"
        "lock" -> "🔒"
        else -> "🔧"
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .scale(scale)
            .clip(RoundedCornerShape(20.dp))
            .background(
                Brush.linearGradient(
                    colors = if (pressed) listOf(Color(0x4DFFFFFF), Color(0x33FFFFFF)) 
                             else listOf(Color(0x33FFFFFF), Color(0x1AFFFFFF))
                )
            )
            .border(1.dp, Color(0x4DFFFFFF), RoundedCornerShape(20.dp))
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = {
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        pressed = true
                        
                        CoroutineScope(Dispatchers.IO).launch {
                            val btnMap = OverlayService.currentButtons.getOrNull(button.id)
                            val paramsStr = btnMap?.get("tool_params") ?: "{}"
                            val params = ToolRegistry.gson.fromJson(paramsStr, com.google.gson.JsonObject::class.java)
                            ToolRegistry.execute(button.toolName, params)
                        }

                        tryAwaitRelease()
                        haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                        pressed = false
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            Text(text = iconText, style = MaterialTheme.typography.headlineMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = button.label.uppercase(),
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                color = Color(0xFFF1F5F9)
            )
        }
    }
}
