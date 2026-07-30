package com.systemmcp.companion

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

class WakeWordService(private val context: Context) : RecognitionListener {
    companion object {
        private const val TAG = "WakeWordService"
        private const val WAKE_WORD = "mitchell"
    }

    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false

    fun startListening() {
        if (isListening) return
        if (SpeechRecognizer.isRecognitionAvailable(context)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context)
            speechRecognizer?.setRecognitionListener(this)
            
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            
            speechRecognizer?.startListening(intent)
            isListening = true
            Log.d(TAG, "Started listening for wake word")
        } else {
            Log.e(TAG, "Speech recognition is not available on this device")
        }
    }

    fun stopListening() {
        isListening = false
        try {
            speechRecognizer?.stopListening()
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping SpeechRecognizer: \${e.message}")
        }
        speechRecognizer = null
    }

    override fun onReadyForSpeech(params: Bundle?) {}
    override fun onBeginningOfSpeech() {}
    override fun onRmsChanged(rmsdB: Float) {}
    override fun onBufferReceived(buffer: ByteArray?) {}
    override fun onEndOfSpeech() {}
    
    override fun onError(error: Int) {
        Log.d(TAG, "SpeechRecognizer error: \$error")
        isListening = false
        // Auto-restart listening if error is not fatal
        if (error != SpeechRecognizer.ERROR_CLIENT && error != SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
            startListening()
        }
    }

    override fun onResults(results: Bundle?) {
        handleResults(results)
        isListening = false
        startListening() // Restart listening loop
    }

    override fun onPartialResults(partialResults: Bundle?) {
        handleResults(partialResults)
    }

    private fun handleResults(results: Bundle?) {
        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        if (!matches.isNullOrEmpty()) {
            for (match in matches) {
                if (match.lowercase().contains(WAKE_WORD)) {
                    Log.d(TAG, "Wake word detected!")
                    // Notify Python backend
                    val payload = mapOf("event" to "wake_word_detected")
                    MitchellService.broadcastNotification(payload)
                    break
                }
            }
        }
    }

    override fun onEvent(eventType: Int, params: Bundle?) {}
}
