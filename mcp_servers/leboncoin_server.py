#!/usr/bin/env python
"""MCP server exposing Leboncoin search tools."""

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from scripts.piloterr_leboncoin_search import PiloterrLeboncoinSearch
from scripts.travel_time import get_distance_time, reverse_geocode

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("leboncoin-server")


@mcp.tool()
def search_leboncoin_properties(
    location: str, workplace: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
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
        key = api_key or os.environ.get("PILOTERR_API_KEY")
        if not key:
            return {
                "location": location,
                "error": "API key is required. Set PILOTERR_API_KEY environment variable or provide api_key parameter.",
                "status": "error",
            }

        # Initialize searcher
        searcher = PiloterrLeboncoinSearch(key)

        # Perform search
        raw_results = searcher.search(location)
        if not raw_results:
            return {
                "location": location,
                "error": "No results found or API error occurred",
                "status": "error",
            }

        # Format results
        formatted_results = searcher.format_results(raw_results)

        # Limit to first 20 properties and add travel times
        properties = formatted_results.get("properties", [])[:20]

        # Add travel time calculations and street address for each property
        for prop in properties:
            try:
                lat = prop.get("latitude")
                lng = prop.get("longitude")

                if lat != "N/A" and lng != "N/A":
                    # Calculate travel time using coordinates
                    travel_info = get_distance_time(
                        origin_latlng=(float(lat), float(lng)),
                        destination_address=workplace,
                        mode="transit",
                    )

                    prop["travel_to_work"] = {
                        "distance_km": round(travel_info["distance_m"] / 1000.0, 1),
                        "duration_min": travel_info["duration_min"],
                        "mode": "transit",
                        "workplace": workplace,
                    }

                    # Get street address using reverse geocoding
                    try:
                        full_address = reverse_geocode(float(lat), float(lng))
                        # Extract just the street part (first part before the first comma)
                        street_part = full_address.split(",")[0].strip()

                        # Clean up the street: remove building numbers and extra details
                        # Remove patterns like "53", "2a", "34B", etc. at the beginning
                        cleaned_street = re.sub(r"^\d+[a-zA-Z]?\s*", "", street_part)
                        # Remove extra details like "2nd floor", "1st floor", etc.
                        cleaned_street = re.sub(
                            r"\s+\d+(st|nd|rd|th)\s+floor.*$",
                            "",
                            cleaned_street,
                            flags=re.IGNORECASE,
                        )

                        prop["street"] = cleaned_street.strip()
                    except Exception as e:
                        prop["street"] = f"Address lookup failed: {str(e)}"

                else:
                    prop["travel_to_work"] = {
                        "error": "No coordinates available for travel calculation"
                    }
                    prop["street"] = "No coordinates available for address lookup"
            except Exception as e:
                prop["travel_to_work"] = {
                    "error": f"Travel calculation failed: {str(e)}"
                }
                prop["street"] = f"Address processing failed: {str(e)}"

            # Remove latitude and longitude from results
            prop.pop("latitude", None)
            prop.pop("longitude", None)

        return {
            "location": location,
            "workplace": workplace,
            "search_summary": formatted_results.get("search_summary", {}),
            "properties": properties,
            "returned_count": len(properties),
            "status": "success",
        }

    except Exception as e:
        return {"location": location, "error": str(e), "status": "error"}


@mcp.tool()
def search_and_save_leboncoin_properties(
    location: str, workplace: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search Leboncoin properties and save results to files in results/ folder.
    Uses the same enhanced processing as search_leboncoin_properties.

    Args:
        location: The location name to search for properties
        workplace: Workplace address for travel time calculation (required)
        api_key: Optional Piloterr API key (uses environment variable if not provided)

    Returns:
        Dictionary with search summary and file save information
    """
    try:
        # Get the enhanced results using the main search function
        search_result = search_leboncoin_properties(location, workplace, api_key)

        if search_result.get("status") != "success":
            return search_result

        # Use provided API key or get from environment for raw data saving
        key = api_key or os.environ.get("PILOTERR_API_KEY")
        searcher = PiloterrLeboncoinSearch(key)

        # Get raw results for saving
        raw_results = searcher.search(location)

        # Save raw results
        searcher.save_results(
            raw_results, f"raw_leboncoin_{location.replace(' ', '_')}.json"
        )

        # Save enhanced results (with streets and travel times)
        enhanced_results = {
            "search_summary": search_result.get("search_summary", {}),
            "properties": search_result.get("properties", []),
        }
        searcher.save_results(
            enhanced_results, f"formatted_leboncoin_{location.replace(' ', '_')}.json"
        )

        return {
            "location": location,
            "workplace": workplace,
            "search_summary": search_result.get("search_summary", {}),
            "files_saved": [
                f"results/raw_leboncoin_{location.replace(' ', '_')}.json",
                f"results/formatted_leboncoin_{location.replace(' ', '_')}.json",
            ],
            "property_count": len(search_result.get("properties", [])),
            "status": "success",
        }

    except Exception as e:
        return {"location": location, "error": str(e), "status": "error"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
