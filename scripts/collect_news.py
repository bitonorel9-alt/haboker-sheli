#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הבוקר שלי — אוסף חדשות
מושך חדשות מהיום האחרון בנושאים: כדורגל (ישראל+עולם, כולל תוצאות חיות מ-365Scores),
פוליטיקה (ישראל), מזג אוויר (עתלית), AI, בידור, ונושא יומי ללמוד + עובדה.

רץ כל שעה עגולה דרך GitHub Actions -> כותב news_data.js שהאתר index.html קורא.
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

# ---- מקורות RSS פר-נושא (עדכניים, ציבוריים, כולם בעברית) ----
FEEDS = {
    "כדורגל": [
        "https://www.one.co.il/cat/coop/xml/rss/mvp.aspx",       # ONE (ישראל + עולם)
        "https://rss.walla.co.il/feed/48",                       # וואלה ספורט
        "https://www.ynet.co.il/Integration/StoryRss3.xml",      # ynet ספורט (ישראל + עולם, גיבוי)
    ],
    "פוליטיקה": [
        "https://www.ynet.co.il/Integration/StoryRss2.xml",      # ynet חדשות
        "https://rss.walla.co.il/feed/2686",                     # וואלה חדשות
    ],
    "AI": [
        "https://www.geektime.co.il/feed/",                      # גיקטיים - טכנולוגיה ו-AI בעברית
    ],
    "בידור": [
        "https://rss.walla.co.il/feed/6",                        # וואלה תרבות
        "https://www.ynet.co.il/Integration/StoryRss538.xml",    # ynet בידור
    ],
}

# מקורות RSS כלליים לפעמים מערבבים תוכן זר (הוליווד/ארה"ב) - מילות מפתח לדחוף אחורה
FOREIGN_ENTERTAINMENT_KEYWORDS = ["הוליווד", "אמריקני", "אמריקאי", "אמריקה", "ארה\"ב",
                                  "ספרינגסטין", "מדונה", "טיילור סוויפט", "נטפליקס", "מרוול"]

MAX_AGE_HOURS = 30  # "היום האחרון"
# לבידור נותנים חלון רחב יותר: פחות כתבות ביום, וכך יש סיכוי טוב יותר למצוא מספיק
# תוכן ישראלי לפני שנופלים חזרה על תוכן זר (ראו TOPIC_FILTERS)
TOPIC_MAX_AGE_HOURS = {"בידור": 72}

def clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return html.unescape(t).strip()

def is_recent(entry, max_age=MAX_AGE_HOURS):
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            dt = datetime.datetime(*tp[:6])
            age = (datetime.datetime.utcnow() - dt).total_seconds() / 3600
            return age <= max_age
    return True  # אם אין תאריך, ניקח בכל זאת

AI_KEYWORDS = ["בינה מלאכותית", "ai", "chatgpt", "gpt", "מודל שפה", "למידת מכונה",
               "אנתרופיק", "openai", "קלוד", "gemini", "רובוט", "אלגוריתם"]

# סינון רלוונטיות פר-נושא: include = תעדוף כתבות שמכילות מילת מפתח, exclude = דחיפת כתבות כאלה אחורה
TOPIC_FILTERS = {
    "AI": (AI_KEYWORDS, "include"),
    "בידור": (FOREIGN_ENTERTAINMENT_KEYWORDS, "exclude"),
}

def extract_image(entry, raw_html):
    """מנסה לשלוף תמונת כתבה: media:thumbnail/content, enclosure, או <img> ראשון בתיאור הגולמי."""
    for key in ("media_thumbnail", "media_content"):
        media = entry.get(key)
        if media:
            url = media[0].get("url")
            if url:
                return url
    for link_obj in entry.get("links", []):
        if link_obj.get("rel") == "enclosure" and str(link_obj.get("type", "")).startswith("image"):
            return link_obj.get("href")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html or "")
    return m.group(1) if m else None

