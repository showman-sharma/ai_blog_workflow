
# Agentic AI/ML Newsletter Generator

Automated, agentic workflow for publishing a weekly AI/ML newsletter with engaging, practitioner-focused content. Fetches real news and research, summarizes with LLMs, formats in HTML, and publishes to WordPress. Prompts are tuned for clean output—no extra labels, explanations, or artifacts.

Automate the creation and publishing of a weekly AI/ML newsletter using real news headlines and research papers. The workflow fetches news, summarizes, formats in clean HTML, and publishes to WordPress with professional structure and references.

## Features
- Fetches real AI/ML news headlines (Serpstack, Google News RSS)
- Fetches recent AI/ML research papers (arXiv)
- Summarizes and analyzes news/research using LLMs (Cohere, Ollama)
- Prompts tuned for direct, artifact-free output (no extra labels or explanations)
- Formats newsletter in clean, professional HTML
- Publishes automatically to WordPress
- References section with clickable sources
- Smart, captivating blog post titles

## Setup
1. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
2. Copy `.env.example` to `.env` and fill in your API keys and WordPress credentials.
3. (Optional) To generate a WordPress access token, use:
	```bash
	python get_wordpress_token.py
	```
	Follow the instructions to authorize and update your `.env`.
4. Run the newsletter generator:
	```bash
	python agentic_newsletter_generator.py
	```
5. (Optional) For LinkedIn-style output, use the style guide in `style_guide.py` and nodes in `linkedin_nodes.py` to generate carousel scripts or LinkedIn-native articles (not included in WordPress posts).

## Configuration
- Edit `.env` for API keys and WordPress settings
- Customize prompts and formatting in `agentic_newsletter_generator.py`, `style_guide.py`, and `linkedin_nodes.py`
- Prompts are tuned for direct output—no extra labels, explanations, or artifacts in published posts.

## Security
- Never commit your real `.env` file or secrets to version control.
- All sensitive credentials are loaded from environment variables.

## Requirements
See `requirements.txt` for Python dependencies. Make sure to install all listed packages for full functionality.

## LinkedIn Nodes: Generating LinkedIn-Native Content

You can use the optional `linkedin_nodes.py` to generate LinkedIn-native articles and carousel scripts from your weekly news and research sources. This is useful for manual posting or cross-posting to LinkedIn, and is not included in WordPress posts.

### How to Use

1. **Import and Setup:**
	```python
	from linkedin_nodes import title_hook_node, linkedin_writer_node
	from style_guide import STYLE_GUIDE
	# Set up your LLM (Cohere/Ollama) as in your main workflow
	```

2. **Prepare State:**
	Create a `state` dictionary with your news and papers (as lists of objects or dicts):
	```python
	state = {
		"news": [...],  # list of news items
		"papers": [...],  # list of research items
		"meta": {},
		"themes": []
	}
	```

3. **Generate LinkedIn Content:**
	```python
	state = title_hook_node(state, llm)
	state = linkedin_writer_node(state, llm)
	print(state["meta"]["title"])    # LinkedIn title
	print(state["meta"]["hook"])     # LinkedIn hook
	print(state["meta"]["article"])  # LinkedIn article text
	```

4. **Manual Posting:**
	Copy the generated title, hook, and article text to LinkedIn. Optionally, use the carousel script for LinkedIn slides.

**Note:** The nodes expect your news and papers in a specific format (see `model_dump()` usage in the code). You may need to adapt your data structures to match what the nodes expect.

## License
MIT
