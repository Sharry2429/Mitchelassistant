package com.systemmcp.companion

import android.content.Intent
import android.os.Bundle
import android.service.voice.VoiceInteractionService

class MitchellVoiceInteractionService : VoiceInteractionService() {
    override fun onReady() {
        super.onReady()
        // Assistant is ready
    }
}
