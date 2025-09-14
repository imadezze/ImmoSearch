#!/usr/bin/env python
"""MCP server exposing DVF (Demandes de Valeurs Foncières) analysis tools."""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
import pickle
# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

import json
import statistics
from datetime import datetime

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from scripts.leboncoin_url_generator import get_real_estate_url
from scripts.piloterr_leboncoin_search import PiloterrLeboncoinSearch
from scripts.static_map_generator import (
    aggregated_maps_links,
    fetch_and_save_map,
    floats_to_blue_red_hex,
    parse_price_to_float,
    upload_to_imgbb,
)
from scripts.travel_time import get_distance_time, reverse_geocode

# Try to import W&B integration, fallback if not available
try:
    from scripts.wandb_integration import ensure_tracer, trace_mcp_operation

    tracer = ensure_tracer()
except ImportError:
    # W&B not available, create no-op tracer and decorator
    tracer = None

    def trace_mcp_operation(operation_name: str):
        def decorator(func):
            return func

        return decorator


# Load environment variables
load_dotenv()

# Create MCP server with Lambda-compatible settings
mcp = FastMCP("immosearch-server", stateless_http=True, debug=False, port=3000)
display_prompt_inject = "Create an iframe with the following URL in in canvas: "

class DVFAnalyzer:
    """DVF (Demandes de Valeurs Foncières) analyzer for French real estate data."""

    def __init__(self, base_url: str = "https://api.cquest.org/dvf"):
        self.base_url = base_url

    def fetch_data(
        self, code_postal: str, type_local: str = "Appartement"
    ) -> Optional[Dict]:
        """Fetch DVF data from API."""
        url = f"{self.base_url}?code_postal={code_postal}&type_local={type_local}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Check if the response is valid
            if not data or "resultats" not in data:
                return None
            return data
        except requests.RequestException as e:
            return None

    def filter_recent_transactions(
        self, data: list, max_results: int = 100, nb_pieces: Optional[int] = None
    ) -> list:
        """Filter for most recent transactions."""
        if not data:
            return []

        # Filter by room count if specified
        filtered_data = data
        if nb_pieces is not None:
            filtered_data = [
                t for t in data if t.get("nombre_pieces_principales") == nb_pieces
            ]

        # Sort by date descending
        sorted_transactions = sorted(
            [t for t in filtered_data if t.get("date_mutation")],
            key=lambda x: x["date_mutation"],
            reverse=True,
        )

        return sorted_transactions[:max_results]

    def extract_relevant_data(
        self, transactions: list, analysis_type: str = "sale"
    ) -> list:
        """Extract relevant data from transactions and remove duplicates."""
        extracted_data = []
        seen_transactions = set()

        for transaction in transactions:
            valeur_fonciere = transaction.get("valeur_fonciere")
            surface_relle_bati = transaction.get("surface_relle_bati")
            nombre_pieces_principales = transaction.get("nombre_pieces_principales")
            date_mutation = transaction.get("date_mutation")
            voie = transaction.get("voie", "")
            commune = transaction.get("commune", "")
            nature_mutation = transaction.get("nature_mutation", "")

            # Keep only transactions with essential data
            if (
                valeur_fonciere is not None
                and surface_relle_bati is not None
                and surface_relle_bati > 0
                and valeur_fonciere > 0
            ):

                prix_m2 = valeur_fonciere / surface_relle_bati

                # Create a unique key to identify duplicates
                # Using date, value, surface, and street to identify same transaction
                unique_key = (date_mutation, valeur_fonciere, surface_relle_bati, voie)

                # Skip if we've already seen this exact transaction
                if unique_key in seen_transactions:
                    continue

                seen_transactions.add(unique_key)

                # Calculate estimated rents if requested
                item_data = {
                    "valeur_fonciere": valeur_fonciere,
                    "surface_relle_bati": surface_relle_bati,
                    "nombre_pieces_principales": nombre_pieces_principales,
                    "prix_m2": round(prix_m2, 2),
                    "date_mutation": date_mutation,
                    "voie": voie,
                    "commune": commune,
                    "nature_mutation": nature_mutation,
                }

                # Add rental data if requested
                if analysis_type == "rental":
                    # Formula: Monthly rent = (Property value × Yield) / (12 × 100)
                    loyer_5pct = round((valeur_fonciere * 5) / (12 * 100), 2)
                    loyer_6pct = round((valeur_fonciere * 6) / (12 * 100), 2)
                    loyer_7pct = round((valeur_fonciere * 7) / (12 * 100), 2)
                    loyer_7pct = round((valeur_fonciere * 7) / (12 * 100), 2)
                    loyer_m2_5pct = round(loyer_5pct / surface_relle_bati, 2)
                    loyer_m2_6pct = round(loyer_6pct / surface_relle_bati, 2)
                    loyer_m2_7pct = round(loyer_7pct / surface_relle_bati, 2)
                    loyer_m2_7pct = round(loyer_7pct / surface_relle_bati, 2)

                    item_data.update(
                        {
                            "loyer_mensuel_5pct": loyer_5pct,
                            "loyer_mensuel_6pct": loyer_6pct,
                            "loyer_mensuel_7pct": loyer_7pct,
                            "loyer_mensuel_7pct": loyer_7pct,
                            "loyer_m2_5pct": loyer_m2_5pct,
                            "loyer_m2_6pct": loyer_m2_6pct,
                            "loyer_m2_7pct": loyer_m2_7pct,
                            "loyer_m2_7pct": loyer_m2_7pct,
                        }
                    )

                extracted_data.append(item_data)

        return extracted_data

    def remove_outliers_iqr(self, data: list) -> list:
        """
        Remove outliers by eliminating top and bottom 15% of price/m² values
        """
        if len(data) < 4:
            return data

        # Extract prices per m²
        prix_m2_list = [item["prix_m2"] for item in data]

        # Sort prices to get percentiles
        sorted_prices = sorted(prix_m2_list)

        # Calculate 15th and 85th percentiles (remove top and bottom 15%)
        n = len(sorted_prices)
        lower_index = int(n * 0.15)
        upper_index = int(n * 0.85)

        # Get bounds
        lower_bound = (
            sorted_prices[lower_index] if lower_index < n else sorted_prices[0]
        )
        upper_bound = (
            sorted_prices[upper_index] if upper_index < n else sorted_prices[-1]
        )

        # Filter data
        filtered_data = [
            item for item in data if lower_bound <= item["prix_m2"] <= upper_bound
        ]

        return filtered_data

    def calculate_statistics(self, data: list, analysis_type: str = "sale") -> Dict:
        """Calculate statistics on price per m² or rental estimates."""
        if not data:
            return {}

        if analysis_type == "sale":
            prix_m2_list = [item["prix_m2"] for item in data]

            stats = {
                "nb_transactions": len(data),
                "prix_m2_moyen": round(statistics.mean(prix_m2_list), 2),
                "prix_m2_median": round(statistics.median(prix_m2_list), 2),
                "prix_m2_min": min(prix_m2_list),
                "prix_m2_max": max(prix_m2_list),
            }

            if len(prix_m2_list) > 1:
                stats["prix_m2_ecart_type"] = round(statistics.stdev(prix_m2_list), 2)

        else:  # rental
            # Concatenate 5%, 6%, and 7% data together
            loyer_combined = []
            loyer_m2_combined = []

            for item in data:
                loyer_combined.extend(
                    [
                        item["loyer_mensuel_5pct"],
                        item["loyer_mensuel_6pct"],
                        item["loyer_mensuel_7pct"],
                    ]
                )
                loyer_m2_combined.extend(
                    [
                        item["loyer_m2_5pct"],
                        item["loyer_m2_6pct"],
                        item["loyer_m2_7pct"],
                    ]
                )

            stats = {
                "nb_transactions": len(data),
                "loyer_moyen": round(statistics.mean(loyer_combined), 2),
                "loyer_median": round(statistics.median(loyer_combined), 2),
                "loyer_min": min(loyer_combined),
                "loyer_max": max(loyer_combined),
                "loyer_m2_moyen": round(statistics.mean(loyer_m2_combined), 2),
                "loyer_m2_median": round(statistics.median(loyer_m2_combined), 2),
                "loyer_m2_min": min(loyer_m2_combined),
                "loyer_m2_max": max(loyer_m2_combined),
            }

            if len(loyer_combined) > 1:
                stats["loyer_ecart_type"] = round(statistics.stdev(loyer_combined), 2)
                stats["loyer_m2_ecart_type"] = round(
                    statistics.stdev(loyer_m2_combined), 2
                )

        return stats


