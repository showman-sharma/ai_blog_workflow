# LangChain-based Agentic AI/ML Newsletter Workflow (solid: no empty/broken posts)
# - Resolves Google News redirect links to final publisher URL
# - Builds HTML deterministically (LLM only writes short text blocks)
# - Accepts 200/201 as WordPress success

import os
from dotenv import load_dotenv
from typing import List, Tuple
import logging
import requests
from requests.adapters import HTTPAdapter, Retry
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
import feedparser
import html
import re

from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseLanguageModel
from langchain_community.llms import Ollama

import os
from dotenv import load_dotenv
from typing import List, Tuple
import logging
import time
import requests
from requests.adapters import HTTPAdapter, Retry
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import feedparser

from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_core.language_models import BaseLanguageModel

# LLMs
from langchain_community.llms import Ollama
try:
    from langchain_community.llms import Cohere as LC_Cohere
    _HAS_LC_COHERE = True
except Exception:
    _HAS_LC_COHERE = False

# Import style guide
from style_guide import STYLE_GUIDE

# -----------------------------------------------------------------------------
# HTTP Session with retries
# -----------------------------------------------------------------------------
# LangChain-based Agentic AI/ML Newsletter Workflow (solid: no empty/broken posts)
# - Resolves Google News redirect links to final publisher URL
# - Builds HTML deterministically (LLM only writes short text blocks)
# - Accepts 200/201 as WordPress success

import os
from dotenv import load_dotenv
load_dotenv()

# Config (set in .env)
AGENT_MODE = os.getenv("AGENT_MODE", "cohere").lower()  # "cohere" or "ollama"
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus")
SERPSTACK_API_KEY = os.getenv("SERPSTACK_API_KEY", "")
WORDPRESS_ACCESS_TOKEN = os.getenv("WORDPRESS_ACCESS_TOKEN", "")
WORDPRESS_SITE_ID = os.getenv("WORDPRESS_SITE_ID", "")
PUBLISH = os.getenv("PUBLISH", "false").lower() == "true"  # guardrail

# Logging setup (must be before any use of 'log')
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("aiml-newsletter")

from typing import List, Tuple
import logging
import time
import requests
from requests.adapters import HTTPAdapter, Retry
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import feedparser

from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_core.language_models import BaseLanguageModel

# LLMs
from langchain_community.llms import Ollama
try:
    from langchain_community.llms import Cohere as LC_Cohere
    _HAS_LC_COHERE = True
except Exception:
    _HAS_LC_COHERE = False

# -----------------------------------------------------------------------------
# HTTP Session with retries
# -----------------------------------------------------------------------------
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    s.headers.update({"User-Agent": "AIML-Newsletter/1.3 (+https://example.com)"})
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

HTTP = make_session()
UTC = timezone.utc

# -----------------------------------------------------------------------------
# LLM setup
# -----------------------------------------------------------------------------
def get_llm() -> BaseLanguageModel:
    if AGENT_MODE == "cohere" and _HAS_LC_COHERE and COHERE_API_KEY:
        log.info(f"Using Cohere model: {COHERE_MODEL}")
        return LC_Cohere(cohere_api_key=COHERE_API_KEY, model=COHERE_MODEL)
    log.info("Falling back to Ollama: phi3")
    return Ollama(model="phi3")

llm: BaseLanguageModel = get_llm()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def week_ago() -> datetime:
    return datetime.now(UTC) - timedelta(days=7)

