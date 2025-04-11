import os
import requests
import json
from dotenv import load_dotenv
from langchain.tools import Tool # Import the Tool class

load_dotenv()

def perform_tavily_search(query, search_type="web", max_results=5):
    """
    Perform a web search using Tavily API. Handles 'web', 'academic', and 'social' types.
    Returns list of search results or raises an error.
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        # Consider logging this error instead of raising, returning [] might be safer for agent
        print("Error: TAVILY_API_KEY not found in environment variables")
        return [] # Return empty list on error

    url = "https://api.tavily.com/search"
    params = {
        "api_key": tavily_api_key,
        "query": query,
        "max_results": max_results
    }

    # Adjust search parameters based on search type
    if search_type == "academic":
        params["search_depth"] = "advanced"
        params["include_domains"] = [
            "scholar.google.com", "arxiv.org", "researchgate.net",
            "sciencedirect.com", "ieee.org", "ncbi.nlm.nih.gov",
            "academia.edu", "ssrn.com", "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov"
        ]
    elif search_type == "social":
        params["include_domains"] = [
            "twitter.com", "reddit.com", "linkedin.com",
            "quora.com", "medium.com", "substack.com", "news.ycombinator.com",
            "discord.com", "facebook.com", "instagram.com"
        ]
    elif search_type == "web":
        # Standard web search, maybe exclude academic/social to avoid overlap if desired?
        # params["exclude_domains"] = ["scholar.google.com", "arxiv.org", "reddit.com", "twitter.com"] # Example
        pass # Keep as default for now
    else:
        print(f"Warning: Unknown search type '{search_type}', using default web search settings")
        # Default to web search settings

    # Remove empty arrays to avoid API issues
    if "include_domains" in params and not params["include_domains"]:
        del params["include_domains"]
    if "exclude_domains" in params and not params["exclude_domains"]:
        del params["exclude_domains"]

    # Ensure query is not too long
    if len(query) > 400:
        print(f"Warning: Query truncated to 390 characters for Tavily API.")
        query = query[:399]
        params["query"] = query

    try:
        response = requests.post(url, json=params)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""), # Agent will use this content
            })
        print(f"Tavily '{search_type}' search returned {len(results)} results.")

        return results
    except requests.exceptions.RequestException as e:
        print(f"Error during Tavily API request for {search_type} search: {str(e)}")
        error_details = str(e)
        if hasattr(e, 'response') and e.response:
            try:
                error_details += f"\nResponse: {e.response.text}"
            except:
                pass
        print(f"Detailed error: {error_details}")
        return []


# --- Create LangChain Tools ---

# Tool for Standard Web Search
web_search_tool = Tool(
    name="web",
    func=lambda q: perform_tavily_search(q, search_type="web", max_results=10),
    description="Performs a standard web search using the Tavily Search API. Use this for general questions, current events, or information not likely found in academic papers or social media discussions.",
    # return_direct=False # Agent should process the results
)

# Tool for Academic Search
academic_search_tool = Tool(
    name="academic",
    func=lambda q: perform_tavily_search(q, search_type="academic", max_results=10),
    description="Performs an academic search using the Tavily Search API, focusing on sites like Google Scholar, arXiv, PubMed, etc. Use this for finding research papers, scientific articles, or technical information.",
    # return_direct=False
)

# Tool for Social/Discussion Search
social_search_tool = Tool(
    name="social", # Renamed slightly for clarity
    func=lambda q: perform_tavily_search(q, search_type="social", max_results=10),
    description="Performs a search focused on social media and discussion platforms like Twitter, Reddit, Hacker News, etc., using the Tavily Search API. Use this to find opinions, discussions, or recent informal posts about a topic.",
    # return_direct=False
)

# Dictionary to easily map search type strings to the corresponding tool
SEARCH_TOOL_MAP = {
    "web": web_search_tool,
    "academic": academic_search_tool,
    "social": social_search_tool,
}
