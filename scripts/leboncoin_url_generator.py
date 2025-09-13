import urllib.parse
import sys

def generate_leboncoin_url(location, real_estate_type=2, property_type="rental"):
    """
    Generate a Leboncoin URL for a given location and real estate type.

    Args:
        location (str): The location name (e.g., "le bourget", "paris lyon")
        real_estate_type (int): Real estate type code (default: 2)
        property_type (str): "rental" for rentals, "sale" for sales (default: "rental")

    Returns:
        str: Complete Leboncoin URL
    """
    # Format location for URL
    encoded_location = urllib.parse.quote(location.lower().replace(' ', '-'))

    if property_type.lower() in ["rental", "rent", "location", "locations"]:
        # Rental URL pattern: https://www.leboncoin.fr/cl/locations/cp_location/real_estate_type:2
        base_url = "https://www.leboncoin.fr/cl/locations/cp_"
        url = f"{base_url}{encoded_location}/real_estate_type:{real_estate_type}"
    elif property_type.lower() in ["sale", "sales", "sell", "vente", "ventes"]:
        # Sales URL pattern: https://www.leboncoin.fr/cl/ventes_immobilieres/cp_location/real_estate_type:2
        base_url = "https://www.leboncoin.fr/cl/ventes_immobilieres/cp_"
        url = f"{base_url}{encoded_location}/real_estate_type:{real_estate_type}"
    else:
        raise ValueError(f"Invalid property_type '{property_type}'. Use 'rental' or 'sale'.")

    return url

def get_real_estate_url(location, property_type="rental"):
    """
    Simplified function to get real estate URL for a location.

    Args:
        location (str): The location name
        property_type (str): "rental" for rentals, "sale" for sales

    Returns:
        str: Complete Leboncoin URL for real estate (type 2)
    """
    return generate_leboncoin_url(location, 2, property_type)

def bulk_generate_urls(locations, real_estate_type=2, property_type="rental"):
    """
    Generate URLs for multiple locations.

    Args:
        locations (list): List of location names
        real_estate_type (int): Real estate type code (default: 2)
        property_type (str): "rental" for rentals, "sale" for sales

    Returns:
        dict: Dictionary mapping locations to their URLs
    """
    return {location: generate_leboncoin_url(location, real_estate_type, property_type)
            for location in locations}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python leboncoin_url_generator.py <location>")
        print("Example: python leboncoin_url_generator.py 'le bourget'")
        sys.exit(1)
    
    location = " ".join(sys.argv[1:])
    url = get_real_estate_url(location)
    print(url)