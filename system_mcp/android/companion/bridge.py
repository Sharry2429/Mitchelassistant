"""
system_mcp.android.companion.bridge
Python client for the Mitchell AI Companion APK socket server.

Protocol:
    - TCP socket on 127.0.0.1:5000 (forwarded via `adb forward tcp:5000 tcp:5000`)
    - Framing: 4-byte big-endian length prefix (struct "!I") + UTF-8 JSON payload
    - Auth: first message must be {"action": "handshake", "token": "<token>"}

Response contract (from the Kotlin CompanionService):
    Success: {"status": "ok", ...data fields...}
    Error:   {"status": "error", "message": "..."}

Action        | Request fields          | Response data fields
--------------+-------------------------+--------------------------------------
handshake     | token                   | message
get_clipboard | (none)                  | text
set_clipboard | text                    | message
write_setting | type, key, value        | message
get_accessibility_tree | (none)         | tree (nested dict)
stream_notifications   | enable (bool)  | streaming, listenerConnected
"""

import socket
import json
import struct
import threading
from typing import Callable, Any, Optional

from system_mcp.core.errors import RequiresCompanionApp, RequiresCompanionUpdate, SystemMCPError

COMPANION_VERSION = "1.0.0"


class CompanionBridge:
    """
    Python client side of the Mitchell AI Companion APK bridge.
    Communicates via a local TCP socket forwarded over ADB.
    """

    def __init__(self, port: int = 5000, token: str = "system_mcp_secret"):
        self.host = "127.0.0.1"
        self.port = port
        self.token = token
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_callback: Optional[Callable[[dict], None]] = None
        self._streaming = False
        self._authenticated = False

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    def _connect(self):
        """Open the TCP socket and perform the handshake."""
        if self._socket and self._authenticated:
            return

        # Ensure ADB is connected and the port is forwarded
        try:
            from system_mcp.android.connection import get_active_serial
            get_active_serial()
        except Exception as e:
            pass

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((self.host, self.port))

            # Perform Handshake  -- Kotlin expects {"action":"handshake","token":"..."}
            handshake_resp = self._send_raw({
                "action": "handshake",
                "token": self.token,
            })

            # Kotlin returns {"status":"ok","message":"Handshake successful"} on success
            if handshake_resp.get("status") != "ok":
                self.close()
                error = handshake_resp.get("message", "Unknown error")
                if "version" in error.lower():
                    raise RequiresCompanionUpdate(f"Companion app version mismatch: {error}")
                raise RequiresCompanionApp(f"Companion app handshake failed: {error}")

            self._authenticated = True

        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            self._socket = None
            self._authenticated = False
            raise RequiresCompanionApp(
                f"Could not connect to Companion APK on {self.host}:{self.port}. "
                "Ensure it is installed and running, and port is forwarded "
                "(adb forward tcp:5000 tcp:5000). "
                f"Error: {e}"
            )

    def _send_raw(self, payload: dict) -> dict:
        """Send a JSON payload prefixed with a 4-byte big-endian length header and read the response."""
        data = json.dumps(payload).encode("utf-8")
        header = struct.pack("!I", len(data))

        try:
            self._socket.sendall(header + data)

            # Read response: 4-byte header then payload
            resp_header = self._recv_exact(4)
            if not resp_header:
                raise ConnectionError("Connection lost while reading response header.")

            length = struct.unpack("!I", resp_header)[0]

            resp_data = self._recv_exact(length)
            if not resp_data:
                raise ConnectionError("Connection lost while reading response payload.")

            return json.loads(resp_data.decode("utf-8"))

        except Exception as e:
            self.close()
            raise RequiresCompanionApp(f"Communication with Companion APK failed: {e}")

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Read exactly n bytes from the socket."""
        chunks = []
        bytes_recd = 0
        while bytes_recd < n:
            chunk = self._socket.recv(min(n - bytes_recd, 4096))
            if not chunk:
                return None
            chunks.append(chunk)
            bytes_recd += len(chunk)
        return b"".join(chunks)

    def close(self):
        """Close the connection to the companion app."""
        with self._lock:
            self._streaming = False
            self._authenticated = False
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

    # ------------------------------------------------------------------ #
    # Generic execute
    # ------------------------------------------------------------------ #

    def execute(self, action: str, **kwargs) -> Any:
        """Execute a synchronous command on the companion app.

        Returns the full response dict (excluding 'status' key).
        Raises SystemMCPError on Kotlin-side errors.
        """
        with self._lock:
            self._connect()
            # After handshake, subsequent requests do NOT need the token
            # (the Kotlin side tracks per-connection auth state)
            payload = {"action": action, **kwargs}
            response = self._send_raw(payload)

            if response.get("status") == "error":
                raise SystemMCPError(
                    f"Companion action '{action}' failed: {response.get('message')}"
                )

            return response

    # ------------------------------------------------------------------ #
    # Exposed Bridge API  (matches Kotlin CompanionService actions)
    # ------------------------------------------------------------------ #

    def get_clipboard(self) -> str:
        """Read the device clipboard via the Accessibility Service."""
        resp = self.execute("get_clipboard")
        return resp.get("text", "")

    def set_clipboard(self, text: str) -> None:
        """Write to the device clipboard via the Accessibility Service."""
        self.execute("set_clipboard", text=text)

    def write_setting(self, setting_type: str, key: str, value: str) -> None:
        """Write to Android Settings (global/secure/system).

        Requires WRITE_SECURE_SETTINGS to be granted via ADB.
        Kotlin field name is 'type' (not 'namespace').
        """
        self.execute("write_setting", type=setting_type, key=key, value=value)

    def get_accessibility_tree(self) -> dict:
        """Returns a rich accessibility tree captured by the Companion Service.

        The tree contains: className, packageName, text, contentDescription,
        viewIdResourceName, boundsInScreen, isClickable, isEnabled, isFocused,
        isScrollable, and nested children[].
        """
        resp = self.execute("get_accessibility_tree")
        return resp.get("tree", {})

    def start_notification_stream(self, callback: Callable[[dict], None]) -> None:
        """Enable notification streaming and listen for events on a background thread.

        The Kotlin app uses a broadcast model: once streaming is enabled,
        incoming notifications are pushed to ALL connected sockets. We open
        a dedicated socket for the stream so synchronous calls are not blocked.
        """
        if self._streaming:
            return

        # First, tell the service to enable streaming
        self.execute("stream_notifications", enable=True)

        self._stream_callback = callback
        self._streaming = True

        def stream_worker():
            stream_sock = None
            try:
                # Dedicated socket for receiving streamed notifications
                stream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                stream_sock.connect((self.host, self.port))

                # Handshake on this socket too
                hs = json.dumps({"action": "handshake", "token": self.token}).encode("utf-8")
                stream_sock.sendall(struct.pack("!I", len(hs)) + hs)

                # Read handshake response
                hdr = stream_sock.recv(4)
                if hdr:
                    hs_len = struct.unpack("!I", hdr)[0]
                    stream_sock.recv(hs_len)  # consume handshake response

                while self._streaming:
                    try:
                        header = stream_sock.recv(4)
                        if not header or len(header) < 4:
                            break
                        length = struct.unpack("!I", header)[0]

                        chunks = []
                        bytes_recd = 0
                        while bytes_recd < length:
                            chunk = stream_sock.recv(min(length - bytes_recd, 4096))
                            if not chunk:
                                break
                            chunks.append(chunk)
                            bytes_recd += len(chunk)

                        data = json.loads(b"".join(chunks).decode("utf-8"))
                        if self._stream_callback:
                            self._stream_callback(data)
                    except socket.timeout:
                        continue
                    except Exception:
                        break

            except Exception:
                pass
            finally:
                self._streaming = False
                if stream_sock:
                    try:
                        stream_sock.close()
                    except Exception:
                        pass

        self._stream_thread = threading.Thread(target=stream_worker, daemon=True)
        self._stream_thread.start()

    def stop_notification_stream(self) -> None:
        """Disable notification streaming."""
        self._streaming = False
        try:
            self.execute("stream_notifications", enable=False)
        except Exception:
            pass
        if self._stream_thread:
            self._stream_thread.join(timeout=2.0)
            self._stream_thread = None
