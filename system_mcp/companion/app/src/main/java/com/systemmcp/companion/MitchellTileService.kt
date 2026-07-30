package com.systemmcp.companion

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService

class MitchellTileService : TileService() {
    override fun onStartListening() {
        super.onStartListening()
        updateTileState()
    }

    override fun onClick() {
        super.onClick()
        if (OverlayService.isOverlayVisible) {
            OverlayService.hideOverlay(this)
        } else {
            OverlayService.showOverlay(this)
        }
        updateTileState()
    }

    private fun updateTileState() {
        val tile = qsTile ?: return
        if (OverlayService.isOverlayVisible) {
            tile.state = Tile.STATE_ACTIVE
            tile.label = "Mitchell AI (On)"
        } else {
            tile.state = Tile.STATE_INACTIVE
            tile.label = "Mitchell AI (Off)"
        }
        tile.updateTile()
    }
}
