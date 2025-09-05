# LangChain-based Agentic AI/ML Newsletter Workflow

"""
This script uses LangChain to orchestrate the workflow:
- Fetch AI/ML news headlines (Serpstack)
- Fetch recent AI/ML research papers (ArXiv)
- Summarize and ideate topics (LLM)
- Draft full articles (LLM)
- Auto-publish to WordPress

Supports both local (Ollama) and cloud (Cohere) LLMs.
"""

import os
from dotenv import load_dotenv
from langchain.chains import SequentialChain
from langchain.prompts import PromptTemplate
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import cohere
import feedparser

load_dotenv()

# Config
AGENT_MODE = os.getenv("AGENT_MODE", "cohere")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus")
SERPSTACK_API_KEY = os.getenv("SERPSTACK_API_KEY")
WORDPRESS_ACCESS_TOKEN = os.getenv("WORDPRESS_ACCESS_TOKEN")
WORDPRESS_SITE_ID = os.getenv("WORDPRESS_SITE_ID")

# LLM setup
llm = None
if AGENT_MODE == "cohere":
    cohere_client = cohere.Client(COHERE_API_KEY)
else:
    from langchain_community.llms import Ollama
    llm = Ollama(model="phi3")

# Step 1: Fetch news headlines
def fetch_news(query="artificial intelligence machine learning", num=5):
    params = {
        "access_key": SERPSTACK_API_KEY,
        "query": query,
        "type": "news",
        "num": num
    }
    sources = []
    try:
        response = requests.get("http://api.serpstack.com/search", params=params)
        print("=== DEBUG: Raw Serpstack Response ===\n", response.text)
        data = response.json()
        results = []
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        if "news_results" in data:
            for item in data["news_results"]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                url = item.get("url", "")
                source_name = item.get("source_name", "")
                published = item.get("published", "")
                # Try to parse published date
                try:
                    pub_date = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    pub_date = None
                if pub_date and pub_date >= one_week_ago:
                    results.append(f"Title: {title}<br>Snippet: {snippet}<br>URL: {url}<br>Published: {published}")
                    sources.append((title, url, source_name))
        if results:
            return "<br><br>".join(results), sources
    except Exception as e:
        print("Serpstack failed:", e)
    # Fallback: Google News RSS
    print("Falling back to Google News RSS...")
    feed = feedparser.parse("https://news.google.com/rss/search?q=artificial+intelligence+machine+learning&hl=en-US&gl=US&ceid=US:en")
    results = []
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    for entry in feed.entries[:num]:
        title = entry.title
        summary = entry.summary if hasattr(entry, 'summary') else ''
        link = entry.link
        published = entry.published if hasattr(entry, 'published') else ''
        try:
            pub_date = datetime.strptime(published[:16], "%a, %d %b %Y")
            # Make pub_date timezone-aware (UTC)
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = None
        if pub_date and pub_date >= one_week_ago:
            results.append(f"Title: {title}<br>Summary: {summary}<br>URL: {link}<br>Published: {published}")
            # Try to get source name from entry if available
            source_name = entry.get('source', None)
            if not source_name:
                # Try to parse from link domain
                from urllib.parse import urlparse
                domain = urlparse(link).netloc.replace('www.', '')
                source_name = domain.split('.')[0].capitalize() + ' News'
            sources.append((title, link, source_name))
    return "<br><br>".join(results), sources

# Step 2: Fetch ArXiv papers
def fetch_arxiv(max_results=5):
    ARXIV_URL = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI+OR+cat:cs.LG",
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending"
    }
    try:
        response = requests.get(ARXIV_URL, params=params)
        print("=== DEBUG: Raw ArXiv Response ===\n", response.text)
        root = ET.fromstring(response.content)
        papers = []
        sources = []
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
            link = entry.find("{http://www.w3.org/2005/Atom}id").text.strip()
            published = entry.find("{http://www.w3.org/2005/Atom}published").text.strip()
            pub_date = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
            pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date >= one_week_ago:
                papers.append(f"Title: {title}<br>Summary: {summary}<br>URL: {link}<br>Published: {published}")
                sources.append((title, link, "arXiv"))
        return "<br><br>".join(papers), sources
    except Exception as e:
        print("ArXiv fetch failed:", e)
        return "", []

