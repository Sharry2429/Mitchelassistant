#!/bin/bash
set -e

echo "=================================================="
echo "    SystemMCP Relay Server AWS Deployment Setup   "
echo "=================================================="

# 1. Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# 2. Create app directory
APP_DIR="/opt/systemmcp"
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# 3. Install Python dependencies
python3 -m pip install --upgrade pip
pip3 install websockets

# 4. Copy systemd service if available locally
if [ -f "deploy/relay_server.service" ]; then
    echo "Installing systemd service..."
    sudo cp deploy/relay_server.service /etc/systemd/system/systemmcp-relay.service
    sudo systemctl daemon-reload
    sudo systemctl enable systemmcp-relay
    sudo systemctl restart systemmcp-relay
    echo "Relay Server service started and enabled on boot."
fi

# 5. Configure Nginx
if [ -f "deploy/nginx.conf" ]; then
    echo "Setting up Nginx configuration..."
    sudo cp deploy/nginx.conf /etc/nginx/sites-available/systemmcp
    sudo ln -sf /etc/nginx/sites-available/systemmcp /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
    echo "Nginx reverse proxy operational."
fi

echo "=================================================="
echo "Setup Complete!"
echo "Next step: Run 'sudo certbot --nginx' to acquire an SSL certificate for WSS."
echo "=================================================="
