package com.systemmcp.companion

import androidx.car.app.CarContext
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.MessageTemplate
import androidx.car.app.model.Template

class MitchellCarScreen(carContext: CarContext) : Screen(carContext) {
    override fun onGetTemplate(): Template {
        val triggerAction = Action.Builder()
            .setTitle("Speak to Mitchell")
            .setOnClickListener {
                // Notify python side that assistant was triggered from car
                val payload = mapOf("event" to "car_assistant_triggered")
                MitchellService.broadcastNotification(payload)
            }
            .build()

        return MessageTemplate.Builder("Mitchell AI is connected and listening.")
            .setTitle("Mitchell AI")
            .addAction(triggerAction)
            .build()
    }
}
