#!/usr/bin/env python3
"""
Test script for Google Maps MCP server
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the google_maps_mcp src to path
sys.path.insert(0, str(Path(__file__).parent / "google_maps_mcp" / "src"))

from google_maps_mcp.mcp_server import find_places_nearby


async def test_paris_search():
    """Test searching for places in Paris"""
    print("🗺️ Testing Google Maps MCP Server - Paris Search")
    print("=" * 50)

    try:
        # Test different place types in Paris
        search_configs = [
            {"location": "Paris", "place_type": "restaurant", "sort_by": "rating"},
            {
                "location": "Paris",
                "place_type": "tourist_attraction",
                "sort_by": "rating",
            },
            {"location": "Paris", "place_type": "cafe", "sort_by": "rating"},
        ]

        for config in search_configs:
            print(
                f"\n🔍 Searching for {config['place_type']} in {config['location']} (sorted by {config['sort_by']})"
            )
            print("-" * 30)

            results = find_places_nearby(**config)

            if results:
                print(f"✅ Found {len(results)} places:")
                for i, place in enumerate(results[:5], 1):  # Show top 5 results
                    print(f"{i}. {place.get('name', 'N/A')}")
                    print(f"   Rating: {place.get('rating', 'N/A')} ⭐")
                    print(f"   Reviews: {place.get('user_ratings_total', 'N/A')}")
                    print(f"   Address: {place.get('vicinity', 'N/A')}")
                    print()
            else:
                print("❌ No results found")

    except Exception as e:
        print(f"❌ Error during search: {e}")
        print("Make sure GOOGLE_MAPS_API_KEY is set in your environment")


if __name__ == "__main__":
    # Set the API key from environment or the one provided
    api_key = os.getenv(
        "GOOGLE_MAPS_API_KEY", "AIzaSyAC5y-YNySqI4RuLjre3xSiGffQS2O9FQc"
    )
    os.environ["GOOGLE_MAPS_API_KEY"] = api_key

    print(f"🔑 Using API key: {api_key[:10]}...")
    asyncio.run(test_paris_search())
