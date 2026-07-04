#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הבוקר שלי — שליחת תמצית יומית לוואטסאפ (דרך CallMeBot, חינמי, ללא הרשמה מסובכת)

הגדרה חד-פעמית:
1. שמור את המספר +34 644 59 71 07 באנשי הקשר שלך בוואטסאפ.
2. שלח לו הודעה בדיוק כך: "I allow callmebot to send me messages"
3. תוך דקה-שתיים יגיע אליך API Key בהודעת חזרה.
4. העתק את config/whatsapp_config.example.json ל-config/whatsapp_config.json
   ומלא phone (עם קידומת מדינה, לדוגמה 972501234567), apikey, ואופציונלית
   site_url (קישור לאתר המתארח, אם הוגדר) כדי שהקישור יצורף להודעה.

אם הקובץ לא קיים — הסקריפט פשוט מדלג (לא שובר את run_daily.bat).
"""
import json, sys, urllib.parse, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CFG  = BASE / "config" / "whatsapp_config.json"
DATA = BASE / "data" / "news_data.json"

def build_message(d, site_url=None):
    lines = [f"☀️ *הבוקר שלי* · {d.get('date_he','')}", ""]
    L = d["lead"]
    lines.append(f"📌 *{L['title']}*")
    if L.get("summary"):
        lines.append(L["summary"])
    lines.append("")
    for a in d.get("articles", []):
        if a.get("learn"):
            continue
        lines.append(f"• [{a['section']}] {a['title']}")
    lines.append("")
    if site_url:
        lines.append(f"לכל הפרטים והסטטיסטיקות: {site_url}")
    else:
        lines.append("לכל הפרטים והסטטיסטיקות — פתח את האתר במחשב.")
    return "\n".join(lines)[:2000]  # CallMeBot מגביל אורך הודעה

def main():
    if not CFG.exists():
        print("אין config/whatsapp_config.json — מדלג על שליחת וואטסאפ (ראו הוראות בראש הקובץ).")
        return
    if not DATA.exists():
        print(f"חסר קובץ נתוני חדשות: {DATA} (הרץ קודם collect_news.py)")
        sys.exit(1)

    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    d = json.loads(DATA.read_text(encoding="utf-8"))
    text = build_message(d, cfg.get("site_url"))

    url = ("https://api.callmebot.com/whatsapp.php?"
           f"phone={urllib.parse.quote(str(cfg['phone']))}"
           f"&text={urllib.parse.quote(text)}"
           f"&apikey={urllib.parse.quote(str(cfg['apikey']))}")

    print("שולח הודעת וואטסאפ…")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            print("✓ נשלח:", r.read().decode("utf-8", "ignore")[:200])
    except Exception as ex:
        print(f"שגיאה בשליחת וואטסאפ: {ex}")

if __name__ == "__main__":
    main()
