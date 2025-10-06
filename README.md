# Mr-Transparent-TE.bot
This is a best earning bot in telegram BD 💰
# Telegram Pro Ads Bot - Railway Deployment

## Step 1: GitHub
1. নতুন repository বানাও।
2. এই ফাইলগুলো (bot.py, requirements.txt, Procfile, .env.example) GitHub-এ upload করো।

## Step 2: Railway
1. https://railway.app/ → Sign in
2. New Project → Deploy from GitHub → তোমার repo select করো
3. Environment Variables বসাও:
   - BOT_TOKEN = BotFather token
   - ADMIN_ID = তোমার Telegram ID
   - BASE_URL = Railway app URL (উদাহরণ: https://yourapp.up.railway.app)
4. Deploy বাটন চাপো → deploy হয়ে যাবে।

## Step 3: Telegram Bot Test
- `/start` → সাবস্ক্রাইব
- `/ads` → ads দেখো
- `/balance` → balance চেক করো
- Click ad → 30% user, 70% তোমার
- `/withdraw` → request
- Admin `/approve_withdraw <id>` → payout confirm
