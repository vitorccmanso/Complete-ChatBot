import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def perform_tavily_search(query, search_type="web", max_results=5):
    """
    Perform a web search using Tavily API.
    
    Args:
        query: The search query
        search_type: "web" (default), "academic", or "social"
        max_results: Number of results to return
        
    Returns:
        List of search results with title, url, and content
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    
    # API endpoint
    url = "https://api.tavily.com/search"
    
    # Configure search parameters based on search_type
    params = {
        "api_key": tavily_api_key,
        "query": query,
        "max_results": max_results
    }
    
    # Adjust search parameters based on search type
    if search_type == "academic":
        params["search_depth"] = "advanced"  # More comprehensive search
        # Add academic domains to include
        params["include_domains"] = [
            "scholar.google.com", "arxiv.org", "researchgate.net", 
            "sciencedirect.com", "ieee.org", "ncbi.nlm.nih.gov",
            "academia.edu", "ssrn.com", "nature.com", "science.org"
        ]
    elif search_type == "social":
        # Focus on social media and discussion sites
        params["include_domains"] = [
            "twitter.com", "reddit.com", "linkedin.com", 
            "quora.com", "medium.com", "substack.com",
            "discord.com", "facebook.com", "instagram.com"
        ]
    elif search_type == "web":
        # Standard web search with no specific domain focus
        pass
    else:
        print(f"Warning: Unknown search type '{search_type}', using default web search")
    
    # Remove empty arrays to avoid API issues
    if "include_domains" in params and not params["include_domains"]:
        del params["include_domains"]
    if "exclude_domains" in params and not params["exclude_domains"]:
        del params["exclude_domains"]
    
    # Ensure query is not too long (Tavily has a 400 char limit)
    if len(query) > 390:
        query = query[:390] + "..."
        params["query"] = query
    
    # Print request details for debugging
    print(f"Tavily API request for {search_type} search:")
    print(f"- Query length: {len(query)} characters")
    print(f"- Search type: {search_type}")
    print(f"- Max results: {max_results}")
    
    # Execute search
    try:
        response = requests.post(url, json=params)
        
        # Debug response information
        print(f"Tavily API status code: {response.status_code}")
        if response.status_code != 200:
            print(f"Tavily API error response: {response.text}")
        
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        data = response.json()
        
        # Format results for consistency
        results = []
        for result in data.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", "")
            })
        
        print(f"Tavily {search_type} search returned {len(results)} results")
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
