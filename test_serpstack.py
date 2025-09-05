import os
import requests
from dotenv import load_dotenv

load_dotenv()
SERPSTACK_API_KEY = os.getenv("SERPSTACK_API_KEY")

def test_serpstack(query="artificial intelligence machine learning", num=5):
    params = {
        "access_key": SERPSTACK_API_KEY,
        "query": query,
        "type": "news",
        "num": num
    }
    response = requests.get("http://api.serpstack.com/search", params=params)
    print("Raw Serpstack response:")
    print(response.text)
    data = response.json()
    print("Parsed news results:")
    print(data.get("news_results", []))

if __name__ == "__main__":
    test_serpstack()
