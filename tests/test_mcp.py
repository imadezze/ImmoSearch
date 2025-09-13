#!/usr/bin/env python
"""Simple test script for MCP tools."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Import MCP tools directly
from mcp_servers.leboncoin_server import search_leboncoin_properties

def test_search_properties():
    """Test the search properties MCP tool."""
    print("Testing search_leboncoin_properties...")
    
    # Test with Le Bourget
    result = search_leboncoin_properties("le bourget")
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Location: {result.get('location')}")
        print(f"Total results: {result.get('search_summary', {}).get('total_results')}")
        print(f"Returned count: {result.get('returned_count')}")
        
        properties = result.get('properties', [])
        print(f"\nFirst few properties:")
        for i, prop in enumerate(properties[:3], 1):
            print(f"\n--- Property {i} ---")
            print(f"Title: {prop.get('title')}")
            print(f"Price: {prop.get('price')}")
            print(f"Location: {prop.get('location')}")
            print(f"Zipcode: {prop.get('zipcode')}")
            print(f"URL: {prop.get('url')}")
            if prop.get('key_attributes'):
                print(f"Attributes: {prop.get('key_attributes')}")
    else:
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    test_search_properties()