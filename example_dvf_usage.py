#!/usr/bin/env python
"""Example usage of DVF MCP tools."""

from mcp_servers.dvf_server import analyze_dvf_data, get_dvf_price_summary, estimate_rental_prices

def example_dvf_analysis():
    """Example of how to use DVF analysis tools."""
    print("🏠 DVF Analysis Examples")
    print("=" * 40)
    
    # Example 1: Quick price summary
    print("\n💰 Quick Price Summary for Gennevilliers (92230)")
    result = get_dvf_price_summary("92230")
    if result["status"] == "success":
        summary = result["price_summary"]
        print(f"Average price/m²: {summary['average_price_per_m2']} €")
        print(f"Median price/m²: {summary['median_price_per_m2']} €")
        print(f"Based on {summary['transactions_analyzed']} transactions")
    
    # Example 2: Analysis for 3-room apartments
    print("\n🏠 3-Room Apartments Analysis")
    result = analyze_dvf_data("92230", max_results=100, nb_pieces=3)
    if result["status"] == "success":
        stats = result["statistics"]
        print(f"Transactions analyzed: {stats['nb_transactions']}")
        print(f"Average price/m²: {stats['prix_m2_moyen']} €")
        print(f"Price range: {stats['prix_m2_min']} - {stats['prix_m2_max']} €/m²")
        
        # Show recent examples
        print("\nRecent transactions:")
        for i, example in enumerate(result["recent_examples"][:3], 1):
            print(f"{i}. {example['date_mutation']} - {example['valeur_fonciere']:,} € - {example['surface_relle_bati']} m² - {example['prix_m2']} €/m²")
    
    # Example 3: Rental estimation
    print("\n🏠 Rental Estimation for Gennevilliers (92230)")
    rental_result = estimate_rental_prices("92230", max_results=50)
    if rental_result["status"] == "success":
        estimates = rental_result["rental_estimates"]
        print(f"Based on {estimates['transactions_analyzed']} transactions:")
        
        print("\n💰 5% Yield:")
        print(f"Average rent: {estimates['yield_5_percent']['average_monthly_rent']} €/month")
        print(f"Average rent/m²: {estimates['yield_5_percent']['average_rent_per_m2']} €/m²/month")
        
        print("\n💰 6% Yield:")
        print(f"Average rent: {estimates['yield_6_percent']['average_monthly_rent']} €/month")
        print(f"Average rent/m²: {estimates['yield_6_percent']['average_rent_per_m2']} €/m²/month")

if __name__ == "__main__":
    example_dvf_analysis()