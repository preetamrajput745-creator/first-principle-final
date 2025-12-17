# Modular Trading Platform (Anti-Gravity)

This is a local-first trading system designed for stability and modular research.

## 🚀 Quick Start Guide (For Total Beginners)

**Prerequisites:** You must have Python and Node.js installed.

### Step 1: Safe Start (Recommended)
This method prevents the "White Screen" and "Random Stop" issues by building the app properly.
1. Double-click **`START_SAFE.bat`**.
2. Wait for the build to finish (might take 2-3 minutes the first time).
3. The dashboard will open automatically at: `http://localhost:3000`

### Step 2: Configure Environment
1. Copy `.env.example` and rename it to `.env`.
2. Fill in your keys (if needed) or leave defaults for local testing.

---

## ⚠️ Troubleshooting Guide

| Problem | Likely Cause | Fix |
| :--- | :--- | :--- |
| **White Screen / Loading Forever** | Database is "locked" or Frontend crashed. | Close all black "CMD" windows and run `START_SAFE.bat` again. |
| **Chart Freezes / No Data** | You clicked inside the black CMD window. | Press `Enter` key on the black window to unfreeze it. |
| **Random Stop after 2 days** | "Dev Mode" filled up memory. | Use `START_SAFE.bat` instead of `npm run dev`. |

---

## ☁️ How to Upload to GitHub (Phase 4)

1. **Login to GitHub** and create a **New Repository**.
   - Name: `my-trading-platform`
   - Select: **Private**
   - **Do NOT** check "Add README" (we already have one).

2. **Open Terminal** in this folder (Right click -> Open in Terminal).
3. **Run these commands exactly:**
   ```bash
   git init
   git add .
   git commit -m "Initial backup"
   git branch -M main
   # Replace URL below with your actual GitHub repo URL
   git remote add origin https://github.com/YOUR_USERNAME/my-trading-platform.git
   git push -u origin main
   ```

4. **Done!** Your code is safe. **Secrets in `.env` were NOT uploaded.**
