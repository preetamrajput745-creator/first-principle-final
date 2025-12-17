
# Troubleshooting "Website Not Open"

If you are unable to access the website at http://localhost:3000, please follow these steps:

## 1. Use the Fix Script
Double-click `FIX_AND_LAUNCH.bat`. This script explicitly starts all 4 required components:
- API (Port 8000)
- Dashboard (Port 8501)
- Frontend (Port 3000) <- This was likely missing
- Demo Data (Background Simulation)

## 2. PowerShell Execution Policy Error
If you see an error about `npm.ps1 cannot be loaded`, it is because Windows PowerShell restricts scripts by default.
**Solution**: Run the system using Command Prompt (`cmd.exe`) instead of PowerShell, or use the `.bat` file which defaults to CMD.

## 3. Verify Ports
Ensure these ports are free: 3000, 8000, 8501.
If another app is using them, you will see a "Address already in use" error in the pop-up windows.

## 4. Node.js Verification
Ensure Node.js is installed. Open a terminal and run `node -v`. You should see `v18+`.
