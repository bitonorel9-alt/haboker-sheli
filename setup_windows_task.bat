@echo off
REM ===== הגדרה חד-פעמית: תזמון ל-07:30 כל בוקר =====
REM הרץ קובץ זה פעם אחת (לחיצה כפולה). ייצור משימה יומית ב-Task Scheduler.
cd /d "%~dp0"
schtasks /Create /TN "HaBoker Sheli" /TR "\"%~dp0run_daily.bat\"" /SC DAILY /ST 07:30 /F
echo.
echo ✓ נקבעה משימה יומית בשם "HaBoker Sheli" לשעה 07:30.
echo   לבדיקה מיידית הרץ:  schtasks /Run /TN "HaBoker Sheli"
echo   לביטול:            schtasks /Delete /TN "HaBoker Sheli" /F
pause
