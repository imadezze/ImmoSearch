#!/usr/bin/env python
"""MCP server exposing DVF (Demandes de Valeurs Foncières) analysis tools."""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import logging
# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import requests
import json
import statistics
from datetime import datetime

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("dvf-server")

class DVFAnalyzer:
    """DVF (Demandes de Valeurs Foncières) analyzer for French real estate data."""
    
    def __init__(self, base_url: str = "https://api.cquest.org/dvf"):
        self.base_url = base_url
    
    def fetch_data(self, code_postal: str, type_local: str = "Appartement") -> Optional[Dict]:
        """Fetch DVF data from API."""
        url = f"{self.base_url}?code_postal={code_postal}&type_local={type_local}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Check if the response is valid
            if not data or 'resultats' not in data:
                return None
            return data
        except requests.RequestException as e:
            return None
    
    def filter_recent_transactions(self, data: list, max_results: int = 100, nb_pieces: Optional[int] = None) -> list:
        """Filter for most recent transactions."""
        if not data:
            return []
            
        # Filter by room count if specified
        filtered_data = data
        if nb_pieces is not None:
            filtered_data = [
                t for t in data 
                if t.get('nombre_pieces_principales') == nb_pieces
            ]
        
        # Sort by date descending
        sorted_transactions = sorted(
            [t for t in filtered_data if t.get('date_mutation')],
            key=lambda x: x['date_mutation'],
            reverse=True
        )
        
        return sorted_transactions[:max_results]
    
    def extract_relevant_data(self, transactions: list, analysis_type: str = "sale") -> list:
        """Extract relevant data from transactions."""
        extracted_data = []
        
        for transaction in transactions:
            valeur_fonciere = transaction.get('valeur_fonciere')
            surface_relle_bati = transaction.get('surface_relle_bati')
            nombre_pieces_principales = transaction.get('nombre_pieces_principales')
            date_mutation = transaction.get('date_mutation')
            voie = transaction.get('voie', '')
            commune = transaction.get('commune', '')
            nature_mutation = transaction.get('nature_mutation', '')
            
            # Keep only transactions with essential data
            if (valeur_fonciere is not None and 
                surface_relle_bati is not None and 
                surface_relle_bati > 0 and
                valeur_fonciere > 0):
                
                prix_m2 = valeur_fonciere / surface_relle_bati
                
                # Calculate estimated rents if requested
                item_data = {
                    'valeur_fonciere': valeur_fonciere,
                    'surface_relle_bati': surface_relle_bati,
                    'nombre_pieces_principales': nombre_pieces_principales,
                    'prix_m2': round(prix_m2, 2),
                    'date_mutation': date_mutation,
                    'voie': voie,
                    'commune': commune,
                    'nature_mutation': nature_mutation
                }
                
                # Add rental data if requested
                if analysis_type == "rental":
                    # Formula: Monthly rent = (Property value × Yield) / (12 × 100)
                    loyer_5pct = round((valeur_fonciere * 5) / (12 * 100), 2)
                    loyer_6pct = round((valeur_fonciere * 6) / (12 * 100), 2)
                    loyer_m2_5pct = round(loyer_5pct / surface_relle_bati, 2)
                    loyer_m2_6pct = round(loyer_6pct / surface_relle_bati, 2)
                    
                    item_data.update({
                        'loyer_mensuel_5pct': loyer_5pct,
                        'loyer_mensuel_6pct': loyer_6pct,
                        'loyer_m2_5pct': loyer_m2_5pct,
                        'loyer_m2_6pct': loyer_m2_6pct
                    })
                
                extracted_data.append(item_data)
        
        return extracted_data
    
    def remove_outliers_iqr(self, data: list) -> list:
        """
        Remove outliers using IQR method (keep only Q1 to Q3)
        """
        if len(data) < 4:
            return data
        
        # Extract prices per m²
        prix_m2_list = [item['prix_m2'] for item in data]
        
        # Calculate Q1, Q3 and IQR
        q1 = statistics.quantiles(prix_m2_list, n=4)[0]  # 25th percentile
        q3 = statistics.quantiles(prix_m2_list, n=4)[2]  # 75th percentile
        iqr = q3 - q1
        
        # Use classic IQR method: Q1 - 1.5*IQR and Q3 + 1.5*IQR
        lower_bound = max(q1 - 1.5 * iqr, 0)  # No negative prices
        upper_bound = q3 + 1.5 * iqr
        
        # Filter data
        filtered_data = [
            item for item in data
            if lower_bound <= item['prix_m2'] <= upper_bound
        ]
        
        return filtered_data
    
    def calculate_statistics(self, data: list, analysis_type: str = "sale") -> Dict:
        """Calculate statistics on price per m² or rental estimates."""
        if not data:
            return {}
        
        if analysis_type == "sale":
            prix_m2_list = [item['prix_m2'] for item in data]
            
            stats = {
                'nb_transactions': len(data),
                'prix_m2_moyen': round(statistics.mean(prix_m2_list), 2),
                'prix_m2_median': round(statistics.median(prix_m2_list), 2),
                'prix_m2_min': min(prix_m2_list),
                'prix_m2_max': max(prix_m2_list),
            }
            
            if len(prix_m2_list) > 1:
                stats['prix_m2_ecart_type'] = round(statistics.stdev(prix_m2_list), 2)
        
        else:  # rental
            loyer_5pct_list = [item['loyer_mensuel_5pct'] for item in data]
            loyer_6pct_list = [item['loyer_mensuel_6pct'] for item in data]
            loyer_m2_5pct_list = [item['loyer_m2_5pct'] for item in data]
            loyer_m2_6pct_list = [item['loyer_m2_6pct'] for item in data]
            
            stats = {
                'nb_transactions': len(data),
                'loyer_5pct_moyen': round(statistics.mean(loyer_5pct_list), 2),
                'loyer_5pct_median': round(statistics.median(loyer_5pct_list), 2),
                'loyer_5pct_min': min(loyer_5pct_list),
                'loyer_5pct_max': max(loyer_5pct_list),
                'loyer_6pct_moyen': round(statistics.mean(loyer_6pct_list), 2),
                'loyer_6pct_median': round(statistics.median(loyer_6pct_list), 2),
                'loyer_6pct_min': min(loyer_6pct_list),
                'loyer_6pct_max': max(loyer_6pct_list),
                'loyer_m2_5pct_moyen': round(statistics.mean(loyer_m2_5pct_list), 2),
                'loyer_m2_5pct_median': round(statistics.median(loyer_m2_5pct_list), 2),
                'loyer_m2_6pct_moyen': round(statistics.mean(loyer_m2_6pct_list), 2),
                'loyer_m2_6pct_median': round(statistics.median(loyer_m2_6pct_list), 2),
            }
            
            if len(loyer_5pct_list) > 1:
                stats['loyer_5pct_ecart_type'] = round(statistics.stdev(loyer_5pct_list), 2)
                stats['loyer_6pct_ecart_type'] = round(statistics.stdev(loyer_6pct_list), 2)
        
        return stats

