import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

def test_arxiv(max_results=5):
    ARXIV_URL = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI+OR+cat:cs.LG",
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending"
    }
    response = requests.get(ARXIV_URL, params=params)
    print("Raw ArXiv response:")
    print(response.text[:1000])  # Print first 1000 chars for brevity
    root = ET.fromstring(response.content)
    papers = []
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
        published = entry.find("{http://www.w3.org/2005/Atom}published").text.strip()
        pub_date = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
        pub_date = pub_date.replace(tzinfo=timezone.utc)
        if pub_date >= one_week_ago:
            papers.append(title)
    print("Recent ArXiv papers:")
    print(papers)

if __name__ == "__main__":
    test_arxiv()