def fetch_topic(section, urls, limit=3):
    keywords, mode = TOPIC_FILTERS.get(section, (None, None))
    max_age = TOPIC_MAX_AGE_HOURS.get(section, MAX_AGE_HOURS)
    items, extra = [], []
    for u in urls:
        try:
            feed = feedparser.parse(u)
            for e in feed.entries:
                if not is_recent(e, max_age):
                    continue
                title = clean(e.get("title"))
                raw_summ = e.get("summary", e.get("description", ""))
                summ = clean(raw_summ)
                if not title:
                    continue
                item = {
                    "section": section,
                    "title": title[:120],
                    "summary": (summ[:260] + "…") if len(summ) > 260 else summ,
                    "source": clean(getattr(feed.feed, "title", u)),
                    "link": e.get("link", ""),
                    "image": extract_image(e, raw_summ),
                }
                if keywords:
                    hay = (title + " " + summ).lower()
                    matched = any(k.lower() in hay for k in keywords)
                    is_preferred = matched if mode == "include" else not matched
                    (items if is_preferred else extra).append(item)
                else:
                    items.append(item)
                if len(items) >= limit:
                    break
        except Exception as ex:
            print(f"  אזהרה [{section}] {u}: {ex}")
        if len(items) >= limit:
            break
    items = (items + extra)[:limit]
    return items

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

# ---- תוצאות כדורגל בזמן אמת (365Scores) ----
# הערה: זהו ה-API הפנימי (לא רשמי) שאתר 365Scores עצמו משתמש בו. ציבורי וללא מפתח,
# אבל לא מתועד רשמית - אם ישבר/יחסם בעתיד, הכרטיס פשוט לא יופיע (fail-soft).
ISRAELI_TEAM_HE = {
    "Maccabi Tel Aviv": "מכבי תל אביב", "Hapoel Tel Aviv": "הפועל תל אביב",
    "Maccabi Haifa": "מכבי חיפה", "Hapoel Haifa": "הפועל חיפה",
    "Hapoel Beer Sheva": "הפועל באר שבע", "Beitar Jerusalem": "בית\"ר ירושלים",
    "Hapoel Jerusalem": "הפועל ירושלים", "Maccabi Netanya": "מכבי נתניה",
    "Hapoel Petah Tikva": "הפועל פתח תקווה", "Maccabi Petah Tikva": "מכבי פתח תקווה",
    "Bnei Sakhnin": "בני סכנין", "Ashdod": "מ.ס. אשדוד",
    "Maccabi Bnei Reineh": "מכבי בני ריינה", "Hapoel Hadera": "הפועל חדרה",
    "Ironi Kiryat Shmona": "עירוני קריית שמונה", "Ironi Tiberias": "עירוני טבריה",
    "Hapoel Rishon LeZion": "הפועל ראשון לציון",
}
STATUS_HE = {
    "Scheduled": "טרם התחיל", "Not Started": "טרם התחיל",
    "Live": "בשידור חי", "In Progress": "מתקיים כעת", "Half Time Break": "מחצית",
    "Halftime": "מחצית", "1st Half": "מחצית ראשונה", "2nd Half": "מחצית שנייה",
    "Ended": "הסתיים", "Finished": "הסתיים", "Just Ended": "הסתיים הרגע",
    "Final Result Only": "הסתיים", "Postponed": "נדחה", "Cancelled": "בוטל",
}
# משחקים חיים/שהסתיימו זה עתה מעניינים יותר ממשחקים עתידיים - סדר תצוגה
STATUS_GROUP_PRIORITY = {3: 0, 4: 1, 2: 2}

def he_team(name):
    return ISRAELI_TEAM_HE.get(name, name)

def he_status(text):
    return STATUS_HE.get(text, text)

def games_to_rows(games, limit=5):
    games = sorted(games, key=lambda g: STATUS_GROUP_PRIORITY.get(g.get("statusGroup"), 9))[:limit]
    rows = []
    for g in games:
        home, away = g.get("homeCompetitor", {}), g.get("awayCompetitor", {})
        hs, as_ = home.get("score"), away.get("score")
        started = hs is not None and as_ is not None and hs >= 0 and as_ >= 0
        status = he_status(g.get("statusText", ""))
        value = f"{hs:g}:{as_:g} · {status}" if started else status
        matchup = f"{he_team(home.get('name',''))} נגד {he_team(away.get('name',''))}"
        rows.append([matchup, value])
    return rows

def fetch_israel_scores():
    try:
        import requests
        url = "https://webws.365scores.com/web/games/current/?sports=1&countries=6"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}).json()
        rows = games_to_rows(r.get("games") or [])
        if not rows:
            return None
        return {
            "section": "כדורגל",
            "title": "תוצאות בזמן אמת · ישראל",
            "summary": "עדכון חי ממשחקי הכדורגל בישראל - מתעדכן בכל איסוף.",
            "source": "365Scores",
            "link": "https://www.365scores.com/he/football/israel",
            "image": None,
            "stats": rows,
        }
    except Exception as ex:
        print(f"  אזהרה 365Scores (ישראל): {ex}")
        return None

