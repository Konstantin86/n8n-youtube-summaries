# n8n-youtube-summaries
This repository contains tutorial and source files for implementing automation to collect and summarize all new videos from YouTube into concise, insightful summaries.

---
## How-To

### 1. Install n8n on your local device
The best is to follow the official documentation: [n8n Docs](https://docs.n8n.io/integrations/creating-nodes/test/run-node-locally/).

#### 1.1 Example on Ubuntu
```bash
sudo apt install -y nodejs
sudo npm install -g n8n
```

To run **n8n** as a service (recommended):

```bash
sudo useradd -m -d /home/n8n -s /bin/bash n8n
sudo passwd n8n   # (set password if you want login)
sudo nano /etc/systemd/system/n8n.service
```

Paste the following into the file:

```ini
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=n8n
Environment=PATH=/usr/bin:/usr/local/bin
Environment=HOME=/home/n8n
WorkingDirectory=/home/n8n
ExecStart=/usr/bin/n8n
Restart=always
RestartSec=10
Environment=N8N_HOST=0.0.0.0
Environment=N8N_PORT=5678
Environment=N8N_PROTOCOL=http
Environment=N8N_SECURE_COOKIE=false
Environment=N8N_OAUTH2_REDIRECT_URL=http://localhost:5678/rest/oauth2-credential/callback
Environment=N8N_EDITOR_BASE_URL=http://localhost:5678
Environment=WEBHOOK_URL=http://localhost:5678/

[Install]
WantedBy=multi-user.target
```

Reload and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n
```

---

### 2. Test n8n in browser
Open:  
```
http://192.168.0.122:5678
```

---

### 3. Implement FastAPI wrapper around `youtube-transcript-api` for obtaining YouTube transcripts

#### 3.1 Install Prerequisites
```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install youtube-transcript-api fastapi uvicorn
```
