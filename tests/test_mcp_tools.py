#!/usr/bin/env python
"""Direct test of MCP tools without client."""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to access mcp_servers
sys.path.append(str(Path(__file__).parent.parent))

from mcp_servers.immosearch_server import search_leboncoin_properties
from initial_servers.leboncoin_server import search_and_save_leboncoin_properties


def test_rental_search(location, workplace):
    """Test rental property search."""
    print("🏠 Testing RENTAL properties...")
    print("=" * 40)
    result = search_leboncoin_properties(location, workplace, property_type="rental")

    print(f"\n📊 Rental Results:")
    print(f"Status: {result.get('status')}")
    print(f"Property Type: {result.get('property_type', 'N/A')}")

    if result.get("status") == "success":
        summary = result.get("search_summary", {})
        print(f"Total results: {summary.get('total_results', 0)}")
        print(f"Returned: {result.get('returned_count', 0)} properties")

        print(f"\n🏠 Sample rental properties:")
        for i, prop in enumerate(result.get("properties", [])[:3], 1):
            print(f"\n--- Rental Property {i} ---")
            print(f"Title: {prop.get('title', 'N/A')}")
            print(f"Price: {prop.get('price', 'N/A')}")
            print(f"Location: {prop.get('location', 'N/A')}")
            print(f"Street: {prop.get('street', 'N/A')}")

            travel_info = prop.get("travel_to_work", {})
            if "error" not in travel_info:
                print(f"Travel to work: {travel_info.get('duration_min', 'N/A')} min ({travel_info.get('distance_km', 'N/A')} km)")
            else:
                print(f"Travel info error: {travel_info.get('error', 'N/A')}")

            attrs = prop.get("key_attributes", {})
            if attrs:
                print(f"Attributes: {attrs}")
    else:
        print(f"❌ Rental Error: {result.get('error', 'Unknown error')}")

def test_sales_search(location, workplace):
    """Test sales property search."""
    print("💰 Testing SALES properties...")
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

            travel_info = prop.get("travel_to_work", {})
            if "error" not in travel_info:
                print(f"Travel to work: {travel_info.get('duration_min', 'N/A')} min ({travel_info.get('distance_km', 'N/A')} km)")
            else:
                print(f"Travel info error: {travel_info.get('error', 'N/A')}")

            attrs = prop.get("key_attributes", {})
            if attrs:
                print(f"Attributes: {attrs}")
    else:
        print(f"❌ Sales Error: {sales_result.get('error', 'Unknown error')}")

def test_save_function(location, workplace, property_type="rental"):
    """Test the save functionality for a specific property type."""
    type_name = "RENTALS" if property_type == "rental" else "SALES"
    print(f"💾 Testing save functionality for {type_name}...")
    print("=" * 50)

    save_result = search_and_save_leboncoin_properties(location, workplace, property_type=property_type)

    if save_result.get("status") == "success":
        files = save_result.get("files_saved", [])
        print(f"✅ {type_name.title()} files saved:")
        for file in files:
            print(f"  - {file}")
        print(f"Saved {save_result.get('property_count', 0)} {property_type} properties with enhanced data")
        print(f"Timestamp: {save_result.get('timestamp', 'N/A')}")
    else:
        print(f"❌ {type_name.title()} save error: {save_result.get('error', 'Unknown error')}")

def test_all(location, workplace):
    """Test all functionality (search + save for both types)."""
    print("🔍 Testing ALL MCP Leboncoin functionality...\n")
    print(f"Location: {location}")
    print(f"Workplace: {workplace}")
    print("=" * 60)

    # Test rentals
    test_rental_search(location, workplace)

    print("\n")

    # Test sales
    test_sales_search(location, workplace)

    print("\n")

    # Test save for rentals
    test_save_function(location, workplace, "rental")

    print("\n")

    # Test save for sales
    test_save_function(location, workplace, "sale")


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test MCP Leboncoin tools with various options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_mcp_tools.py                              # Test all functionality
  python test_mcp_tools.py --save-only                  # Test only save functions
  python test_mcp_tools.py --save-only --type rental    # Test only rental save
  python test_mcp_tools.py --save-only --type sale      # Test only sales save
  python test_mcp_tools.py --search-only --type rental  # Test only rental search
  python test_mcp_tools.py --location "Paris" --workplace "La Défense"
        """
    )

    parser.add_argument(
        "--location",
        default="le bourget",
        help="Location to search for properties (default: 'le bourget')"
    )

    parser.add_argument(
        "--workplace",
        default="Gare du Nord, Paris",
        help="Workplace address for travel calculations (default: 'Gare du Nord, Paris')"
    )

    parser.add_argument(
        "--type",
        choices=["rental", "sale", "both"],
        default="both",
        help="Property type to test (default: both)"
    )

    parser.add_argument(
        "--save-only",
        action="store_true",
        help="Test only the save functionality"
    )

    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Test only the search functionality (no saving)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.save_only and args.search_only:
        print("❌ Error: Cannot use --save-only and --search-only together")
        return

    location = args.location
    workplace = args.workplace
    property_type = args.type

    print(f"🔧 Test Configuration:")
    print(f"  Location: {location}")
    print(f"  Workplace: {workplace}")
    print(f"  Property Type: {property_type}")
    print(f"  Mode: {'Save Only' if args.save_only else 'Search Only' if args.search_only else 'Full Test'}")
    print("=" * 60)

    if args.save_only:
        # Test only save functionality
        if property_type == "both":
            test_save_function(location, workplace, "rental")
            print("\n")
            test_save_function(location, workplace, "sale")
        else:
            test_save_function(location, workplace, property_type)

    elif args.search_only:
        # Test only search functionality
        if property_type == "both":
            test_rental_search(location, workplace)
            print("\n")
            test_sales_search(location, workplace)
        elif property_type == "rental":
            test_rental_search(location, workplace)
        else:
            test_sales_search(location, workplace)

    else:
        # Test all functionality
        test_all(location, workplace)

if __name__ == "__main__":
    main()
