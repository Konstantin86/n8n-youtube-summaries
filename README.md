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
# tools for venv
sudo apt update
sudo apt install -y python3-venv

# make a project dir
mkdir -p ~/yt-transcript && cd ~/yt-transcript

# create + activate venv
python3 -m venv .venv
source .venv/bin/activate

# upgrade pip + install packages inside the venv
pip install --upgrade pip wheel
pip install youtube-transcript-api fastapi "uvicorn[standard]"
```

#### 3.2 Create the file ~/yt-transcript/transcript_api.py (source code is provided in this repository)
#### 3.3 Run as a systemd service. Create file /etc/systemd/system/transcript-api.service:

```ini
[Unit]
Description=YouTube Transcript API (FastAPI + youtube-transcript-api)
After=network.target

[Service]
User=kostiantyn_lazurenko
WorkingDirectory=/home/kostiantyn_lazurenko/yt-transcript
# Use the venv's Python so we don't touch the system Python
ExecStart=/home/kostiantyn_lazurenko/yt-transcript/.venv/bin/python -m uvicorn transcript_api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
# Webshare credentials (rotate residential)
Environment=WEBSHARE_USER={here comes your webshare username}
Environment=WEBSHARE_PASS={here comes your webshare password}
Environment=WEBSHARE_LOCATIONS=de,us

# keep your existing vars (CHANNELS_API_KEY etc.)

[Install]
WantedBy=multi-user.target
```

#### 3.4 Enable the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable transcript-api
sudo systemctl start transcript-api
```

### 4. Setup n8n workflow
```
http://192.168.0.122:5678
```
#### 4.1 Go to the Credentials and create credentials for the following services 
##### 4.1.1 Youtube Account (Youtube OAuth 2 API)
##### 4.1.2 Telegram Account (Telegram API)
##### 4.1.3 OpenAi Account (OpenAi)

#### 4.1 Create new workflow
#### 4.2 Click on '...' -> "Import from file" and select the yt_digest.public.json file from this repository
#### 4.3 Open 'Set Config' node and replace apiKey with your Google Credentials
#### 4.4 Open 'Get Subscriptions' node and set your Youtube Auth 2 crenedtials
#### 4.5 Open two last Telegram related nodes and replace {{TELEGRAM_CHAT_ID}} with your real chat id (one way to get it is to call https://api.telegram.org/bot<BOT_TOKEN>/getUpdates endpoint and look for the value "chat": { "id": 123456789, "first_name": "YourName", ... } in the json response). Also connect your telegram credentials
#### 4.6 Open 'OpenAI Chat Model' node and connect your openAI credentials
#### 4.7 Open 'Get Captions' node and ensure it calls correct endpoint (localhost or ip and port)
#### 4.8 Add triggers for your workflow (like 'schedule trigger' or whatever you need)

### Use workflow and enjoy!