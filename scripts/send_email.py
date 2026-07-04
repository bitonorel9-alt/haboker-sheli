#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הבוקר שלי — שליחת תמצית יומית למייל
בונה מייל HTML יפה מ-news_data.json ושולח אליך.

>>> אבטחה: הסקריפט קורא פרטי מייל מקובץ config/email_config.json בלבד.
    אתה ממלא אותו. הסיסמה לא נשמרת בקוד ואף אחד אחר לא רואה אותה. <<<

הגדרה חד-פעמית — ראה קובץ config/email_config.example.json והוראות ב-README.
"""
import json, smtplib, ssl, datetime, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CFG  = BASE / "config" / "email_config.json"
DATA = BASE / "data" / "news_data.json"

def load(p, what):
    if not p.exists():
        print(f"חסר קובץ {what}: {p}")
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))

def build_html(d):
    def card(a, lead=False):
        stats = ""
        if a.get("stats"):
            rows = "".join(
                f'<tr><td style="color:#6b6152;font-size:13px;padding:3px 0">{s[0]}</td>'
                f'<td style="text-align:left;color:#0b5d4e;font-weight:700;font-size:13px">{s[1]}</td></tr>'
                for s in a["stats"])
            stats = (f'<table style="width:100%;border-top:1px dashed #d8cdb8;margin-top:10px;'
                     f'padding-top:8px">{rows}</table>')
        bg = "#0b5d4e" if a.get("learn") else "#fffdf7"
        fg = "#f5f0e6" if a.get("learn") else "#14110d"
        sec = "#e9c46a" if a.get("learn") else "#0b5d4e"
        size = "22px" if lead else "18px"
        return f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 14px">
         <tr><td style="background:{bg};border:1px solid #d8cdb8;border-radius:14px;padding:18px 20px" dir="rtl">
          <div style="color:{sec};font-size:11px;font-weight:700;letter-spacing:1px">{a["section"].upper()}</div>
          <div style="font-family:Georgia,serif;font-weight:700;font-size:{size};color:{fg};margin:6px 0 6px;line-height:1.25">{a["title"]}</div>
          <div style="color:{'#d3e6df' if a.get('learn') else '#463f34'};font-size:14px;line-height:1.55">{a["summary"]}</div>
          <div style="color:#6b6152;font-size:11px;margin-top:8px">{a.get("source","")}</div>
          {stats}
         </td></tr>
        </table>'''

    L = d["lead"]
    lead_html = card({"section":L["section"],"title":L["title"],"summary":L["summary"],
                      "source":"הכותרת של הבוקר","stats":None}, lead=True)
    body = "".join(card(a) for a in d["articles"])
    return f'''<!DOCTYPE html><html dir="rtl" lang="he"><body style="margin:0;background:#f5f0e6;padding:24px 0;font-family:Arial,Helvetica,sans-serif">
    <table align="center" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto">
     <tr><td dir="rtl" style="border-bottom:2px solid #14110d;padding:0 8px 14px">
       <div style="font-family:Georgia,serif;font-weight:900;font-size:34px;color:#14110d">הבוקר <span style="color:#0b5d4e">שלי</span></div>
       <div style="color:#6b6152;font-size:13px;margin-top:4px">{d.get("date_he","")} · עתלית · עודכן {d.get("updated","")}</div>
     </td></tr>
     <tr><td style="padding:16px 8px 0">{lead_html}{body}</td></tr>
     <tr><td dir="rtl" style="border-top:2px solid #14110d;padding:16px 8px;text-align:center;color:#6b6152;font-size:12px">
       תמצית יומית · פתח את האתר המלא במחשב לסטטיסטיקות אינטראקטיביות ודירוג כתבות
     </td></tr>
    </table></body></html>'''

def main():
    cfg = load(CFG, "הגדרות מייל")
    d   = load(DATA, "נתוני חדשות (הרץ קודם collect_news.py)")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ הבוקר שלי · {d.get('date_he','')}"
    msg["From"] = cfg["from_email"]
    msg["To"]   = cfg["to_email"]
    msg.attach(MIMEText(build_html(d), "html", "utf-8"))

    ctx = ssl.create_default_context()
    print(f"שולח אל {cfg['to_email']}…")
    with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as s:
        s.starttls(context=ctx)
        s.login(cfg["from_email"], cfg["app_password"])
        s.send_message(msg)
    print("✓ המייל נשלח בהצלחה")

if __name__ == "__main__":
    main()
