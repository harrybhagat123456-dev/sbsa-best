<h1 align="center">
  ✨ SAINI DRM Bot ✨
</h1>

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=18&pause=1000&color=00F7FF&center=true&vCenter=true&width=435&lines=Welcome+to+DRM+Bot+by+@nikhil.saini.khe" alt="Typing SVG" />
</p>

---

> 🔐 **Note:** CP DRM supported — Minimum quality **360p**  
> 🚫 **Do not remove the credit tag**

---

## 📜 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/stop`  | Stop the bot |

---

## 🚀 Deployment Process

### Quick Deploy Options

Choose your preferred platform for deployment. Each platform has unique benefits:

| Platform | Speed | Free Tier | Best For |
|----------|-------|-----------|----------|
| **Railway** ⚡ | 35-50 MB/s | $5 credit (6-8 months) | Maximum Speed |
| **Koyeb** ♾️ | 30-45 MB/s | Unlimited free tier | Long-term hosting |
| **Replit** 🔥 | 45-60 MB/s | Free with limits | Development & Testing |
| **Render** 🌐 | 12-25 MB/s | 750h/month free | Quick deployment |
| **Heroku** 💜 | 15-30 MB/s | Limited free tier | Traditional hosting |

---

## 📦 One-Click Deploy Buttons

[![Deploy to Railway](https://img.shields.io/badge/Deploy%20to-Railway-blueviolet?style=for-the-badge&logo=railway)](https://railway.app/new)
[![Deploy to Koyeb](https://img.shields.io/badge/Deploy%20to-Koyeb-black?style=for-the-badge&logo=koyeb)](https://app.koyeb.com/deploy)
[![Deploy to Render](https://img.shields.io/badge/Deploy%20to-Render-blue?style=for-the-badge&logo=render)](https://render.com/deploy)  
[![Deploy to Heroku](https://img.shields.io/badge/Deploy%20to-Heroku-purple?style=for-the-badge&logo=heroku)](https://www.heroku.com/deploy?template=https://github.com/nikhilsainiop/saini-txt-direct)

---

## 🔧 Deployment Guides

### 🚄 Railway Deployment (Recommended for Speed)

**Why Railway?**
- 2-5x faster than Render
- Higher CPU allocation (0.25-0.5 vCPU)
- $5 free credit lasts 6-8 months
- No bandwidth monitoring

**Steps:**
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select this repository
4. Add environment variables:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   OWNER=your_telegram_id
   CREDIT=YOUR_NAME
   ```
5. Railway will auto-detect `Dockerfile` and deploy
6. Your bot will be live in 2-3 minutes!

**Configuration:** Uses `railway.json` and `Dockerfile`

---

### 🌍 Koyeb Deployment (Unlimited Free Tier)

**Why Koyeb?**
- Truly unlimited free tier (no time limits)
- EU-based servers with global CDN
- Auto-scaling capabilities
- Built-in health checks

**Steps:**
1. Go to [app.koyeb.com](https://app.koyeb.com) and sign up
2. Click "Create Service" → "GitHub"
3. Connect your repository
4. Configure deployment:
   - **Builder**: Dockerfile
   - **Port**: 8000 (Gunicorn default)
   - **Instance Type**: Nano (free tier)
5. Add environment secrets:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   OWNER=your_telegram_id
   ```
6. Click "Deploy"

**Configuration:** Uses `koyeb.yaml` and `Dockerfile`

---

### 🎨 Render Deployment

**Steps:**
1. Fork this repository
2. Go to [render.com](https://render.com)
3. Create new "Web Service" from GitHub repo
4. Select "Docker" as environment
5. Add environment variables in Render dashboard
6. Click "Create Web Service"

**Configuration:** Uses `render.yaml` and `Dockerfile`

---

### 💜 Heroku Deployment

**Steps:**
1. Click the "Deploy to Heroku" button above
2. Fill in the required environment variables
3. Click "Deploy app"
4. Wait for deployment to complete

**Configuration:** Uses `app.json`, `heroku.yml`, and `Procfile`

---

## 🔑 Required Environment Variables

All platforms require these environment variables:

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `API_ID` | Telegram API ID | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | Telegram API Hash | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `BOT_TOKEN` | Bot token from BotFather | [@BotFather](https://t.me/BotFather) on Telegram |
| `OWNER` | Your Telegram user ID | [@userinfobot](https://t.me/userinfobot) |
| `CREDIT` | Your name/credit (optional) | Any name (6-8 letters) |

---

## 🎯 Manual Deployment Guide

If you prefer manual setup:

### Step-by-Step:
1. **Fork** the Repository  
2. **Set Environment Variables** in your platform's dashboard
3. Choose your deployment method:
   - **Docker**: Most platforms auto-detect `Dockerfile`
   - **Buildpack**: Uses `Procfile` for Heroku/Render
4. Deploy and monitor logs for successful startup

---

## 📊 Performance Optimization

For maximum download speeds, the bot is pre-configured with optimal settings for each platform. Expected speeds:
- **Railway**: 35-50 MB/s
- **Koyeb**: 30-45 MB/s  
- **Replit**: 45-60 MB/s
- **Render**: 12-25 MB/s

---

## 🤖 Bot Usernames

- [Saini_Contact](https://t.me/saini_contact_bot)

---

## 📂 Original Repositories

- 🔗 [nikhilsainiop/saini-txt-direct](https://github.com/nikhilsainiop/saini-txt-direct)

---

> 👨‍💻 Created with ❤️ by [@nikhil.saini.khe](https://instagram.com/nikhil.saini.khe)
