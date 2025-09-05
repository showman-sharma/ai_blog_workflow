

import requests
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import urlencode
WORDPRESS_CLIENT_ID = os.getenv("WORDPRESS_CLIENT_ID")
WORDPRESS_CLIENT_SECRET = os.getenv("WORDPRESS_CLIENT_SECRET")
WORDPRESS_REDIRECT_URI = os.getenv("WORDPRESS_REDIRECT_URI", "https://showmansharma.wordpress.com/")
WORDPRESS_ACCESS_TOKEN = os.getenv("WORDPRESS_ACCESS_TOKEN")
WORDPRESS_SITE_ID = os.getenv("WORDPRESS_SITE_ID")  # e.g., '123456789' or 'showmansharma.wordpress.com'

def get_wordpress_authorization_url():
    params = {
        "client_id": WORDPRESS_CLIENT_ID,
        "redirect_uri": WORDPRESS_REDIRECT_URI,
        "response_type": "code",
        "scope": "global"
    }
    return f"https://public-api.wordpress.com/oauth2/authorize?{urlencode(params)}"

def get_wordpress_access_token(auth_code):
    url = "https://public-api.wordpress.com/oauth2/token"
    data = {
        "client_id": WORDPRESS_CLIENT_ID,
        "client_secret": WORDPRESS_CLIENT_SECRET,
        "redirect_uri": WORDPRESS_REDIRECT_URI,
        "grant_type": "authorization_code",
        "code": auth_code
    }
    response = requests.post(url, data=data)
    return response.json().get("access_token")

def publish_to_wordpress(title, content):
    if not WORDPRESS_ACCESS_TOKEN:
        print("WordPress access token not set. Please complete OAuth2 flow.")
        return
    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{WORDPRESS_SITE_ID}/posts/new"
    headers = {"Authorization": f"Bearer {WORDPRESS_ACCESS_TOKEN}"}
    data = {
        "title": title,
        "content": content,
        "status": "publish"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"Post published: {response.json().get('URL')}")
    else:
        print(f"Failed to publish post: {response.text}")

load_dotenv()

# MODE: 'local' for Ollama/Phi-3, 'cohere' for Cohere API
AGENT_MODE = os.getenv("AGENT_MODE", "local")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus")

# Ollama and model config
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"

# ArXiv API config
ARXIV_URL = "http://export.arxiv.org/api/query"

# Google News via Serpstack config
SERPSTACK_API_KEY = os.getenv("SERPSTACK_API_KEY")
SERPSTACK_URL = "http://api.serpstack.com/search"

# Helper: Fetch latest AI/ML papers from ArXiv

def fetch_arxiv_ai_papers(max_results=10):
    # Get date 7 days ago
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    params = {
        "search_query": "cat:cs.AI+OR+cat:cs.LG",
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending"
    }
    response = requests.get(ARXIV_URL, params=params)
    root = ET.fromstring(response.content)
    papers = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
        summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
        link = entry.find("{http://www.w3.org/2005/Atom}id").text.strip()
        published = entry.find("{http://www.w3.org/2005/Atom}published").text.strip()
        # Parse published date
        pub_date = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
        if pub_date >= one_week_ago:
            papers.append(f"Title: {title}\nSummary: {summary}\nURL: {link}\nPublished: {published}")
    return "\n\n".join(papers)

# Helper: Search Google News for AI/ML

def serpstack_news_search(query, num=10):
    if not SERPSTACK_API_KEY:
        raise ValueError("SERPSTACK_API_KEY environment variable not set.")
    params = {
        "access_key": SERPSTACK_API_KEY,
        "query": query,
        "type": "news",
        "num": num
    }
    response = requests.get(SERPSTACK_URL, params=params)
    data = response.json()
    results = []
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    if "news_results" in data:
        for item in data["news_results"]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            published = item.get("published", "")
            # Try to parse published date
            try:
                pub_date = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pub_date = None
            if pub_date and pub_date >= one_week_ago:
                results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}\nPublished: {published}")
    return "\n\n".join(results)

# Helper: Use Phi-3 Mini to analyze and decide on deeper research

def summarize_and_ideate(headlines):
    prompt = f"Read these AI/ML news headlines and suggest 2-3 interesting article topics. For each, say if deeper research is needed.\n{headlines}"
    if AGENT_MODE == "cohere":
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY environment variable not set.")
        url = "https://api.cohere.ai/v1/chat"
        headers = {"Authorization": f"Bearer {COHERE_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": COHERE_MODEL,
            "message": prompt,
            "temperature": 0.3,
            "max_tokens": 1024
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["text"]
    else:
        response = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
        return response.json()["response"]

# Helper: Deeper research (ArXiv + News)

def deeper_research(topic):
    print(f"\nDeeper research for topic: {topic}\n")
    arxiv_results = fetch_arxiv_ai_papers(max_results=3)
    news_results = serpstack_news_search(topic, num=3)
    prompt = f"Summarize and collate these findings for the topic '{topic}':\nArXiv:\n{arxiv_results}\n\nNews:\n{news_results}"
    if AGENT_MODE == "cohere":
        if not COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY environment variable not set.")
        url = "https://api.cohere.ai/v1/chat"
        headers = {"Authorization": f"Bearer {COHERE_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": COHERE_MODEL,
            "message": prompt,
            "temperature": 0.3,
            "max_tokens": 2048
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["text"]
    else:
        response = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
        return response.json()["response"]

if __name__ == "__main__":
    print("=== Agentic AI/ML Newsletter Generator ===\n")
    print(f"MODE: {AGENT_MODE}\n")

    # Ensure WordPress OAuth2 is complete before any LLM inferencing
    if not WORDPRESS_ACCESS_TOKEN:
        print("\nTo authorize your app, visit this URL and follow the instructions:")
        print(get_wordpress_authorization_url())
        print("After authorization, use the code to get your access token and add it to your .env file.")
        exit(0)

    print("Fetching latest AI/ML headlines...")
    arxiv_headlines = fetch_arxiv_ai_papers(max_results=5)
    news_headlines = serpstack_news_search("artificial intelligence machine learning", num=5)
    all_headlines = f"ArXiv:\n{arxiv_headlines}\n\nGoogle News:\n{news_headlines}"
    print("\nAnalyzing headlines and ideating topics...")
    topics_summary = summarize_and_ideate(all_headlines)
    print("\nSuggested topics and research needs:\n", topics_summary)
    # Extract topics needing deeper research (simple heuristic: look for lines with 'deeper research needed')
    for line in topics_summary.split('\n'):
        if 'deeper research' in line.lower():
            topic = line.split(':')[0].strip()
            article = deeper_research(topic)
            print(f"\nDrafted article for topic '{topic}':\n{article}\n")
            # Auto-publish to WordPress
            publish_to_wordpress(f"AI/ML Weekly: {topic}", article)
    print("\nNewsletter draft complete!")
