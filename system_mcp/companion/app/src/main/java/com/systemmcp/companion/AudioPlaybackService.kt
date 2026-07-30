package com.systemmcp.companion

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Base64
import android.util.Log

class AudioPlaybackService {
    companion object {
        private const val TAG = "AudioPlaybackService"
        private const val SAMPLE_RATE = 24000 // Common TTS sample rate
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_OUT_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        
        private var audioTrack: AudioTrack? = null

        fun registerTools() {
            ToolRegistry.register("play_audio_frame") { root ->
                if (!root.has("data") || root.get("data").isJsonNull) {
                    throw Exception("Missing 'data' field containing base64 PCM")
                }
                val base64Data = root.get("data").asString
                val pcmBytes = Base64.decode(base64Data, Base64.DEFAULT)
                
                playPcmBytes(pcmBytes)
                ToolRegistry.successResult()
            }
        }

        private fun playPcmBytes(pcmBytes: ByteArray) {
            if (audioTrack == null || audioTrack?.state != AudioTrack.STATE_INITIALIZED) {
                val minBufferSize = AudioTrack.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
                audioTrack = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AUDIO_FORMAT)
                            .setSampleRate(SAMPLE_RATE)
                            .setChannelMask(CHANNEL_CONFIG)
                            .build()
                    )
                    .setBufferSizeInBytes(minBufferSize)
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()
            }

            if (audioTrack?.playState != AudioTrack.PLAYSTATE_PLAYING) {
                audioTrack?.play()
            }

            audioTrack?.write(pcmBytes, 0, pcmBytes.size)
        }
        
        fun stopPlayback() {
            try {
                audioTrack?.stop()
                audioTrack?.release()
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping AudioTrack: \${e.message}")
            }
            audioTrack = null
        }
    }
}
