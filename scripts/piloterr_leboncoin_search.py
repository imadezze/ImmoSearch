import requests
import json
import sys
import os
from dotenv import load_dotenv
from leboncoin_url_generator import get_real_estate_url

# Load environment variables from .env file
load_dotenv()

class PiloterrLeboncoinSearch:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('PILOTERR_API_KEY')
        self.base_url = "https://piloterr.com/api/v2/leboncoin/search"
        
        if not self.api_key:
            raise ValueError("API key is required. Set PILOTERR_API_KEY environment variable or pass api_key parameter.")
    
    def search(self, location, return_page_source=False):
        """
        Search Leboncoin for real estate in a specific location using Piloterr API.
        
        Args:
            location (str): Location name (e.g., "le bourget", "paris")
            return_page_source (bool): Whether to return HTML source
            
        Returns:
            dict: API response with search results
        """
        leboncoin_url = get_real_estate_url(location)
        
        headers = {
            'x-api-key': self.api_key
        }
        
        params = {
            'query': leboncoin_url
        }
        
        if return_page_source:
            params['return_page_source'] = 'true'
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None
    
    def format_results(self, results):
        """
        Format and structure the search results for better readability.
        
        Args:
            results (dict): Raw API response
            
        Returns:
            dict: Formatted results
        """
        if not results or 'ads' not in results:
            return {"error": "No results found or invalid response"}
        
        formatted = {
            "search_summary": {
                "total_results": results.get('total', 0),
                "ads_returned": len(results.get('ads', []))
            },
            "properties": []
        }
        
        for ad in results.get('ads', []):
            location_data = ad.get('location', {})
            property_info = {
                "title": ad.get('subject', 'N/A'),
                "price": self._format_price(ad.get('price')),
                "location": self._format_location(location_data),
                "zipcode": location_data.get('zipcode', 'N/A'),
                "district": location_data.get('district', 'N/A'),
                "department_name": location_data.get('department_name', 'N/A'),
                "region_name": location_data.get('region_name', 'N/A'),
                "category": ad.get('category_name', 'N/A'),
                "ad_type": ad.get('ad_type', 'N/A'),
                "url": ad.get('url', 'N/A'),
                "key_attributes": self._extract_key_attributes(ad.get('attributes', [])),
                "images_count": len(ad.get('images', [])) if ad.get('images') else 0
            }
            formatted["properties"].append(property_info)
        
        return formatted
    
    def _format_price(self, price_data):
        """Format price information."""
        if not price_data:
            return "Price not specified"
        
        if isinstance(price_data, dict):
            value = price_data.get('value', 0)
            currency = price_data.get('currency', '€')
            
            # Clean brackets from value if it's a string
            if isinstance(value, str):
                value = value.strip('[]')
                try:
                    value = int(value)
                except ValueError:
                    pass
            
            return f"{value:,} {currency}"
        
        return str(price_data)
    
    def _format_location(self, location_data):
        """Format location information."""
        if not location_data:
            return "Location not specified"
        
        location_parts = []
        if location_data.get('city'):
            location_parts.append(location_data['city'])
        if location_data.get('zipcode'):
            location_parts.append(f"({location_data['zipcode']})")
        if location_data.get('department'):
            location_parts.append(location_data['department'])
        
        return " ".join(location_parts) if location_parts else "Location not specified"
    
    def _extract_key_attributes(self, attributes):
        """Extract key property attributes."""
        key_attrs = {}
        
        for attr in attributes:
            key = attr.get('key', '').lower()
            
            if key in ['rooms', 'bedrooms', 'surface', 'land_size', 'energy_rate', 'ges', 'furnished', 'heating_type', 'charges_included', 'floor_number']:
                # For rooms, bedrooms, surface, land_size use raw value, others use value_label
                if key in ['rooms', 'bedrooms', 'surface', 'land_size', 'floor_number']:
                    value = attr.get('value', '')
                else:
                    value = attr.get('value_label', attr.get('value', ''))
                key_attrs[key] = value
        
        return key_attrs
    
    def save_results(self, results, filename="leboncoin_results.json"):
        """Save results to JSON file in results folder."""
        try:
            # Create results directory if it doesn't exist
            results_dir = "results"
            os.makedirs(results_dir, exist_ok=True)
            
            # Save file in results directory
            filepath = os.path.join(results_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {filepath}")
        except Exception as e:
            print(f"Error saving results: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python piloterr_leboncoin_search.py <location> [api_key]")
        print("Example: python piloterr_leboncoin_search.py 'le bourget'")
        print("Note: Set PILOTERR_API_KEY environment variable or pass as second argument")
        sys.exit(1)
    
    location = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        searcher = PiloterrLeboncoinSearch(api_key)
        
        print(f"Searching for properties in: {location}")
        raw_results = searcher.search(location)
        
        if raw_results:
            formatted_results = searcher.format_results(raw_results)
            
            # Save raw results
            searcher.save_results(raw_results, "raw_leboncoin_results.json")
            
            # Save formatted results
            searcher.save_results(formatted_results, "formatted_leboncoin_results.json")
            
            # Print summary
            print(f"\nFound {formatted_results['search_summary']['total_results']} total results")
            print(f"Retrieved {formatted_results['search_summary']['ads_returned']} ads")
            
            # Print first few results
            for i, prop in enumerate(formatted_results['properties'][:3], 1):
                print(f"\n--- Property {i} ---")
                print(f"Title: {prop['title']}")
                print(f"Price: {prop['price']}")
                print(f"Location: {prop['location']}")
                print(f"Key attributes: {prop['key_attributes']}")
        else:
            print("No results found or error occurred")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()