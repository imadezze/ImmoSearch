#!/usr/bin/env python
"""Direct test of MCP tools without client."""

import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from mcp_servers.leboncoin_server import search_leboncoin_properties, search_and_save_leboncoin_properties

async def test_search():
    """Test the MCP search tools directly."""
    print("🔍 Testing MCP Leboncoin search tools...\n")
    
    location = "le bourget"
    print(f"Searching properties in: {location}")
    
    # Test search tool
    result = search_leboncoin_properties(location)
    
    print(f"\n📊 Results:")
    print(f"Status: {result.get('status')}")
    
    if result.get('status') == 'success':
        summary = result.get('search_summary', {})
        print(f"Total results: {summary.get('total_results', 0)}")
        print(f"Returned: {result.get('returned_count', 0)} properties")
        
        print(f"\n🏠 Sample properties:")
        for i, prop in enumerate(result.get('properties', [])[:3], 1):
            print(f"\n--- Property {i} ---")
            print(f"Title: {prop.get('title', 'N/A')}")
            print(f"Price: {prop.get('price', 'N/A')}")
            print(f"Location: {prop.get('location', 'N/A')}")
            print(f"Zipcode: {prop.get('zipcode', 'N/A')}")
            
            attrs = prop.get('key_attributes', {})
            if attrs:
                print(f"Attributes: {attrs}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")

    # Test save tool
    print(f"\n💾 Testing save functionality...")
    save_result = search_and_save_leboncoin_properties(location)
    
    if save_result.get('status') == 'success':
        files = save_result.get('files_saved', [])
        print(f"✅ Files saved: {', '.join(files)}")
    else:
        print(f"❌ Save error: {save_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_search())