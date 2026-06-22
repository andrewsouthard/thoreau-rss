#!/usr/bin/env python3
"""
Daily Thoreau Journal RSS Generator
Pulls today's journal entry from the SQLite DB and generates an RSS feed.
"""

import sqlite3
import html
import re
import os
import urllib.request
from datetime import datetime, timezone

DB_URL = "https://raw.githubusercontent.com/andrewsouthard/thoreau-journals/main/thoreau_journals.db"
DB_PATH = "/tmp/thoreau_journals.db"
OUTPUT_DIR = "/home/andrew/thoreau-rss"

def get_today():
    now = datetime.now()
    return now.month, now.day, now.year

def html_to_text(content):
    """Strip HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', content)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_today_entry():
    """Download DB and find today's entry."""
    # Download fresh copy
    urllib.request.urlretrieve(DB_URL, DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    month, day, year = get_today()
    
    # Try exact month/day match
    cursor.execute(
        "SELECT id, author, title, content, words, year, month, day, created_at "
        "FROM journal_entries WHERE month = ? AND day = ? ORDER BY year DESC LIMIT 1",
        (month, day)
    )
    rows = cursor.fetchall()
    
    # Fallback: closest day in same month
    if not rows:
        cursor.execute(
            "SELECT id, author, title, content, words, year, month, day, created_at "
            "FROM journal_entries WHERE month = ? ORDER BY ABS(day - ?) ASC, year DESC LIMIT 1",
            (month, day)
        )
        rows = cursor.fetchall()
    
    # Fallback: latest entry overall
    if not rows:
        cursor.execute(
            "SELECT id, author, title, content, words, year, month, day, created_at "
            "FROM journal_entries WHERE month IS NOT NULL ORDER BY year DESC, month DESC, day DESC LIMIT 1"
        )
        rows = cursor.fetchall()
    
    conn.close()
    
    if not rows:
        return None
    
    row = rows[0]
    return {
        "id": row[0],
        "author": row[1],
        "title": row[2],
        "content": row[3],
        "words": row[4],
        "year": row[5],
        "month": row[6],
        "day": row[7],
        "created_at": row[8],
    }

def generate_rss(entry):
    """Generate RSS 2.0 XML from entry."""
    month, day, year = get_today()
    
    entry_date = datetime(entry["year"], entry["month"], entry["day"])
    date_str = entry_date.strftime("%B %d, %Y")
    
    item_title = entry["title"] or f"Thoreau Journal - {date_str}"
    item_desc = entry["content"]
    item_guid = f"thoreau-{entry['year']}-{entry['month']:02d}-{entry['day']:02d}-{entry['id']}"
    item_link = "https://github.com/andrewsouthard/thoreau-journals"
    item_pubdate = entry["created_at"] or datetime.now().isoformat()
    
    # Format pubdate as RFC 822
    if isinstance(item_pubdate, str):
        try:
            from email.utils import format_datetime
            pub = datetime.fromisoformat(item_pubdate.replace("Z", "+00:00"))
            item_pubdate = format_datetime(pub)
        except:
            item_pubdate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    escape = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    now_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Thoreau Daily Journal</title>
    <link>https://github.com/andrewsouthard/thoreau-journals</link>
    <description>A daily entry from Henry David Thoreau's journals, delivered fresh each day.</description>
    <language>en-us</language>
    <lastBuildDate>{now_str}</lastBuildDate>
    <atom:link href="https://andrewsouthard.github.io/thoreau-rss/feed.xml" rel="self" type="application/rss+xml"/>
    <item>
      <title>{escape(item_title)}</title>
      <description>{escape(item_desc)}</description>
      <pubDate>{item_pubdate}</pubDate>
      <guid>{item_guid}</guid>
      <link>{item_link}</link>
    </item>
  </channel>
</rss>"""
    return xml

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    entry = get_today_entry()
    
    if entry is None:
        print("ERROR: No journal entry found for today")
        return
    
    rss = generate_rss(entry)
    
    output_path = os.path.join(OUTPUT_DIR, "feed.xml")
    with open(output_path, "w") as f:
        f.write(rss)
    
    print(f"Generated RSS feed at {output_path}")
    print(f"Entry: {entry['year']}-{entry['month']:02d}-{entry['day']:02d} ({entry['words']} words)")

if __name__ == "__main__":
    main()