@trace_mcp_operation("dvf_analysis")
@mcp.tool()
def analyze_dvf_data(
    code_postal: str,
    max_results: int = 100,
    nb_pieces: Optional[int] = None,
    analysis_type: str = "sale",
) -> Dict[str, Any]:
    """
    Analyze DVF (French real estate transaction) data for a given postal code.

    Args:
        code_postal: French postal code (e.g., "92230", "75001")
        max_results: Maximum number of recent transactions to analyze (default: 100)
        nb_pieces: Filter by number of rooms (optional, e.g., 1, 2, 3, 4, 5)
        analysis_type: "sale" for sales analysis, "rental" for rental estimation (default: "sale")

    Returns:
        Dictionary with analysis results including statistics and recent transactions
    """
    logging.info(
        f"Analyzing DVF data for code postal: {code_postal}, max results: {max_results}, nb pieces: {nb_pieces}, analysis type: {analysis_type}"
    )
    try:
        analyzer = DVFAnalyzer()

        # 1. Fetch data
        raw_data = analyzer.fetch_data(code_postal)

        if not raw_data or "resultats" not in raw_data:
            return {
                "code_postal": code_postal,
                "error": "No data available for this postal code",
                "status": "error",
            }

        total_results = raw_data.get("nb_resultats", 0)
        derniere_maj = raw_data.get("derniere_maj", "Unknown")

        # 2. Filter recent transactions
        recent_data = analyzer.filter_recent_transactions(
            raw_data["resultats"], max_results, nb_pieces
        )

        if not recent_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No recent transactions found with specified criteria",
                "status": "error",
            }

        # 3. Extract relevant data
        extracted_data = analyzer.extract_relevant_data(recent_data, analysis_type)

        if not extracted_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No transactions with complete data found",
                "status": "error",
            }

        # 4. Remove outliers
        cleaned_data = analyzer.remove_outliers_iqr(extracted_data)

        if not cleaned_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No transactions after outlier removal",
                "status": "error",
            }

        # 5. Calculate statistics (on cleaned data)
        stats = analyzer.calculate_statistics(cleaned_data, analysis_type)

        # 6. Get date range
        if recent_data:
            most_recent = recent_data[0]["date_mutation"]
            oldest_selected = recent_data[-1]["date_mutation"]
        else:
            most_recent = oldest_selected = None

        return {
            "code_postal": code_postal,
            "nb_pieces_filter": nb_pieces,
            "analysis_type": analysis_type,
            "analysis_summary": {
                "total_transactions_available": total_results,
                "data_last_updated": derniere_maj,
                "transactions_with_data": len(extracted_data),
                "transactions_analyzed": len(cleaned_data),
                "outliers_removed": len(extracted_data) - len(cleaned_data),
                "date_range": {
                    "most_recent": most_recent,
                    "oldest_in_selection": oldest_selected,
                },
            },
            "statistics": stats,
            "status": "success",
        }

    except Exception as e:
        return {
            "code_postal": code_postal,
            "nb_pieces": nb_pieces,
            "error": f"Analysis failed: {str(e)}",
            "status": "error",
        }


