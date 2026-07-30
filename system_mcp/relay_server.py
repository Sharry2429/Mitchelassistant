import asyncio
import json
import logging
import websockets
from collections import defaultdict
from typing import Dict, Set, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")

# Map room_id to connected websockets
rooms: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"host": None, "clients": set()})

async def handle_connection(websocket):
    room_id = None
    role = None
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
                continue

            msg_type = data.get("type")
            room_id = data.get("room")
            if not room_id:
                logger.error("Message missing room ID")
                continue

            if msg_type == "register":
                role = data.get("role")
                if role == "host":
                    if rooms[room_id]["host"] is not None and rooms[room_id]["host"] != websocket:
                        logger.warning(f"Host already registered for room {room_id}, overwriting.")
                        try:
                            await rooms[room_id]["host"].close()
                        except:
                            pass
                    rooms[room_id]["host"] = websocket
                    logger.info(f"Host registered for room {room_id}")
                elif role == "client":
                    rooms[room_id]["clients"].add(websocket)
                    logger.info(f"Client registered for room {room_id}")
                else:
                    logger.error(f"Unknown role: {role}")
                    
            elif msg_type == "message":
                # Route message to the appropriate peer
                if role == "host":
                    # Broadcast to all clients
                    payload = data.get("payload")
                    if payload:
                        disconnected = set()
                        for client_ws in rooms[room_id]["clients"]:
                            try:
                                await client_ws.send(json.dumps({"type": "message", "payload": payload}))
                            except websockets.exceptions.ConnectionClosed:
                                disconnected.add(client_ws)
                        for c in disconnected:
                            rooms[room_id]["clients"].remove(c)
                elif role == "client":
                    # Route to host
                    payload = data.get("payload")
                    host_ws = rooms[room_id].get("host")
                    if host_ws and payload:
                        try:
                            await host_ws.send(json.dumps({"type": "message", "payload": payload}))
                        except websockets.exceptions.ConnectionClosed:
                            rooms[room_id]["host"] = None
                            logger.info(f"Host disconnected from room {room_id}")
                else:
                    logger.warning("Unregistered connection sent a message")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if room_id and role:
            if role == "host":
                if rooms[room_id]["host"] == websocket:
                    rooms[room_id]["host"] = None
                    logger.info(f"Host unregistered from room {room_id}")
            elif role == "client":
                if websocket in rooms[room_id]["clients"]:
                    rooms[room_id]["clients"].remove(websocket)
                    logger.info(f"Client unregistered from room {room_id}")
            
            # Cleanup empty rooms
            if rooms[room_id]["host"] is None and len(rooms[room_id]["clients"]) == 0:
                del rooms[room_id]

async def main():
    logger.info("Starting Relay Server on ws://0.0.0.0:8765")
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
