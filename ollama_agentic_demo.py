
import requests

# Ollama and model config
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"  # Use 'phi3' for Phi-3 Mini, or change to 'gemma:2b', 'mistral:7b', etc.

# Serpstack config
SERPSTACK_API_KEY = "YOUR_ACTUAL_SERPSTACK_API_KEY"  # <-- Replace with your actual Serpstack API key
SERPSTACK_URL = "http://api.serpstack.com/search"

def serpstack_search(query):
    params = {
        "access_key": SERPSTACK_API_KEY,
        "query": query,
        "num": 5  # Limit to top 5 results for brevity
    }
    response = requests.get(SERPSTACK_URL, params=params)
    data = response.json()
    results = []
    if "organic_results" in data:
        for item in data["organic_results"]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}")
    return "\n\n".join(results)

def run_agentic_flow(task):
    # Step 1: Search the web for the task
    print(f"Searching the web for: {task}\n")
    web_results = serpstack_search(task)
    print("Top Search Results:\n", web_results)

    # Step 2: Summarize results with Phi-3 Mini
    prompt = f"Summarize and extract the most useful information for coding from these search results:\n{web_results}"
    response = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
    result = response.json()
    summary = result["response"]
    print("\nSummary from Phi-3 Mini:\n", summary)

if __name__ == "__main__":
    print("=== Coding Agent with Serpstack + Phi-3 Mini ===\n")
    print("Type your coding question (or press Enter for the default):")
    user_query = input().strip()
    if not user_query:
        user_query = "Latest Python async HTTP libraries and usage examples."
    run_agentic_flow(user_query)

if __name__ == "__main__":
    # Example task
    task = "Summarize the main points of the latest AI research and create a to-do list for learning."
    run_agentic_flow(task)