@mcp.tool()
def analyze_dvf_data(code_postal: str, max_results: int = 100, nb_pieces: Optional[int] = None, analysis_type: str = "sale") -> Dict[str, Any]:
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
    logging.info(f"Analyzing DVF data for code postal: {code_postal}, max results: {max_results}, nb pieces: {nb_pieces}, analysis type: {analysis_type}")
    try:
        analyzer = DVFAnalyzer()
        
        # 1. Fetch data
        raw_data = analyzer.fetch_data(code_postal)
        
        if not raw_data or 'resultats' not in raw_data:
            return {
                "code_postal": code_postal,
                "error": "No data available for this postal code",
                "status": "error"
            }
        
        total_results = raw_data.get('nb_resultats', 0)
        derniere_maj = raw_data.get('derniere_maj', 'Unknown')
        
        # 2. Filter recent transactions
        recent_data = analyzer.filter_recent_transactions(
            raw_data['resultats'], max_results, nb_pieces
        )
        
        if not recent_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No recent transactions found with specified criteria",
                "status": "error"
            }
        
        # 3. Extract relevant data
        extracted_data = analyzer.extract_relevant_data(recent_data, analysis_type)
        
        if not extracted_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No transactions with complete data found",
                "status": "error"
            }
        
        # 4. Remove outliers
        cleaned_data = analyzer.remove_outliers_iqr(extracted_data)
        
        if not cleaned_data:
            return {
                "code_postal": code_postal,
                "nb_pieces": nb_pieces,
                "error": "No transactions after outlier removal",
                "status": "error"
            }
        
        # 5. Calculate statistics (on cleaned data)
        stats = analyzer.calculate_statistics(cleaned_data, analysis_type)
        original_stats = analyzer.calculate_statistics(extracted_data, analysis_type)
        
        # 6. Get recent examples (top 5, from cleaned data)
        recent_examples = sorted(cleaned_data, 
                               key=lambda x: x['date_mutation'], 
                               reverse=True)[:5]
        
        # 7. Analyze by rooms (on cleaned data)
        rooms_data = {}
        for item in cleaned_data:
            nb_p = item.get('nombre_pieces_principales', 'Unknown')
            if nb_p not in rooms_data:
                rooms_data[nb_p] = []
            rooms_data[nb_p].append(item['prix_m2'])
        
        rooms_stats = {}
        for nb_p, prix_list in rooms_data.items():
            if prix_list:
                rooms_stats[str(nb_p)] = {
                    'nb_transactions': len(prix_list),
                    'prix_m2_moyen': round(statistics.mean(prix_list), 2),
                    'prix_m2_median': round(statistics.median(prix_list), 2),
                }
        
        # 7. Get date range
        if recent_data:
            most_recent = recent_data[0]['date_mutation']
            oldest_selected = recent_data[-1]['date_mutation']
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
                    "oldest_in_selection": oldest_selected
                }
            },
            "comparison": {
                "with_outliers": {
                    "transactions": original_stats.get('nb_transactions', 0),
                    "average_price_m2": original_stats.get('prix_m2_moyen', 0)
                },
                "without_outliers": {
                    "transactions": stats.get('nb_transactions', 0),
                    "average_price_m2": stats.get('prix_m2_moyen', 0)
                }
            },
            "statistics": stats,
            "statistics_by_rooms": rooms_stats,
            "recent_examples": recent_examples,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "code_postal": code_postal,
            "nb_pieces": nb_pieces,
            "error": f"Analysis failed: {str(e)}",
            "status": "error"
        }

