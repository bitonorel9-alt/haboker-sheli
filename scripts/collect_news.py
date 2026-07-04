#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הבוקר שלי — אוסף חדשות יומי
מושך חדשות מהיום האחרון בנושאים: כדורגל (ישראל+עולם), פוליטיקה (ישראל),
מזג אוויר (עתלית), AI, בידור, ונושא יומי ללמוד + עובדה.

מריץ כל בוקר -> כותב news_data.js שהאתר index.html קורא.
תלוי בהעדפות שנלמדו מהדירוגים שלך (prefs.json).

התקנה חד-פעמית:  pip install feedparser requests
"""
import json, datetime, html, re, os, sys, random
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("חסר feedparser. הרץ:  pip install feedparser requests")
    sys.exit(1)

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
PREFS_FILE = DATA / "prefs.json"

# ---- עיר מזג האוויר: עתלית ----
ATLIT_LAT, ATLIT_LON = 32.7100, 34.9400

# ---- מקורות RSS פר-נושא (עדכניים, ציבוריים) ----
FEEDS = {
    "כדורגל": [
        "https://www.one.co.il/cat/coop/xml/rss/mvp.aspx",       # ONE
        "https://rss.walla.co.il/feed/48",                       # וואלה ספורט
        "https://www.espn.com/espn/rss/soccer/news",             # עולמי
    ],
    "פוליטיקה": [
        "https://www.ynet.co.il/Integration/StoryRss2.xml",      # ynet חדשות
        "https://rss.walla.co.il/feed/2686",                     # וואלה חדשות
    ],
    "AI": [
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
    "בידור": [
        "https://rss.walla.co.il/feed/6",                        # וואלה תרבות
        "https://www.ynet.co.il/Integration/StoryRss538.xml",    # ynet בידור
    ],
}

MAX_AGE_HOURS = 30  # "היום האחרון"

def clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return html.unescape(t).strip()

def is_recent(entry):
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            dt = datetime.datetime(*tp[:6])
            age = (datetime.datetime.utcnow() - dt).total_seconds() / 3600
            return age <= MAX_AGE_HOURS
    return True  # אם אין תאריך, ניקח בכל זאת

def fetch_topic(section, urls, limit=3):
    items = []
    for u in urls:
        try:
            feed = feedparser.parse(u)
            for e in feed.entries:
                if not is_recent(e):
                    continue
                title = clean(e.get("title"))
                summ = clean(e.get("summary", e.get("description", "")))
                if not title:
                    continue
                items.append({
                    "section": section,
                    "title": title[:120],
                    "summary": (summ[:200] + "…") if len(summ) > 200 else summ,
                    "source": clean(getattr(feed.feed, "title", u)),
                    "link": e.get("link", ""),
                })
                if len(items) >= limit:
                    break
        except Exception as ex:
            print(f"  אזהרה [{section}] {u}: {ex}")
        if len(items) >= limit:
            break
    return items[:limit]

def fetch_weather():
    """מזג אוויר לעתלית דרך Open-Meteo (חינמי, ללא מפתח)."""
    try:
        import requests
        url = ("https://api.open-meteo.com/v1/forecast"
               f"?latitude={ATLIT_LAT}&longitude={ATLIT_LON}"
               "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
               "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
               "&timezone=Asia%2FJerusalem")
        r = requests.get(url, timeout=10).json()
        cur, day = r.get("current", {}), r.get("daily", {})
        tmax = day.get("temperature_2m_max", [None])[0]
        tmin = day.get("temperature_2m_min", [None])[0]
        rain = day.get("precipitation_probability_max", [0])[0]
        hum = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        return {
            "section": "מזג אוויר",
            "title": f"עתלית · {tmax}° / {tmin}°",
            "summary": f"כרגע {cur.get('temperature_2m')}°, לחות {hum}%, רוח {wind} קמ״ש. סיכוי משקעים {rain}%.",
            "source": "Open-Meteo · השירות המטאורולוגי",
            "link": "",
            "stats": [
                ["מקסימום", f"{tmax}°"],
                ["מינימום", f"{tmin}°"],
                ["לחות", f"{hum}%", int(hum) if hum else 0],
                ["רוח", f"{wind} קמ״ש"],
                ["סיכוי גשם", f"{rain}%", int(rain) if rain else 0],
            ],
        }
    except Exception as ex:
        print(f"  אזהרה מזג אוויר: {ex}")
        return {"section":"מזג אוויר","title":"עתלית — התחזית להיום",
                "summary":"לא הצלחתי למשוך תחזית כרגע.","source":"Open-Meteo","link":"","stats":[]}

# ---- נושא יומי ללמוד + עובדה (מתחלף לפי יום בשנה) ----
LEARN_TOPICS = [
    ("אפקט דנינג-קרוגר", "ככל שאדם יודע פחות בתחום, כך הוא נוטה להעריך את הידע שלו בו ביתר. מומחים אמיתיים דווקא מפחיתים בערך עצמם.", "מוח וקוגניציה"),
    ("למה השמיים כחולים", "אור השמש מתפזר באטמוספרה, והצבע הכחול (גל קצר) מתפזר הכי הרבה — לכן אנחנו רואים אותו מכל הכיוונים.", "פיזיקה"),
    ("ריבית דריבית", "כשהריבית מצטברת גם על הריבית עצמה, הכסף גדל אקספוננציאלית. איינשטיין כינה זאת 'הפלא השמיני'.", "כלכלה"),
    ("מדוע חתולים מגרגרים", "גרגור בתדר 25-150Hz עשוי לזרז ריפוי עצמות ולהרגיע — לא רק סימן לשמחה.", "ביולוגיה"),
    ("פרדוקס הספינה של תזאוס", "אם מחליפים כל חלק בספינה בהדרגה — האם היא עדיין אותה ספינה? שאלה על זהות ורציפות.", "פילוסופיה"),
    ("למה נמלים לא הולכות לאיבוד", "הן משאירות שביל פרומונים; ככל שהמסלול קצר יותר, הריח מתחזק מהר יותר — אלגוריתם מציאת דרך טבעי.", "טבע"),
    ("מהי מטבע קוונטי (Qubit)", "בניגוד לביט רגיל (0 או 1), קיוביט יכול להיות בשני המצבים בו-זמנית — בסיס למחשוב הקוונטי.", "טכנולוגיה"),
]
FACTS = [
    "לתמנון יש שלושה לבבות ודם כחול.",
    "דבש לא מתקלקל — נמצא דבש בן 3,000 שנה שעדיין אכיל.",
    "בננות הן פיזור רדיואקטיבי קל בגלל האשלגן שבהן.",
    "כוכב הנוגה מסתובב הפוך משאר כוכבי הלכת.",
    "המילה 'רובוט' נטבעה במחזה צ׳כי ב-1920.",
    "לב הכחול הכי גדול — הלווייתן הכחול — במשקל של מכונית.",
    "אין מספיק זהב בעולם כדי לצפות בו את כל היבשה.",
]

def learn_card():
    idx = datetime.date.today().toordinal()
    topic, expl, field = LEARN_TOPICS[idx % len(LEARN_TOPICS)]
    fact = FACTS[idx % len(FACTS)]
    return {
        "section": "לומדים", "learn": True,
        "title": topic,
        "summary": expl,
        "source": f"תמצית ידע יומית · {field}",
        "link": "",
        "stats": [["תחום", field], ["עובדה בונוס", fact]],
    }

def load_prefs():
    if PREFS_FILE.exists():
        try: return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except: pass
    return {}

def main():
    print("אוסף חדשות מהיום האחרון…")
    prefs = load_prefs()
    articles = []

    for section, urls in FEEDS.items():
        print(f"· {section}")
        articles += fetch_topic(section, urls, limit=3)

    print("· מזג אוויר (עתלית)")
    weather = fetch_weather()

    # מוסיפים סטטיסטיקות בסיסיות לכתבות ספורט/פוליטיקה שאין להן
    for a in articles:
        if "stats" not in a:
            a["stats"] = [["מקור", a["source"][:20]]]

    learn = learn_card()

    # בחירת הכותרת הראשית: עדיפות לפוליטיקה ישראל, אחרת הכי מדורג
    lead_pool = [a for a in articles if a["section"] == "פוליטיקה"] or articles
    lead_pool.sort(key=lambda a: prefs.get(a["section"], 0), reverse=True)
    lead = lead_pool[0] if lead_pool else {
        "section":"מבזק","title":"אין כותרת זמינה","summary":"נסה שוב מאוחר יותר."}

    # שאר הכתבות ממוינות לפי העדפה נלמדת
    body = [a for a in articles if a is not lead]
    body.sort(key=lambda a: prefs.get(a["section"], 0), reverse=True)
    body = [weather] + body + [learn]

    now = datetime.datetime.now()
    payload = {
        "date": now.strftime("%A, %d %B %Y"),
        "date_he": now.strftime("%d/%m/%Y"),
        "updated": now.strftime("%H:%M"),
        "lead": {
            "section": lead["section"], "eyebrow": "הכותרת של הבוקר",
            "title": lead["title"], "summary": lead["summary"],
        },
        "articles": body,
    }

    out = DATA / "news_data.js"
    out.write_text("window.NEWS_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";",
                   encoding="utf-8")
    # גם JSON נקי לשליחת המייל
    (DATA / "news_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✓ נשמרו {len(body)} כתבות -> {out}")
    print(f"✓ כותרת ראשית: {lead['title'][:60]}")

if __name__ == "__main__":
    main()
