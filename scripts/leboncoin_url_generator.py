import urllib.parse
import sys

def generate_leboncoin_url(location, real_estate_type=2):
    """
    Generate a Leboncoin URL for a given location and real estate type.
    
    Args:
        location (str): The location name (e.g., "le bourget", "paris lyon")
        real_estate_type (int): Real estate type code (default: 2)
    
    Returns:
        str: Complete Leboncoin URL
    """
    base_url = "https://www.leboncoin.fr/cl/locations/cp_"
    encoded_location = urllib.parse.quote(location.lower())
    url = f"{base_url}{encoded_location}/real_estate_type:{real_estate_type}"
    return url

def get_real_estate_url(location):
    """
    Simplified function to get real estate URL for a location.
    
    Args:
        location (str): The location name
    
    Returns:
        str: Complete Leboncoin URL for real estate (type 2)
    """
    return generate_leboncoin_url(location, 2)

def bulk_generate_urls(locations, real_estate_type=2):
    """
    Generate URLs for multiple locations.
    
    Args:
        locations (list): List of location names
        real_estate_type (int): Real estate type code (default: 2)
    
    Returns:
        dict: Dictionary mapping locations to their URLs
    """
    return {location: generate_leboncoin_url(location, real_estate_type) 
            for location in locations}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python leboncoin_url_generator.py <location>")
        print("Example: python leboncoin_url_generator.py 'le bourget'")
        sys.exit(1)
    
    location = " ".join(sys.argv[1:])
    url = get_real_estate_url(location)
    print(url)