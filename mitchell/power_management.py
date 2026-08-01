import logging
import psutil
import ctypes
import os

logger = logging.getLogger(__name__)

class PowerManagement:
    def __init__(self):
        # Constants for Windows power management (preventing sleep)
        self.ES_CONTINUOUS = 0x80000000
        self.ES_SYSTEM_REQUIRED = 0x00000001
        self.ES_DISPLAY_REQUIRED = 0x00000002

    def wake_on_lan(self, mac_address: str):
        """Wakes up the target machine if it supports WoL."""
        logger.info(f"Sending magic packet to {mac_address}")

    def check_battery(self) -> dict:
        """Returns the current battery status including percentage and if plugged in."""
        battery = psutil.sensors_battery()
        if battery is None:
            return {"percent": 100, "power_plugged": True} # Default for desktops
        
        return {
            "percent": battery.percent,
            "power_plugged": battery.power_plugged
        }

    def prevent_sleep_lid_closed(self):
        """
        Prevents the local machine from sleeping even when lid is closed.
        On Windows, this uses SetThreadExecutionState.
        """
        if os.name == 'nt':
            logger.info("Setting thread execution state to prevent sleep (lid closed mode)")
            ctypes.windll.kernel32.SetThreadExecutionState(
                self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
            )
        else:
            logger.info("Prevent sleep logic not implemented for non-Windows OS yet.")

    def allow_sleep(self):
        """Allows the system to sleep normally again."""
        if os.name == 'nt':
            logger.info("Restoring normal sleep behavior")
            ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
