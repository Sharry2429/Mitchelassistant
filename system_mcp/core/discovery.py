"""
system_mcp.core.discovery
Provides mDNS (ZeroConf) broadcasting so the Android Companion app can automatically
discover the IP and port of the PC running the Mitchell AI Server.
"""
import socket
import logging
from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

class MitchellDiscoveryServer:
    def __init__(self, port: int = 5000):
        self.port = port
        self.zeroconf = Zeroconf()
        self.service_info = None

    def _get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def start(self):
        ip = self._get_local_ip()
        logger.info(f"Broadcasting Mitchell AI mDNS on {ip}:{self.port}")
        
        # Service type must end in .local.
        service_type = "_mitchell._tcp.local."
        # Name must end with service_type
        service_name = f"MitchellServer._mitchell._tcp.local."
        
        self.service_info = ServiceInfo(
            service_type,
            service_name,
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties={"version": "1.0", "name": "Mitchell PC Backend"},
            server="mitchell.local."
        )
        self.zeroconf.register_service(self.service_info)

    def stop(self):
        if self.service_info:
            self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()

if __name__ == "__main__":
    import time
    server = MitchellDiscoveryServer()
    server.start()
    try:
        print("Broadcasting... Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
