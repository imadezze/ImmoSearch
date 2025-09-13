#!/usr/bin/env python
"""MCP server exposing Leboncoin search tools."""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from scripts.leboncoin_url_generator import generate_leboncoin_url
from scripts.piloterr_leboncoin_search import PiloterrLeboncoinSearch

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("leboncoin-server")

@mcp.tool()
def generate_leboncoin_url(location: str, real_estate_type: int = 2) -> Dict[str, str]:
    """
    Generate a Leboncoin URL for a given location and real estate type.
    
    Args:
        location: The location name (e.g., "le bourget", "paris lyon")
        real_estate_type: Real estate type code (default: 2 for real estate sales)
    
    Returns:
        Dictionary with location and generated URL
    """
    try:
        url = generate_leboncoin_url(location, real_estate_type)
        return {
            "location": location,
            "real_estate_type": str(real_estate_type),
            "url": url,
            "status": "success"
        }
    except Exception as e:
        return {
            "location": location,
            "error": str(e),
            "status": "error"
        }

@mcp.tool()
def search_leboncoin_properties(location: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Search Leboncoin for properties in a specific location using Piloterr API.
    
    Args:
        location: The location name to search for properties
        api_key: Optional Piloterr API key (uses environment variable if not provided)
    
    Returns:
        Dictionary with search results and property information
    """
    try:
        # Use provided API key or get from environment
        key = api_key or os.environ.get('PILOTERR_API_KEY')
        if not key:
            return {
                "location": location,
                "error": "API key is required. Set PILOTERR_API_KEY environment variable or provide api_key parameter.",
                "status": "error"
            }
        
        # Initialize searcher
        searcher = PiloterrLeboncoinSearch(key)
        
        # Perform search
        raw_results = searcher.search(location)
        if not raw_results:
            return {
                "location": location,
                "error": "No results found or API error occurred",
                "status": "error"
            }
        
        # Format results
        formatted_results = searcher.format_results(raw_results)
        
        # Limit to first 20 properties
        properties = formatted_results.get("properties", [])[:20]
        
        return {
            "location": location,
            "search_summary": formatted_results.get("search_summary", {}),
            "properties": properties,
            "returned_count": len(properties),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "location": location,
            "error": str(e),
            "status": "error"
        }

@mcp.tool()
def search_and_save_leboncoin_properties(location: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Search Leboncoin properties and save results to files in results/ folder.
    
    Args:
        location: The location name to search for properties
        api_key: Optional Piloterr API key (uses environment variable if not provided)
    
    Returns:
        Dictionary with search summary and file save information
    """
    try:
        # Use provided API key or get from environment
        key = api_key or os.environ.get('PILOTERR_API_KEY')
        if not key:
            return {
                "location": location,
                "error": "API key is required. Set PILOTERR_API_KEY environment variable or provide api_key parameter.",
                "status": "error"
            }
        
        # Initialize searcher
        searcher = PiloterrLeboncoinSearch(key)
        
        # Perform search
        raw_results = searcher.search(location)
        if not raw_results:
            return {
                "location": location,
                "error": "No results found or API error occurred",
                "status": "error"
            }
        
        # Format results
        formatted_results = searcher.format_results(raw_results)
        
        # Save results
        searcher.save_results(raw_results, f"raw_leboncoin_{location.replace(' ', '_')}.json")
        searcher.save_results(formatted_results, f"formatted_leboncoin_{location.replace(' ', '_')}.json")
        
        return {
            "location": location,
            "search_summary": formatted_results.get("search_summary", {}),
            "files_saved": [
                f"results/raw_leboncoin_{location.replace(' ', '_')}.json",
                f"results/formatted_leboncoin_{location.replace(' ', '_')}.json"
            ],
            "property_count": len(formatted_results.get("properties", [])),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "location": location,
            "error": str(e),
            "status": "error"
        }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")