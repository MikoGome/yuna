import json
from ddgs import DDGS
from scrapling.fetchers import StealthyFetcher

def web_search(query: str) -> str:
    """
    Searches the web using DuckDuckGo to get a list of relevant links and snippets.
    
    Args:
        query: The search query to look up.
        
    Returns:
        A JSON string containing the title, snippet, and URL of the top 5 results.
    """
    try:
        results = DDGS().text(query, max_results=5)
        formatted = [
            {
                "title": r.get("title"), 
                "snippet": r.get("body"), 
                "url": r.get("href")
            } 
            for r in results
        ]
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})


def web_fetch(url: str) -> str:
    """
    Fetches the clean text content of a webpage under the radar.
    Use this to read articles, documentation, or site text.
    Handles anti-bot protections like Cloudflare Turnstile automatically.
    
    Args:
        url: The exact URL of the webpage to fetch.
        
    Returns:
        A clean text representation of the webpage, truncated to respect LLM context limits.
    """
    try:
        # solve_cloudflare=True auto-clicks/verifies Turnstile challenges
        # timeout is set to 60s as recommended for solving complex JS challenges
        page = StealthyFetcher.fetch(
            url, 
            headless=True, 
            network_idle=True, 
            solve_cloudflare=True, 
            timeout=60000
        )
        
        # Extracts text while ignoring non-readable clutter (scripts, styles, layouts)
        clean_text = page.get_all_text(
            ignore_tags=('script', 'style', 'nav', 'footer', 'header', 'noscript')
        )
        
        # Truncate content to roughly ~1,500 words to respect model context window
        return clean_text[:6000]
        
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch page using Scrapling: {str(e)}"})
    

web_tools_meta = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the web using DuckDuckGo to get a list of relevant links and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetches the raw text content of a specific webpage URL under the radar. Use this to read articles, documentation, or site text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The exact URL of the webpage to fetch."
                    }
                },
                "required": ["url"]
            }
        }
    }
]

if __name__ == "__main__":
    print(web_fetch("https://rezero.fandom.com/wiki/Emilia"))