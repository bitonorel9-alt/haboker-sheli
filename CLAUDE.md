# CLAUDE.md — הבוקר שלי

הקשר לפרויקט עבור Claude Code. קרא לפני עבודה על הקוד.

## מה זה
אתר תמצית חדשות יומית מותאם אישית (מותקן כאפליקציה/PWA), מתארח חי ב-GitHub Pages
ומתעדכן אוטומטית כל בוקר דרך GitHub Actions, + שליחת מייל ווואטסאפ אוטומטית ב-07:30
מהמחשב המקומי (עם קישור לאתר החי בהודעת הוואטסאפ).
משתמש: דובר עברית, גר בעתלית. נושאים: כדורגל (ישראל+עולם), פוליטיקה (ישראל),
מזג אוויר (עתלית), AI (חדשות חשובות), בידור, ונושא יומי ללמוד + עובדה.
GitHub: bitonorel9-alt/haboker-sheli · אתר חי: https://bitonorel9-alt.github.io/haboker-sheli/

## ארכיטקטורה
```
index.html                  ← האתר (frontend). Vanilla JS, ללא build. RTL עברית.
                               רקע canvas אנימטיבי, כרטיסי זכוכית, scroll-reveal,
                               מעקב עכבר, החלפת גוון לפי שעה, למידת העדפות (localStorage).
                               מקושר ל-manifest.json + sw.js לצורך התקנה כאפליקציה.
manifest.json                ← מניפסט PWA: שם, אייקונים, צבעים, display=standalone
sw.js                        ← service worker: קאש למסך הבית + טעינה גם בלי אינטרנט
icons/                       ← icon-192.png, icon-512.png, apple-touch-icon.png (נכסים סטטיים)
scripts/collect_news.py      ← אוסף RSS + מזג אוויר, כותב data/news_data.js + .json
scripts/send_email.py        ← בונה מייל HTML מ-data/news_data.json ושולח ב-SMTP
scripts/send_whatsapp.py     ← שולח תמצית טקסט קצרה לוואטסאפ דרך CallMeBot (חינמי)
data/news_data.js            ← window.NEWS_DATA שהאתר טוען (נוצר יומית)
data/prefs.json              ← העדפות שנלמדו מדירוגי 👍/👎
config/email_config.json     ← פרטי SMTP (המשתמש ממלא; לא בגיט)
config/whatsapp_config.json  ← phone+apikey+site_url של CallMeBot (המשתמש ממלא; לא בגיט)
run_daily.bat                ← collect + email + whatsapp (רץ מקומית, למייל/וואטסאפ בלבד)
setup_windows_task.bat       ← מתזמן ל-07:30 (מקומי)
.github/workflows/update-news.yml ← Action מתוזמן (cron) שמריץ collect_news.py בענן
                                    ומקומיט data/news_data.js+.json בחזרה ל-main.
                                    GitHub Pages מגיש את main כאתר חי אחרי כל commit.
                                    בלי סודות — קורא רק RSS/מזג אוויר ציבוריים.
```

## זרימת נתונים
collect_news.py → data/news_data.js (`window.NEWS_DATA={...}`) → index.html קורא ומרנדר.
מבנה כתבה: `{section,title,summary,source,link,stats:[[label,value,pct?],...]}`
`stats` עם ערך שלישי (0-100) מצייר בר התקדמות. כרטיס עם `learn:true` = עיצוב ירוק מיוחד.
אותו data/news_data.json משמש גם את send_email.py וגם את send_whatsapp.py.

## הרצה מקומית
```
pip install feedparser requests
python scripts/collect_news.py     # מייצר נתונים
# פתח index.html בדפדפן (או התקן כאפליקציה — ראו README)
python scripts/send_email.py       # דורש config/email_config.json
python scripts/send_whatsapp.py    # דורש config/whatsapp_config.json (מדלג בשקט אם חסר)
```

## מוסכמות
- אין שלב build, אין תלויות frontend. הכל בקובץ index.html אחד (manifest.json/sw.js הם נכסי PWA סטטיים, לא build step).
- כבד prefers-reduced-motion (כבר ממומש).
- כל טקסט למשתמש בעברית.
- אל תכניס סודות לקוד. SMTP רק דרך config/email_config.json, וואטסאפ רק דרך config/whatsapp_config.json.
- send_whatsapp.py חייב להישאר "fail soft": אם אין config, לצאת בשקט (exit 0) ולא לשבור את run_daily.bat.

## הרחבות אפשריות (רעיונות למשתמש)
- להוסיף מקורות ב-FEEDS (collect_news.py)
- להעביר גם את send_email.py/send_whatsapp.py ל-GitHub Actions (עם GitHub Secrets ל-SMTP/CallMeBot),
  כדי שגם השליחה עצמה לא תהיה תלויה שהמחשב המקומי דלוק ב-07:30
