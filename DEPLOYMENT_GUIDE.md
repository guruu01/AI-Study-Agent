# ☁️ 24/7 Cloud Deployment Guide (Free Tier with Groq & Render)

This guide shows you how to deploy your **AI Study Agent** to the cloud for free so it runs **24 hours a day, 7 days a week**, even when your computer is shut down.

---

## ⚡ The 24/7 Cloud Architecture

```
Telegram Users (Worldwide)
         │
         ▼
[ Render / Railway Free Web Service ] (FastAPI + Embedded Qdrant + SQLite)
         │
         ▼
[ Groq Cloud API ] (Free Llama 3.3 70B — 500+ tokens/second, zero GPU cost)
```

---

## 🔑 Step 1: Get a Free Groq API Key (30 Seconds)

Groq provides **free cloud inference** for **Llama 3.3 70B** with industry-leading speed (500+ tokens/sec) and zero cost.

1. Go to **[console.groq.com](https://console.groq.com/keys)**.
2. Sign in with Google or GitHub (no credit card required).
3. Click **"Create API Key"**, give it a name like `study-agent`, and copy the key (starts with `gsk_...`).

---

## 🚀 Step 2: Push Your Project to GitHub

If you haven't pushed this folder to GitHub yet:
1. Create a new repository on [GitHub](https://github.com/new) (e.g. `ai-study-agent`).
2. Run these commands in PowerShell inside `C:\Users\gurus\.gemini\antigravity-ide\scratch\ai-study-agent`:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of 24/7 AI Study Agent"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ai-study-agent.git
   git push -u origin main
   ```

---

## 🌐 Step 3: Deploy to Render (100% Free Web Service)

1. Go to **[Render.com](https://dashboard.render.com/)** and sign in.
2. Click **"New +"** ➡️ **"Web Service"**.
3. Select **"Build and deploy from a Git repository"** and choose your `ai-study-agent` repo.
4. Fill in the settings:
   * **Name:** `ai-study-agent`
   * **Region:** Any (e.g. Singapore or Frankfurt)
   * **Branch:** `main`
   * **Runtime:** `Python 3` (or choose Docker)
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   * **Instance Type:** `Free` ($0/month)
5. Under **"Environment Variables"**, add these 3 variables:
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `TELEGRAM_BOT_TOKEN` | `your_telegram_bot_token_here` | Your bot token from @BotFather |
   | `GROQ_API_KEY` | `gsk_...` | Your free key from Step 1 |
   | `START_BOT` | `true` | Automatically launches the Telegram bot daemon |
6. Click **"Deploy Web Service"**!

---

## 🚂 Alternative: Deploy to Railway (1 Click)
1. Go to **[Railway.app](https://railway.app)**.
2. Click **"New Project"** ➡️ **"Deploy from GitHub repo"**.
3. Add the environment variables (`TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `START_BOT=true`).
4. Railway will automatically build the `Dockerfile` and launch your bot in ~60 seconds.

---

## ✅ What Happens After Deployment:
* Your Telegram bot (`@Guru_vip_alert_bot`) will stay **online 24/7/365**.
* It runs on **Llama 3.3 70B** via Groq with sub-second response times.
* Anyone you share the bot link with (`t.me/Guru_vip_alert_bot`) can take quizzes, get summaries, and upload notes anytime.
* Your Web Dashboard will be live at a public HTTPS URL (e.g. `https://ai-study-agent.onrender.com`).
