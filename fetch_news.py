import feedparser
import json
import os
from datetime import datetime, timedelta, timezone
from googletrans import Translator
from dateutil import parser as date_parser

# Configuration
COUNTRY = "cuba"
RSS_FEEDS = {
    "Granma": "https://en.granma.cu/feed",
    "14ymedio": "https://www.14ymedio.com/rss/",
    "Juventud Rebelde": "https://www.juventudrebelde.cu/rss",
    "Trabajadores": "https://www.trabajadores.cu/feed",
    "Havana Times": "https://havanatimes.org/feed/",
    "5 Septiembre": "https://www.5septiembre.cu/feed/",
    "Directorio Cubano": "https://www.directoriocubano.info/feed/",
    "Adelante": "https://www.adelante.cu/index.php/es/?format=feed&type=rss"
}

CATEGORIES = ["Diplomacy", "Military", "Energy", "Economy", "Local Events"]
MAX_AGE_DAYS = 7
TARGET_PER_CAT = 20
FILE_PATH = f"docs/{COUNTRY}_news.json"

translator = Translator()

def get_category(text):
    text = text.lower()
    if any(w in text for w in ['minrex', 'canciller', 'embajador', 'relaciones', 'diplomacia', 'bloqueo']): return "Diplomacy"
    if any(w in text for w in ['minfar', 'ejército', 'militar', 'defensa', 'fuerzas armadas']): return "Military"
    if any(w in text for w in ['unión eléctrica', 'apagón', 'energía', 'petróleo', 'combustible', 'luz']): return "Energy"
    if any(w in text for w in ['mipyme', 'divisas', 'pib', 'finanzas', 'economía', 'banco', 'zedm']): return "Economy"
    return "Local Events"

def fetch_and_process():
    if not os.path.exists("docs"):
        os.makedirs("docs")

    existing_data = []
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, 'r') as f:
                existing_data = json.load(f)
        except:
            existing_data = []

    new_stories = []
    seen_urls = {s['url'] for s in existing_data}
    now = datetime.now(timezone.utc)

    for source_name, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            try:
                pub_date = date_parser.parse(entry.published)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                
                if (now - pub_date).days > MAX_AGE_DAYS:
                    continue
                
                if entry.link not in seen_urls:
                    # Translate Title (Spanish to English)
                    translated_title = translator.translate(entry.title, src='es', dest='en').text
                    
                    story = {
                        "title": translated_title,
                        "source": source_name,
                        "url": entry.link,
                        "published_date": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "category": get_category(entry.title + " " + getattr(entry, 'summary', ''))
                    }
                    new_stories.append(story)
                    seen_urls.add(entry.link)
            except:
                continue

    # Combine and deduplicate
    all_stories = new_stories + existing_data
    fresh_stories = []
    seen = set()
    for s in all_stories:
        dt = datetime.strptime(s['published_date'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if (now - dt).days <= MAX_AGE_DAYS and s['url'] not in seen:
            fresh_stories.append(s)
            seen.add(s['url'])

    # Sort by newest first
    fresh_stories.sort(key=lambda x: x['published_date'], reverse=True)

    # Maintain balance: 20 per category
    final_output = []
    for cat in CATEGORIES:
        cat_group = [s for s in fresh_stories if s['category'] == cat][:TARGET_PER_CAT]
        final_output.extend(cat_group)

    with open(FILE_PATH, 'w') as f:
        json.dump(final_output, f, indent=4)

if __name__ == "__main__":
    fetch_and_process()