# Step 3: Summarize and ideate topics
summarize_prompt = PromptTemplate(
    input_variables=["headlines"],
    template="""
Read these AI/ML news headlines and research summaries. Suggest 2-3 interesting newsletter article topics. For each, say if deeper research is needed.\n\n{headlines}
"""
)

# Step 4: Draft full article
article_prompt = PromptTemplate(
    input_variables=["topic", "news", "papers"],
    template="""
Write a concise, visually balanced newsletter article on the topic '{topic}'.
You MUST use ONLY the following news and research findings from the past week. Do NOT add generic content or examples not present in the provided sources. If no research papers are found, state so briefly.

IMPORTANT: Do NOT use Markdown. Output ONLY valid HTML, matching the structure below.

<h2>AI/ML Weekly</h2>
<h3>This Week in AI: {topic}</h3>

<h4>In the News:</h4>
<ul>
{news}
</ul>

<h4>Research Breakthroughs:</h4>
<ul>
{papers}
</ul>

<p>Stay tuned for further developments and insights in the world of AI!</p>
"""
)

# Step 5: Publish to WordPress
def publish_to_wordpress(title, content):
    if not WORDPRESS_ACCESS_TOKEN:
        print("WordPress access token not set. Please add it to your .env file.")
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

if __name__ == "__main__":
    print("=== LangChain Agentic AI/ML Newsletter Generator ===\n")
    print(f"MODE: {AGENT_MODE}\n")
    news, news_sources = fetch_news()
    papers, paper_sources = fetch_arxiv()
    print("\n=== DEBUG: News Headlines Sent to LLM ===\n", news)
    print("\n=== DEBUG: ArXiv Papers Sent to LLM ===\n", papers)
    headlines = f"News:\n{news}\n\nArXiv:\n{papers}"
    print("\nAnalyzing headlines and ideating topics...")
    prompt_text = (
        "Using ONLY the following news headlines and research summaries, write a newsletter article that summarizes the actual events, breakthroughs, and papers from the past week. Do NOT add generic content or examples not present in the provided sources. Focus ONLY on the specific content provided.\n\n"
        f"{headlines}"
    )
    if AGENT_MODE == "cohere":
        response = cohere_client.chat(
            model=COHERE_MODEL,
            message=prompt_text,
            temperature=0.4,
            max_tokens=2048
        )
        article = response.text
    else:
        article = llm.invoke(prompt_text)
    # --- POST-PROCESSING: Convert Markdown to HTML if needed ---
    import markdown
    if article.strip().startswith("#") or "<h2>" not in article:
        article = markdown.markdown(article)
    print("\nNewsletter summary and analysis:\n", article)
    # --- Generate smart, engaging blog post title ---
    import re
    # Extract main topic from <h3>
    main_topic = None
    h3_match = re.search(r'<h3>(.*?)</h3>', article)
    if h3_match:
        main_topic = h3_match.group(1).strip()
    # Extract top 2 headlines from <li><strong>
    headlines = re.findall(r'<li><strong>(.*?)</strong>', article)
    # Build engaging title
    if main_topic and headlines:
        post_title = f"AI/ML Weekly: {main_topic} — {headlines[0]}"
    elif headlines:
        # Combine two top headlines if available
        if len(headlines) > 1:
            post_title = f"AI/ML Weekly: {headlines[0]} & {headlines[1]}"
        else:
            post_title = f"AI/ML Weekly: {headlines[0]}"
    elif main_topic:
        post_title = f"AI/ML Weekly: {main_topic}"
    else:
        post_title = "AI/ML Weekly: Breakthroughs, Comebacks & Grants"
    # --- Add References section ---
    all_sources = news_sources + paper_sources
    if all_sources:
        references_html = "<h4>References</h4><ul>"
        for title, url, source in all_sources:
            # Clean up source name if it's a dict or unexpected type
            if isinstance(source, dict):
                source_name = source.get('title', url)
            else:
                source_name = str(source)
            references_html += f'<li><a href="{url}" target="_blank">{title}</a> <span style="color:#6f6f6f">({source_name})</span></li>'
        references_html += "</ul>"
        article += references_html
    publish_to_wordpress(post_title, article)
    print(f"\nBlog post titled: {post_title}")
    print("\nNewsletter draft complete!")
