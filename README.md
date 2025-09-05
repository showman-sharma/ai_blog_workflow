
# Agentic AI/ML Newsletter Generator

Automate the creation and publishing of a weekly AI/ML newsletter using real news headlines and research papers. The workflow fetches news, summarizes, formats in clean HTML, and publishes to WordPress with professional structure and references.

## Features
- Fetches real AI/ML news headlines (Serpstack, Google News RSS)
- Fetches recent AI/ML research papers (arXiv)
- Summarizes and analyzes news/research using LLMs (Cohere, Ollama)
- Formats newsletter in clean, professional HTML
- Publishes automatically to WordPress
- References section with clickable sources
- Smart, engaging blog post titles

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
	python agentic_newsletter_langchain.py
	```

## Configuration
- Edit `.env` for API keys and WordPress settings
- Customize prompts and formatting in `agentic_newsletter_langchain.py`

## Security
- Never commit your real `.env` file or secrets to version control.
- All sensitive credentials are loaded from environment variables.

## License
MIT
