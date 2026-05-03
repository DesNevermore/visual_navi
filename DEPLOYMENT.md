# Deployment Guide

This guide covers deploying the blind navigation demo to a production server.

## Prerequisites

- A VPS (2 vCPU / 2 GB RAM minimum)
- A domain name (optional but recommended for HTTPS)
- SSH access to the server
- API keys (OpenAI, Gemini)

## Option 1: Deploy with Domain + Caddy (Recommended)

### Step 1: Prepare VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y
```

### Step 2: Upload Code

```bash
# On your local machine
cd /path/to/visualNavigator
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  . user@your-vps-ip:~/visualNavigator/
```

### Step 3: Setup Backend

```bash
# On VPS
cd ~/visualNavigator/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
nano .env  # Add your API keys
```

### Step 4: Configure Caddy

```bash
# Edit Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Add:
```
nav.yourdomain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```

Caddy will automatically obtain and renew Let's Encrypt SSL certificates.

### Step 5: Setup Systemd Service

```bash
# Copy service file
sudo cp ~/visualNavigator/deploy/navigator.service /etc/systemd/system/

# Edit paths
sudo nano /etc/systemd/system/navigator.service
# Update YOUR_USERNAME and /path/to/visualNavigator

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable navigator
sudo systemctl start navigator

# Check status
sudo systemctl status navigator
```

### Step 6: Update Frontend

Edit `frontend/index.html` line 88:
```javascript
const BACKEND_URL = 'https://nav.yourdomain.com';
```

Upload frontend to VPS or serve it from the same Caddy:

```bash
# Add to Caddyfile
nav.yourdomain.com {
    root * /home/user/visualNavigator/frontend
    file_server
    
    handle /capture {
        reverse_proxy 127.0.0.1:8000
    }
    handle /command {
        reverse_proxy 127.0.0.1:8000
    }
}
```

### Step 7: Test

Visit `https://nav.yourdomain.com` on your phone and test the app.

## Option 2: Deploy without Domain (Cloudflare Tunnel)

### Step 1: Setup Backend on VPS

Follow Steps 1-3 from Option 1.

### Step 2: Install Cloudflared

```bash
# On VPS
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### Step 3: Start Backend

```bash
cd ~/visualNavigator/backend
source venv/bin/activate
python main.py &
```

### Step 4: Create Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the `https://xxx.trycloudflare.com` URL.

### Step 5: Update Frontend

Edit `frontend/index.html` line 88 with the tunnel URL, then serve frontend:

```bash
cd ~/visualNavigator/frontend
python3 -m http.server 3000 &
cloudflared tunnel --url http://localhost:3000
```

Visit the frontend tunnel URL on your phone.

**Note**: Tunnel URLs change on restart. For persistent URLs, use Cloudflare Tunnel with authentication.

## Option 3: Android-Only Testing (No Deployment)

If you only need to test on your own Android phone:

1. Find your computer's local IP: `ifconfig` (macOS/Linux) or `ipconfig` (Windows)
2. Start backend: `python main.py`
3. On Android Chrome, go to `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
4. Enable and add `http://YOUR_LOCAL_IP:8000`
5. Restart Chrome
6. Update `frontend/index.html` with `http://YOUR_LOCAL_IP:8000`
7. Serve frontend: `python3 -m http.server 3000`
8. Visit `http://YOUR_LOCAL_IP:3000` on your phone

## Monitoring

### Check Backend Logs

```bash
# If using systemd
sudo journalctl -u navigator -f

# If running manually
tail -f /path/to/backend.log
```

### Check Caddy Logs

```bash
sudo journalctl -u caddy -f
```

### Monitor Resources

```bash
htop
# or
top
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
sudo journalctl -u navigator -n 50

# Test manually
cd ~/visualNavigator/backend
source venv/bin/activate
python main.py
```

### HTTPS not working
```bash
# Check Caddy status
sudo systemctl status caddy

# Check Caddy logs
sudo journalctl -u caddy -n 50

# Verify DNS
dig nav.yourdomain.com
```

### Camera not working on mobile
- Ensure you're using HTTPS (not HTTP)
- Check browser console for errors
- Try a different browser
- Verify camera permissions

### High API costs
- Check backend logs for request frequency
- Implement rate limiting if needed
- Use phone angle detection (already implemented) to reduce API calls
- Consider caching recent responses

## Security Considerations

1. **API Keys**: Never commit `.env` to git. Keep API keys secure.
2. **CORS**: In production, update `main.py` to allow only your domain:
   ```python
   allow_origins=["https://nav.yourdomain.com"]
   ```
3. **Rate Limiting**: Consider adding rate limiting to prevent abuse
4. **HTTPS**: Always use HTTPS in production
5. **Firewall**: Configure firewall to only allow necessary ports (80, 443, 22)

## Cost Optimization

- Use Gemini 2.5 Flash (cheapest vision model)
- Phone angle detection saves API calls
- Keep image resolution at 1024px (already implemented)
- Monitor usage in API dashboards
- Set spending limits in API provider accounts

## Backup

```bash
# Backup session data (if using SQLite in future)
cp ~/visualNavigator/backend/sessions.db ~/backups/

# Backup environment variables
cp ~/visualNavigator/backend/.env ~/backups/
```

## Updates

```bash
# On local machine
git pull origin main

# Upload to VPS
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  . user@your-vps-ip:~/visualNavigator/

# On VPS
cd ~/visualNavigator/backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart navigator
```

## Next Steps

After deployment, test the full flow on your phone and adjust the vision prompts in `backend/vision.py` based on real-world performance.