@trace_mcp_operation("property_search")
@mcp.tool()
def search_leboncoin_properties(
    location: str,
    workplace: str,
    property_type: str = "rental",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search Leboncoin for properties in a specific location using Piloterr API with travel time to workplace.

    Args:
        location: The location name to search for properties
        workplace: Workplace address for travel time calculation (required)
        property_type: "rental" for rentals, "sale" for sales (default: "rental")
        api_key: Optional Piloterr API key (uses environment variable if not provided)

    Returns:
        Dictionary with search results, property information including travel times and an url pointing to a map of the properties
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

        # Perform search with property type parameter
        raw_results = searcher.search(location, property_type=property_type)
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

        loc_list, prices_list = [], []
        # Add travel time calculations and street address for each property
        for i, prop in enumerate(properties):
            try:
                lat = prop.get("latitude")
                lng = prop.get("longitude")
                prop["idx"] = i

                if lat != "N/A" and lng != "N/A":
                    # Helpers to compute the map later
                    loc_list.append((lat, lng))
                    prices_list.append(parse_price_to_float(prop.get("price")))

                    # Calculate travel time using coordinates
                    travel_info = get_distance_time(
                        origin_latlng=(float(lat), float(lng)),
                        destination_address=workplace,
                        mode="transit",
                    )

                    # Add W&B tracing for travel calculation
                    if tracer and tracer.is_enabled():
                        travel_info = tracer.trace_travel_calculation(
                            (float(lat), float(lng)), workplace, "transit", travel_info
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

            # Remove unwanted fields (OSEF parameters)
            # prop.pop("latitude", None)
            # prop.pop("longitude", None)
            prop.pop("zipcode", None)
            prop.pop("department_name", None)
            prop.pop("region_name", None)
            prop.pop("category", None)
            prop.pop("ad_type", None)
            prop.pop("images_count", None)

            # Clean up key_attributes - remove OSEF fields
            if "key_attributes" in prop:
                prop["key_attributes"].pop("ges", None)
                prop["key_attributes"].pop("heating_type", None)

        result = {
            "location": location,
            "workplace": workplace,
            "property_type": property_type,
            "search_summary": formatted_results.get("search_summary", {}),
            "properties": properties,
            "returned_count": len(properties),
            "status": "success",
        }

        global fetched_properties
        fetched_properties = properties

        # Add W&B tracing for property search
        if tracer and tracer.is_enabled():
            result = tracer.trace_property_search(
                location, workplace, property_type, result
            )

        return result

    except Exception as e:
        return {"location": location, "error": str(e), "status": "error"}

@mcp.tool()
def get_map(idx_list: List[int]) -> str:
    """
    Generates a map of specified locations and uploads it to an image hosting service.

    This function filters a global list of fetched properties based on the provided indices,
    then generates a static map showing these locations with colored markers. The map is
    saved locally, uploaded to imgbb, and the URL of the uploaded image is returned.

    Args:
        idx_list (List[int]): A list of integer indices corresponding to the locations
                              in the `fetched_properties` list to be included on the map.

    Returns:
        str: The URL of the generated map image hosted on imgbb.
    """

    filtered_list = [f for (i, f) in enumerate(fetched_properties) if i in idx_list]
    labels = [str(i) for i in range(len(fetched_properties))]
    colors = floats_to_blue_red_hex(filtered_list)
    map_link = aggregated_maps_links(filtered_list,  colors=colors, labels=labels)["static_map"]
    fetch_and_save_map(map_link, output_path="map.png")
    url = upload_to_imgbb("map.png")
    return url


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