# שמות תחרויות "חשובות" - זיהוי לפי שם מדויק (לא substring, כדי לא לתפוס בטעות
# ליגות כמו "Canadian Premier League") ולא לפי popularityRank (שדה לא אמין: הוא
# מצטבר על פני זמן ולא משקף חשיבות "עכשיו", ולכן העדיף בעבר ליגות זוטריות שדווקא
# שיחקו ברגע הדגימה). אם אף אחת מהן לא משחקת כרגע - פשוט לא יופיע כרטיס (fail-soft).
IMPORTANT_COMPETITION_NAMES = {
    "fifa world cup", "world cup", "uefa champions league", "champions league",
    "uefa europa league", "europa league", "uefa europa conference league",
    "premier league", "la liga", "laliga", "serie a", "bundesliga", "ligue 1",
    "uefa european championship", "european championship", "euro",
    "copa america", "conmebol copa libertadores", "copa libertadores",
    "fa cup", "uefa super cup", "uefa nations league",
}

def fetch_world_scores():
    """המשחקים החשובים בעולם כרגע, מתוך רשימת תחרויות מוכרות (לא תלוי בישראל)."""
    try:
        import requests
        url = "https://webws.365scores.com/web/games/current/?sports=1"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}).json()
        comps = r.get("competitions") or []
        top_ids = {
            c["id"] for c in comps
            if (c.get("name") or "").strip().lower() in IMPORTANT_COMPETITION_NAMES
        }
        if not top_ids:
            return None
        games = [g for g in (r.get("games") or []) if g.get("competitionId") in top_ids]
        rows = games_to_rows(games)
        if not rows:
            return None
        return {
            "section": "כדורגל",
            "title": "תוצאות בזמן אמת · עולם",
            "summary": "המשחקים החשובים בעולם כרגע, מהתחרויות המוכרות ביותר.",
            "source": "365Scores",
            "link": "https://www.365scores.com/he/football",
            "image": None,
            "stats": rows,
        }
    except Exception as ex:
        print(f"  אזהרה 365Scores (עולם): {ex}")
        return None

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

HEB_DAYS = ["יום ראשון", "יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת"]
HEB_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
              "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]

def hebrew_date(now):
    day_name = HEB_DAYS[int(now.strftime("%w"))]  # %w: 0=ראשון..6=שבת, לא תלוי locale
    return f"{day_name}, {now.day} ב{HEB_MONTHS[now.month - 1]} {now.year}"

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

    print("· תוצאות כדורגל בזמן אמת (365Scores) - ישראל ועולם")
    live_scores = [c for c in (fetch_israel_scores(), fetch_world_scores()) if c]

    # מוסיפים סטטיסטיקות בסיסיות לכתבות ספורט/פוליטיקה שאין להן
    for a in articles:
        if "stats" not in a:
            a["stats"] = [["מקור", a["source"][:20]]]

    learn = learn_card()

    # בחירת הכותרת הראשית: עדיפות לפוליטיקה ישראל, אחרת הכי מדורג
    lead_pool = [a for a in articles if a["section"] == "פוליטיקה"] or articles
    lead_pool.sort(key=lambda a: prefs.get(a["section"], 0), reverse=True)
    lead = lead_pool[0] if lead_pool else {
        "section": "מבזק", "title": "אין כותרת זמינה", "summary": "נסה שוב מאוחר יותר.",
        "link": "", "image": None}

    # שאר הכתבות ממוינות לפי העדפה נלמדת
    body = [a for a in articles if a is not lead]
    body.sort(key=lambda a: prefs.get(a["section"], 0), reverse=True)
    body = [weather] + live_scores + body + [learn]

    now = datetime.datetime.now()
    payload = {
        "date": hebrew_date(now),
        "date_he": now.strftime("%d/%m/%Y"),
        "updated": now.strftime("%H:%M"),
        "lead": {
            "section": lead["section"], "eyebrow": "הכותרת של הבוקר",
            "title": lead["title"], "summary": lead["summary"],
            "link": lead.get("link", ""), "image": lead.get("image"),
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
