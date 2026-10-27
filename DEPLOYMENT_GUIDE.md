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

## 🔐 Step 4: Supabase PostgreSQL Database & Authentication Setup

StudyAgent uses **Supabase** for secure PostgreSQL persistence, Row Level Security (RLS) data isolation, Google OAuth, and passwordless 6-digit Email OTP verification.

### 4.1 Create a Free Supabase Project
1. Go to **[supabase.com](https://supabase.com/)** and sign in or create an account.
2. Click **"New Project"**, name it `ai-study-agent`, choose a strong database password, and select your preferred region.
3. Once created, go to **Project Settings** (gear icon) ➡️ **API**.
4. Copy the following keys:
   * **Project URL** (e.g. `https://xyzproject.supabase.co`) -> `SUPABASE_URL`
   * **anon public key** -> `SUPABASE_ANON_KEY`
   * **service_role secret key** -> `SUPABASE_SERVICE_ROLE_KEY`

### 4.2 Run Database Migrations & RLS Policies
1. In your Supabase dashboard, click **"SQL Editor"** in the left sidebar.
2. Click **"New Query"**.
3. Open [`supabase_schema.sql`](supabase_schema.sql) in this repository, copy its entire contents, and paste into the SQL Editor.
4. Click **"Run"**.
5. This creates the following tables with Row Level Security:
   * `profiles`: User identity, avatar, education level, field of study, learning goals, preferred theme, language.
   * `study_sessions`: Detailed study time and activity records.
   * `study_progress`: Milestone and completion tracking.
   * `quiz_history`: Question history, accuracy, and citations.
   * `user_preferences`: Study settings and goals.
   * Automated trigger: When a user registers via Google or Email OTP, their profile is automatically initialized with secure defaults.

### 4.3 Configure Google Cloud OAuth
1. Go to **[Google Cloud Console](https://console.cloud.google.com/apis/credentials)**.
2. Create a new project or select an existing one.
3. Configure the **OAuth Consent Screen**:
   * User Type: **External**
   * App Name: `StudyAgent.AI`
   * User Support Email: your email
   * Authorized Domains: `supabase.co`
4. Go to **Credentials** ➡️ **Create Credentials** ➡️ **OAuth client ID**:
   * Application type: **Web application**
   * Name: `StudyAgent Web Client`
   * **Authorized JavaScript origins**:
     * `http://localhost:8000`
     * `https://ai-study-agent-og58.onrender.com`
     * `https://YOUR-SUPABASE-PROJECT-ID.supabase.co`
   * **Authorized redirect URIs**:
     * `https://YOUR-SUPABASE-PROJECT-ID.supabase.co/auth/v1/callback`
5. Copy the generated **Client ID** and **Client Secret**.
6. Back in your **Supabase Dashboard**:
   * Navigate to **Authentication** ➡️ **Providers** ➡️ **Google**.
   * Toggle **"Enable Google"** to **ON**.
   * Paste your **Client ID** and **Client Secret**.
   * Click **Save**.

### 4.4 Configure Passwordless Email OTP
1. In Supabase Dashboard, go to **Authentication** ➡️ **URL Configuration**:
   * **Site URL**: `https://ai-study-agent-og58.onrender.com`
   * **Redirect URLs**:
     * `http://localhost:8000/**`
     * `https://ai-study-agent-og58.onrender.com/**`
2. Go to **Authentication** ➡️ **Email Templates** ➡️ **Magic Link / Confirmation**:
   * Subject: `Your StudyAgent Verification Code: {{ .Token }}`
   * Content:
     ```html
     <h2>Verify your email address</h2>
     <p>Your one-time 6-digit verification code for StudyAgent.AI is:</p>
     <h1 style="letter-spacing: 5px; color: #6366f1;">{{ .Token }}</h1>
     <p>This code expires in 10 minutes. If you did not request this, you can safely ignore this email.</p>
     ```
   * Click **Save**.

---

## 🛠️ Step 5: Render Environment Variables
Add these environment variables in your Render Web Service dashboard (**Environment** tab):

| Variable Name | Example Value | Description |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | `gsk_...` | Free fast Llama 3.3 70B inference |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC...` | Telegram bot daemon |
| `START_BOT` | `true` | Starts background bot runner |
| `SUPABASE_URL` | `https://xyz.supabase.co` | Supabase project URL |
| `SUPABASE_ANON_KEY` | `eyJh...` | Public client publishable key |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJh...` | Server backend secret key |

---

## ✅ What Happens After Deployment:
* Unauthenticated visitors see the **Authentication Landing Page** with Google Login, Email OTP, and feature showcases.
* Authenticated students receive a **Personalized Dashboard** with real study time, total sessions, accuracy %, recent activity timeline, and editable profile.
* Full **Light & Dark Theme** toggle with automatic database persistence across devices.
* Telegram bot (`@Guru_vip_alert_bot`) continues running online 24/7/365.
* Your Web Dashboard is live at: `https://ai-study-agent-og58.onrender.com/`
