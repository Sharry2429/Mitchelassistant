FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir websockets

# Copy relay server script
COPY system_mcp/relay_server.py /app/relay_server.py

EXPOSE 8765

CMD ["python", "relay_server.py"]
