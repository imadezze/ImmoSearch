#!/usr/bin/env python
"""Direct test of MCP tools without client."""

import sys
from pathlib import Path

# Add parent directory to path to access mcp_servers
sys.path.append(str(Path(__file__).parent.parent))

from mcp_servers.leboncoin_server import (
    search_and_save_leboncoin_properties,
    search_leboncoin_properties,
)


def test_search():
    """Test the MCP search tools directly."""
    print("🔍 Testing MCP Leboncoin search tools...\n")

    location = "le bourget"
    workplace = "Gare du Nord, Paris"
    print(f"Searching properties in: {location}")
    print(f"Workplace for travel calculations: {workplace}")

    # Test RENTAL properties first
    print("\n🏠 Testing RENTAL properties...")
    print("=" * 40)
    result = search_leboncoin_properties(location, workplace)

    print(f"\n📊 Results:")
    print(f"Status: {result.get('status')}")

    if result.get("status") == "success":
        summary = result.get("search_summary", {})
        print(f"Total results: {summary.get('total_results', 0)}")
        print(f"Returned: {result.get('returned_count', 0)} properties")
        print(f"Workplace: {result.get('workplace', 'N/A')}")

        print(f"\n🏠 Sample properties:")
        for i, prop in enumerate(result.get("properties", [])[:3], 1):
            print(f"\n--- Property {i} ---")
            print(f"Title: {prop.get('title', 'N/A')}")
            print(f"Price: {prop.get('price', 'N/A')}")
            print(f"Location: {prop.get('location', 'N/A')}")
            print(f"Zipcode: {prop.get('zipcode', 'N/A')}")
            print(f"Street: {prop.get('street', 'N/A')}")  # New street field

            # Travel time information
            travel_info = prop.get("travel_to_work", {})
            if "error" not in travel_info:
                print(
                    f"Travel to work: {travel_info.get('duration_min', 'N/A')} min ({travel_info.get('distance_km', 'N/A')} km)"
                )
            else:
                print(f"Travel info error: {travel_info.get('error', 'N/A')}")

            attrs = prop.get("key_attributes", {})
            if attrs:
                print(f"Attributes: {attrs}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")

    # Test SALES properties
    print("\n\n💰 Testing SALES properties...")
    print("=" * 40)
    sales_result = search_leboncoin_properties(location, workplace, property_type="sale")

    print(f"\n📊 Sales Results:")
    print(f"Status: {sales_result.get('status')}")
    print(f"Property Type: {sales_result.get('property_type', 'N/A')}")

    if sales_result.get("status") == "success":
        summary = sales_result.get("search_summary", {})
        print(f"Total results: {summary.get('total_results', 0)}")
        print(f"Returned: {sales_result.get('returned_count', 0)} properties")

        print(f"\n🏠 Sample sale properties:")
        for i, prop in enumerate(sales_result.get("properties", [])[:3], 1):
            print(f"\n--- Sale Property {i} ---")
            print(f"Title: {prop.get('title', 'N/A')}")
            print(f"Price: {prop.get('price', 'N/A')}")
            print(f"Location: {prop.get('location', 'N/A')}")
            print(f"Street: {prop.get('street', 'N/A')}")

            # Travel time information
            travel_info = prop.get("travel_to_work", {})
            if "error" not in travel_info:
                print(
                    f"Travel to work: {travel_info.get('duration_min', 'N/A')} min ({travel_info.get('distance_km', 'N/A')} km)"
                )
            else:
                print(f"Travel info error: {travel_info.get('error', 'N/A')}")

            attrs = prop.get("key_attributes", {})
            if attrs:
                print(f"Attributes: {attrs}")
    else:
        print(f"❌ Sales Error: {sales_result.get('error', 'Unknown error')}")

    # Test save tool with same parameters (rental by default)
    print(f"\n💾 Testing save functionality...")
    save_result = search_and_save_leboncoin_properties(location, workplace)

    if save_result.get("status") == "success":
        files = save_result.get("files_saved", [])
        print(f"✅ Files saved: {', '.join(files)}")
        print(
            f"Saved {save_result.get('property_count', 0)} properties with enhanced data"
        )
    else:
        print(f"❌ Save error: {save_result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_search()
