import feedparser
from datetime import datetime, timedelta, timezone

def test_google_news(num=5):
    feed = feedparser.parse("https://news.google.com/rss/search?q=artificial+intelligence+machine+learning&hl=en-US&gl=US&ceid=US:en")
    print("Raw Google News RSS entries:")
    for entry in feed.entries[:num]:
        print(entry.title)
        print(entry.link)
        print(entry.published if hasattr(entry, 'published') else '')
        print("---")
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    print("Recent Google News headlines:")
    for entry in feed.entries[:num]:
        published = entry.published if hasattr(entry, 'published') else ''
        try:
            pub_date = datetime.strptime(published[:16], "%a, %d %b %Y").replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = None
        if pub_date and pub_date >= one_week_ago:
            print(entry.title)

if __name__ == "__main__":
    test_google_news()