@mcp.tool()
def estimate_rental_prices(code_postal: str, max_results: int = 100, nb_pieces: Optional[int] = None) -> Dict[str, Any]:
    """
    Estimate rental prices based on DVF sales data using 5% and 6% yield rates.
    
    Args:
        code_postal: French postal code (e.g., "92230", "75001")
        max_results: Maximum number of recent transactions to analyze (default: 100)
        nb_pieces: Filter by number of rooms (optional)
    
    Returns:
        Dictionary with rental estimations for both 5% and 6% yields
    """
    try:
        # Use the rental analysis
        result = analyze_dvf_data(code_postal, max_results=max_results, nb_pieces=nb_pieces, analysis_type="rental")
        
        if result["status"] == "error":
            return result
        
        stats = result.get("statistics", {})
        
        return {
            "code_postal": code_postal,
            "nb_pieces_filter": nb_pieces,
            "rental_estimates": {
                "yield_5_percent": {
                    "average_monthly_rent": stats.get("loyer_5pct_moyen", 0),
                    "median_monthly_rent": stats.get("loyer_5pct_median", 0),
                    "average_rent_per_m2": stats.get("loyer_m2_5pct_moyen", 0),
                    "median_rent_per_m2": stats.get("loyer_m2_5pct_median", 0),
                    "rent_range": {
                        "min": stats.get("loyer_5pct_min", 0),
                        "max": stats.get("loyer_5pct_max", 0)
                    }
                },
                "yield_6_percent": {
                    "average_monthly_rent": stats.get("loyer_6pct_moyen", 0),
                    "median_monthly_rent": stats.get("loyer_6pct_median", 0),
                    "average_rent_per_m2": stats.get("loyer_m2_6pct_moyen", 0),
                    "median_rent_per_m2": stats.get("loyer_m2_6pct_median", 0),
                    "rent_range": {
                        "min": stats.get("loyer_6pct_min", 0),
                        "max": stats.get("loyer_6pct_max", 0)
                    }
                },
                "transactions_analyzed": stats.get("nb_transactions", 0)
            },
            "data_last_updated": result.get("analysis_summary", {}).get("data_last_updated", "Unknown"),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "code_postal": code_postal,
            "nb_pieces": nb_pieces,
            "error": f"Rental estimation failed: {str(e)}",
            "status": "error"
        }

@mcp.tool()
def get_dvf_price_summary(code_postal: str, nb_pieces: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a quick price summary for DVF data (simplified version).
    
    Args:
        code_postal: French postal code (e.g., "92230", "75001")
        nb_pieces: Filter by number of rooms (optional)
    
    Returns:
        Dictionary with price summary statistics
    """
    try:
        # Analyze with fewer results for quick summary
        result = analyze_dvf_data(code_postal, max_results=50, nb_pieces=nb_pieces)
        
        if result["status"] == "error":
            return result
        
        stats = result.get("statistics", {})
        
        return {
            "code_postal": code_postal,
            "nb_pieces_filter": nb_pieces,
            "price_summary": {
                "transactions_analyzed": stats.get("nb_transactions", 0),
                "average_price_per_m2": stats.get("prix_m2_moyen", 0),
                "median_price_per_m2": stats.get("prix_m2_median", 0),
                "price_range": {
                    "min": stats.get("prix_m2_min", 0),
                    "max": stats.get("prix_m2_max", 0)
                }
            },
            "data_last_updated": result.get("analysis_summary", {}).get("data_last_updated", "Unknown"),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "code_postal": code_postal,
            "nb_pieces": nb_pieces,
            "error": f"Price summary failed: {str(e)}",
            "status": "error"
        }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")