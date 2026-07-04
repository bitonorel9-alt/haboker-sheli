@echo off
REM ===== הבוקר שלי — ריצה יומית =====
REM אוסף חדשות -> מעדכן את האתר -> שולח מייל
cd /d "%~dp0"
echo [%date% %time%] אוסף חדשות...
python scripts\collect_news.py
echo [%date% %time%] שולח מייל...
python scripts\send_email.py
echo [%date% %time%] שולח וואטסאפ...
python scripts\send_whatsapp.py
echo [%date% %time%] הסתיים.
