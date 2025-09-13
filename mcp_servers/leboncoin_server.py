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
from scripts.leboncoin_url_generator import get_real_estate_url
from scripts.piloterr_leboncoin_search import PiloterrLeboncoinSearch
from scripts.travel_time import get_distance_time

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("leboncoin-server")


@mcp.tool()
def search_leboncoin_properties(location: str, workplace: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Search Leboncoin for properties in a specific location using Piloterr API with travel time to workplace.
    
    Args:
        location: The location name to search for properties
        workplace: Workplace address for travel time calculation (required)
        api_key: Optional Piloterr API key (uses environment variable if not provided)
    
    Returns:
        Dictionary with search results and property information including travel times
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
        
        # Limit to first 20 properties and add travel times
        properties = formatted_results.get("properties", [])[:20]
        
        # Add travel time calculations for each property
        for prop in properties:
            try:
                lat = prop.get('latitude')
                lng = prop.get('longitude')
                
                if lat != 'N/A' and lng != 'N/A':
                    # Calculate travel time using coordinates
                    travel_info = get_distance_time(
                        origin_latlng=(float(lat), float(lng)),
                        destination_address=workplace,
                        mode="transit"
                    )
                    
                    prop['travel_to_work'] = {
                        "distance_km": round(travel_info['distance_m'] / 1000.0, 1),
                        "duration_min": travel_info['duration_min'],
                        "mode": "transit",
                        "workplace": workplace
                    }
                else:
                    prop['travel_to_work'] = {
                        "error": "No coordinates available for travel calculation"
                    }
            except Exception as e:
                prop['travel_to_work'] = {
                    "error": f"Travel calculation failed: {str(e)}"
                }
            
            # Remove latitude and longitude from results
            prop.pop('latitude', None)
            prop.pop('longitude', None)
        
        return {
            "location": location,
            "workplace": workplace,
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