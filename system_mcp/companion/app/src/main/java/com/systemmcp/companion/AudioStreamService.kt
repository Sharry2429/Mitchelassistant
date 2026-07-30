package com.systemmcp.companion

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicBoolean

class AudioStreamService {
    companion object {
        private const val TAG = "AudioStreamService"
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        
        private var audioRecord: AudioRecord? = null
        private var isRecording = AtomicBoolean(false)
        private var recordingJob: Job? = null
        
        fun registerTools() {
            ToolRegistry.register("start_audio_stream") {
                startStreaming()
                ToolRegistry.successResult(mapOf("message" to "Audio streaming started"))
            }

            ToolRegistry.register("stop_audio_stream") {
                stopStreaming()
                ToolRegistry.successResult(mapOf("message" to "Audio streaming stopped"))
            }
        }

        @SuppressLint("MissingPermission")
        fun startStreaming() {
            if (isRecording.get()) return
            
            val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
                Log.e(TAG, "Invalid buffer size")
                return
            }

            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord initialization failed")
                return
            }

            isRecording.set(true)
            audioRecord?.startRecording()

            recordingJob = CoroutineScope(Dispatchers.IO).launch {
                val buffer = ByteArray(bufferSize)
                while (isRecording.get()) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        val base64Data = Base64.encodeToString(buffer, 0, read, Base64.NO_WRAP)
                        val payload = mapOf(
                            "event" to "audio_frame",
                            "data" to base64Data
                        )
                        MitchellService.broadcastNotification(payload)
                    }
                }
            }
        }

        fun stopStreaming() {
            isRecording.set(false)
            recordingJob?.cancel()
            recordingJob = null
            
            try {
                audioRecord?.stop()
                audioRecord?.release()
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping AudioRecord: \${e.message}")
            }
            audioRecord = null
        }
    }
}
