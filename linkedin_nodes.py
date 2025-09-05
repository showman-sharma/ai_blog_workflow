from langchain_core.messages import SystemMessage, HumanMessage
from style_guide import STYLE_GUIDE

def title_hook_node(state, llm):
    sys = SystemMessage(content=STYLE_GUIDE)
    hum = HumanMessage(content=f"""
Generate 5 title options and 3 hook options for a LinkedIn article based ONLY on these items (news + papers).
Return JSON: {{"titles":[str], "hooks":[str]}}.
Items:
{[it.model_dump() for it in state.news + state.papers]}
""")
    out = llm.invoke([sys, hum])
    import json
    try:
        data = json.loads(str(out))
    except Exception:
        data = {"titles": [], "hooks": []}
    titles = data.get("titles", [])
    hooks = data.get("hooks", [])
    chosen_title = sorted(titles, key=len)[:1] or titles[:1]
    chosen_hook = sorted(hooks, key=lambda s: (-any(c.isdigit() for c in s), -len(s)))[:1] or hooks[:1]
    meta = dict(state.meta)
    meta["title_candidates"] = titles
    meta["hook_candidates"] = hooks
    meta["title"] = chosen_title[0] if chosen_title else "AI/ML Weekly Highlights"
    meta["hook"] = chosen_hook[0] if chosen_hook else ""
    return state.copy(update={"meta": meta})

def linkedin_writer_node(state, llm):
    sys = SystemMessage(content=STYLE_GUIDE)
    news_json = [it.model_dump() for it in state.news]
    pap_json = [it.model_dump() for it in state.papers]
    topic = state.themes[0] if state.themes else state.meta.get("title","AI/ML Weekly")
    hum = HumanMessage(content=f"""
Write a LinkedIn-native article in plain text. Use my title and hook, then 2–4 sections with subheads, short paragraphs, bullets, 'WHY IT MATTERS' block, and a subtle CTA.
Use ONLY these sources; attribute claims to their source ids or outlets.
Return ONLY the article text (no JSON).

TITLE: {state.meta.get("title")}
HOOK: {state.meta.get("hook")}
TOPIC: {topic}
NEWS_ITEMS: {news_json}
PAPER_ITEMS: {pap_json}

Also produce AFTER the article a '---\nCAROUSEL' section with slide-by-slide lines (Slide 1..N) max ~20 words each.
""")
    text = str(llm.invoke([sys, hum]))
    return state.copy(update={"draft_html": text})

def engagement_judge_node(state, llm):
    sys = SystemMessage(content="""
You are an editor judging LinkedIn post quality.
Score on: hook strength (0–1), clarity (0–1), scannability (0–1), evidence (0–1), jargon (0–1 where higher is worse), CTA quality (0–1).
Return JSON: {"pass": bool, "scores": {...}, "issues": [str], "edits":[str]}
Fail if: hook<0.5 or evidence<0.6 or scannability<0.6 or jargon>0.6.
""")
    hum = HumanMessage(content=f"TEXT:\n{state.draft_html}\n\nSources:\n{[it.model_dump() for it in state.news+state.papers]}")
    out = llm.invoke([sys, hum])
    import json
    try:
        verdict = json.loads(str(out))
    except Exception:
        verdict = {"pass": False, "scores": {}, "issues": ["parse_error"], "edits": []}
    return state.copy(update={"verification": verdict})

def linkedin_fix_node(state, llm):
    sys = SystemMessage(content=STYLE_GUIDE)
    hum = HumanMessage(content=f"""
Improve the article STRICTLY following these issues & edits. Keep facts tied to supplied sources. Keep tone and constraints.
ISSUES: {state.verification.get("issues", [])}
EDITS: {state.verification.get("edits", [])}
ARTICLE:
{state.draft_html}
""")
    text2 = str(llm.invoke([sys, hum]))
    return state.copy(update={"draft_html": text2})

def hashtag_node(state, llm):
    sys = SystemMessage(content=STYLE_GUIDE)
    hum = HumanMessage(content=f"""
Propose 6–10 hashtags for this article. Follow the Style Guide rules. Return comma-separated, no '# ' spaces.
ARTICLE (excerpt): {state.draft_html[:1200]}
TOPIC: {state.themes[:2]}
""")
    tags = str(llm.invoke([sys, hum]))
    meta = dict(state.meta); meta["hashtags"] = [t.strip() for t in tags.replace("#"," #").split() if t.startswith("#")][:10]
    return state.copy(update={"meta": meta})

def export_linkedin_package(state, path="linkedin_post.txt"):
    tags = " ".join(state.meta.get("hashtags", []))
    with open(path, "w", encoding="utf-8") as f:
        f.write(state.meta.get("title","") + "\n\n")
        f.write(state.draft_html.strip() + "\n\n")
        f.write(tags + "\n")
    return path
