# AWS Deployment Guide for SystemMCP Relay Server

This guide walks you through deploying the **SystemMCP Relay Server** (`relay_server.py`) to an AWS EC2 instance (or LightSail VPS) so that your PC Host Agent (`mitchell_assistant.py`) and your Android phone can communicate securely via a permanent Cloud WebSocket (`wss://`) endpoint.

---

## 🏗 Architecture Overview

```
[ Android Companion App ] ───( wss://your-aws-domain.com )───┐
                                                            ▼
                                                [ AWS EC2 / Nginx Proxy ]
                                                            │ (ws://127.0.0.1:8765)
                                                            ▼
[ PC Host Agent ] ──────────( wss://your-aws-domain.com )───► [ system_mcp/relay_server.py ]
```

---

## 🚀 Deployment Steps (Option 1: Quick Shell Installer)

### 1. Launch an AWS EC2 Instance
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS (t3.micro / t2.micro free tier is sufficient).
- **Security Group Inbound Rules**:
  - `SSH` (Port 22) - `My IP`
  - `HTTP` (Port 80) - `0.0.0.0/0`
  - `HTTPS` (Port 443) - `0.0.0.0/0`
  - (Optional) `Custom TCP` (Port 8765) - `0.0.0.0/0` if connecting directly without Nginx proxy.

### 2. Clone & Run Setup
SSH into your EC2 instance and run:
```bash
git clone https://github.com/YOUR_REPO/SystemMCP.git /opt/systemmcp
cd /opt/systemmcp
chmod +x deploy/setup_aws_relay.sh
./deploy/setup_aws_relay.sh
```

### 3. Enable WSS (SSL/TLS via Certbot)
To get a free SSL certificate for secure WebSockets (`wss://`):
```bash
sudo certbot --nginx -d your-domain.com
```
*Note: Point an A-record DNS entry for `your-domain.com` to your EC2 Elastic IP address.*

---

## 🐳 Deployment Steps (Option 2: Docker Compose)

If you prefer containerized deployment:
```bash
cd /opt/systemmcp
docker-compose -f deploy/docker-compose.yml up -d --build
```

---

## 📱 Connecting Clients to AWS Relay

### 1. PC Host Agent (`mitchell_assistant.py`)
Set the environment variable or pass `--relay`:
```powershell
$env:RELAY_URL="wss://your-domain.com"
python mitchell_assistant.py --remote
```

### 2. Android Mitchell App
In the Android Companion app settings / config, set the Relay URL to:
`wss://your-domain.com` (or `ws://YOUR_EC2_PUBLIC_IP:8765` for testing).

---

## 🔍 Service Status & Logs

- **Check Service**: `sudo systemctl status systemmcp-relay`
- **View Logs**: `sudo journalctl -u systemmcp-relay -f`
- **Restart Service**: `sudo systemctl restart systemmcp-relay`