def fmt_rfc822(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")

def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "source"
    except Exception:
        return "source"

def resolve_final_url(link: str) -> str:
    """
    Resolve Google News / other redirects to a clean publisher URL.
    Best-effort: follow redirects; if it fails, return original link.
    """
    if not link:
        return link
    try:
        # Some Google links include a real URL as a param, try to extract it first
        q = urlparse(link).query
        qs = parse_qs(q)
        for key in ("url", "u", "link"):
            if key in qs and qs[key]:
                return qs[key][0]
        # Else follow redirects
        r = HTTP.get(link, timeout=12, allow_redirects=True)
        final = r.url or link
        # guard against news.google.com final
        return final
    except Exception:
        return link

def li(title: str, url: str, src: str, published: str) -> str:
    return f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a> — <em>{html.escape(src)} • {html.escape(published)}</em></li>'

# -----------------------------------------------------------------------------
# Step 1: Fetch news (Serpstack -> Google News RSS fallback)
# -----------------------------------------------------------------------------
def fetch_news(query: str = "artificial intelligence machine learning", num: int = 6) -> Tuple[str, List[Tuple[str, str, str]]]:
    items: List[str] = []
    sources: List[Tuple[str, str, str]] = []
    seen = set()
    cutoff = week_ago()

    # Serpstack
    if SERPSTACK_API_KEY:
        try:
            params = {"access_key": SERPSTACK_API_KEY, "query": query, "type": "news", "num": num}
            resp = HTTP.get("http://api.serpstack.com/search", params=params, timeout=15)
            data = resp.json() if resp.ok else {}
            for it in (data.get("news_results") or [])[: num * 3]:
                title = (it.get("title") or "").strip()
                raw_url = (it.get("url") or "").strip()
                if not title or not raw_url:
                    continue
                src = (it.get("source_name") or "").strip() or domain_of(raw_url)
                published = (it.get("published") or "").strip()
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except Exception:
                    try:
                        pub_dt = datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
                    except Exception:
                        pub_dt = None
                if not pub_dt or pub_dt < cutoff:
                    continue
                url = resolve_final_url(raw_url)
                key = (title, url)
                if key in seen:
                    continue
                seen.add(key)
                items.append(li(title, url, src, fmt_rfc822(pub_dt)))
                sources.append((title, url, src))
                if len(items) >= num:
                    break
            if items:
                return "\n".join(items), sources
        except Exception as e:
            log.warning(f"Serpstack failed: {e}")

    # Google News RSS fallback
    log.info("Falling back to Google News RSS…")
    feed = feedparser.parse(
        "https://news.google.com/rss/search?q=artificial+intelligence+machine+learning&hl=en-US&gl=US&ceid=US:en"
    )
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        raw_link = getattr(entry, "link", "").strip()
        published = getattr(entry, "published", "").strip()
        if not title or not raw_link or not published:
            continue
        try:
            pub_dt = datetime(*entry.published_parsed[:6], tzinfo=UTC)  # type: ignore[attr-defined]
        except Exception:
            try:
                pub_dt = datetime.strptime(published[:16], "%a, %d %b %Y").replace(tzinfo=UTC)
            except Exception:
                pub_dt = None
        if not pub_dt or pub_dt < cutoff:
            continue
        url = resolve_final_url(raw_link)
        src = domain_of(url)
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        items.append(li(title, url, src, fmt_rfc822(pub_dt)))
        sources.append((title, url, src))
        if len(items) >= num:
            break

    if not items:
        items = ['<li>No recent news found.</li>']
    return "\n".join(items), sources

# -----------------------------------------------------------------------------
# Step 2: Fetch arXiv (recent by updated date)
# -----------------------------------------------------------------------------
def fetch_arxiv(max_results: int = 6) -> Tuple[str, List[Tuple[str, str, str]]]:
    ARXIV_URL = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI+OR+cat:cs.LG",
        "start": 0,
        "max_results": max_results,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
    }
    headers = {"User-Agent": "AIML-Newsletter/1.3 (arXiv polite bot)"}
    cutoff = week_ago()

    try:
        resp = HTTP.get(ARXIV_URL, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        log.warning(f"arXiv fetch failed: {e}")
        return "<li>No recent research found.</li>", []

    ns = {"a": "http://www.w3.org/2005/Atom"}
    lis: List[str] = []
    sources: List[Tuple[str, str, str]] = []

    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        link = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
        updated = (entry.findtext("a:updated", default="", namespaces=ns) or "").strip()
        if not title or not link or not updated:
            continue
        try:
            upd_dt = datetime.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
        except Exception:
            upd_dt = None
        if not upd_dt or upd_dt < cutoff:
            continue
        text = f"{title}: {summary[:220].rstrip()}…" if len(summary) > 240 else f"{title}: {summary}"
        lis.append(li(text, link, "arXiv", fmt_rfc822(upd_dt)))
        sources.append((title, link, "arXiv"))
        if len(lis) >= max_results:
            break

    if not lis:
        return "<li>No recent research found.</li>", sources
    return "\n".join(lis), sources

# -----------------------------------------------------------------------------
# Tiny prompts (LLM only for topic + short paragraphs)
# -----------------------------------------------------------------------------

topic_prompt = PromptTemplate(
    input_variables=["bullets"],
    template=(
        STYLE_GUIDE + "\n\nFrom these weekly AI/ML items, write ONLY a single, specific, captivating topic title (max 12 words, no clickbait, no quotes, no explanations, no labels, no extra text).\n{bullets}"
    ),
)


intro_prompt = PromptTemplate(
    input_variables=["topic", "why"],
    template=(
        STYLE_GUIDE + "\n\nWrite ONLY a punchy, practitioner-focused introduction (2–3 sentences) for the newsletter topic below. Use a concrete tension, question, or surprising stat as a hook. Do not include any labels, explanations, or extra text.\nTOPIC: {topic}\nREASONS: {why}\nNo markdown, no emojis, no links."
    ),
)


summary_prompt = PromptTemplate(
    input_variables=["topic"],
    template=(
        STYLE_GUIDE + "\n\nWrite ONLY 2–4 sentences summarizing what the week means for practitioners for the topic: {topic}. Include actionable takeaways and a 'WHY IT MATTERS' block, but do not include any labels, explanations, or extra text. No markdown, no emojis, no links."
    ),
)

def llm_text(prompt: PromptTemplate, **kwargs) -> str:
    out = llm.invoke(prompt.format(**kwargs))  # type: ignore[arg-type]
    return html.escape(str(out).strip())

# -----------------------------------------------------------------------------
# WordPress publish (accept 200 or 201)
# -----------------------------------------------------------------------------
def publish_to_wordpress(title: str, content: str) -> str:
    if not PUBLISH:
        return f"(dry-run) Would publish: {title}"

    missing = []
    if not WORDPRESS_ACCESS_TOKEN:
        missing.append("WORDPRESS_ACCESS_TOKEN")
    if not WORDPRESS_SITE_ID:
        missing.append("WORDPRESS_SITE_ID")
    if missing:
        raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

    url = f"https://public-api.wordpress.com/rest/v1.1/sites/{WORDPRESS_SITE_ID}/posts/new"
    headers = {
        "Authorization": f"Bearer {WORDPRESS_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"title": title, "content": content, "status": "publish"}

    resp = HTTP.post(url, headers=headers, json=data, timeout=25)
    if resp.status_code in (200, 201):  # WordPress.com may return 200 with JSON body
        try:
            wp_url = resp.json().get("URL", "<no-url>")
        except Exception:
            wp_url = "<no-url>"
        return f"Post published: {wp_url}"
    raise RuntimeError(f"Failed to publish ({resp.status_code}): {resp.text}")

# -----------------------------------------------------------------------------
# Assemble HTML deterministically
# -----------------------------------------------------------------------------
def build_references_html(sources: List[Tuple[str, str, str]]) -> str:
    # sources: list of (title, url, source)
    uniq = []
    seen = set()
    for t,u,s in sources:
        key = (t,u)
        if key in seen: 
            continue
        seen.add(key)
        uniq.append((t,u,s))
    if not uniq:
        return "<li>No references available.</li>"
    lis = [
        f'<li><a href="{html.escape(u, quote=True)}">{html.escape(s)} — {html.escape(t)}</a></li>'
        for (t,u,s) in uniq
    ]
    return "\n".join(lis)

def assemble_article(topic: str, intro_txt: str, news_html: str, papers_html: str, summary_txt: str, refs_html: str) -> str:
    # Ensure lists aren’t empty
    news_block = news_html.strip() or "<li>No recent news found.</li>"
    papers_block = papers_html.strip() or "<li>No recent research found.</li>"

    return f"""
<h2 style='font-size:2em; font-weight:800; margin-bottom:0.2em;'>AI/ML Weekly: {html.escape(topic)}</h2>

<h3 style='font-size:1.3em; font-weight:600; margin-top:0;'>This Week's Big Idea</h3>

<h4>Introduction</h4>
<p>{intro_txt}</p>

<h4>In the News:</h4>
<ul>
{news_block}
</ul>

<h4>Research Breakthroughs:</h4>
<ul>
{papers_block}
</ul>

<h4>Summary &amp; Implications</h4>
<p>{summary_txt}</p>

<h4>References</h4>
<ul>
{refs_html}
</ul>

<p>Stay tuned for further developments and insights in the world of AI!</p>
""".strip()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== AI/ML Weekly — Deterministic Builder ===")
    print(f"MODE: {AGENT_MODE} | PUBLISH: {PUBLISH}")

    # 1) Fetch sources
    news_list_html, news_sources = fetch_news("artificial intelligence machine learning", 6)
    papers_list_html, paper_sources = fetch_arxiv(6)

    # 2) Topic (robust: if LLM fails, fallback)
    bullets = []
    for (t,u,s) in (news_sources + paper_sources)[:6]:
        bullets.append(f"- {t} ({s})")
    bullets_text = "\n".join(bullets) if bullets else "- Weekly highlights and notable updates"
    raw_topic = llm_text(topic_prompt, bullets=bullets_text) or "Key AI/ML Highlights"
    # Clean up topic: remove prompt artifacts and quotes
    def clean_topic(t: str) -> str:
        t = t.strip()
        # Remove common prompt artifacts
        t = re.sub(r"^(Here is a proposed topic title:|Title:|This title.*:)", "", t, flags=re.IGNORECASE)
        t = t.replace('"', '').replace("'", "")
        t = re.sub(r"^[:\s]+", "", t)
        # Remove trailing explanations if present
        t = t.split("\n")[0]
        return t.strip()
    topic = clean_topic(raw_topic) or "Key AI/ML Highlights"

    # 3) Intro & Summary (short text only)
    why_fragments = ", ".join([t for (t,_,_) in (news_sources + paper_sources)[:3]]) or "notable updates across AI applications and research"
    intro_txt = llm_text(intro_prompt, topic=topic, why=why_fragments) or html.escape("A quick tour of the most useful AI/ML developments this week.")
    summary_txt = llm_text(summary_prompt, topic=topic) or html.escape("Expect continued iteration across models, tooling, and applied ML in production.")

    # 4) References
    refs_html = build_references_html(news_sources + paper_sources)

    # 5) Assemble
    article_html = assemble_article(topic, intro_txt, news_list_html, papers_list_html, summary_txt, refs_html)

    # Absolute safety: don’t publish if suspiciously short
    if len(article_html) < 300 or "<ul>" not in article_html:
        print("ERROR: Article too short or malformed; aborting publish.")
        print(article_html)
        raise SystemExit(1)

    # 6) Publish
    # Make the WordPress post title captivating and relevant to the week's topic
    title = f"AI/ML Weekly: {topic}"
    result = publish_to_wordpress(title, article_html)
    print(result)
