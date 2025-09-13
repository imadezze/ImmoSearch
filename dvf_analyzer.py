#!/usr/bin/env python
"""
Script pour extraire et analyser les données DVF (Demandes de Valeurs Foncières)
Version modifiée pour analyser les données les plus récentes disponibles
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import statistics

class DVFAnalyzer:
    def __init__(self, base_url: str = "https://api.cquest.org/dvf"):
        self.base_url = base_url
    
    def fetch_data(self, code_postal: str, type_local: str = "Appartement") -> Optional[Dict]:
        """
        Récupère les données DVF pour un code postal donné
        
        Args:
            code_postal: Code postal à analyser
            type_local: Type de local (par défaut "Appartement")
            
        Returns:
            Données JSON de l'API ou None en cas d'erreur
        """
        url = f"{self.base_url}?code_postal={code_postal}&type_local={type_local}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Erreur lors de l'appel API: {e}")
            return None
    
    def filter_recent_transactions(self, data: List[Dict], max_results: int = 500, nb_pieces: Optional[int] = None) -> List[Dict]:
        """
        Filtre pour obtenir les X transactions les plus récentes
        
        Args:
            data: Liste des transactions
            max_results: Nombre maximum de transactions à récupérer
            nb_pieces: Nombre de pièces à filtrer (optionnel)
            
        Returns:
            Liste des transactions les plus récentes (limitée à max_results)
        """
        # Filtrer par nombre de pièces si spécifié
        filtered_data = data
        if nb_pieces is not None:
            filtered_data = [
                t for t in data 
                if t.get('nombre_pieces_principales') == nb_pieces
            ]
            print(f"🏠 Filtrage par nombre de pièces: {nb_pieces}")
            print(f"🗒️ {len(filtered_data)} transactions avec {nb_pieces} pièces trouvées")
        
        # Trier par date décroissante
        sorted_transactions = sorted(
            [t for t in filtered_data if t.get('date_mutation')],
            key=lambda x: x['date_mutation'],
            reverse=True
        )
        
        # Prendre les X premiers
        recent_transactions = sorted_transactions[:max_results]
        
        if recent_transactions:
            most_recent = recent_transactions[0]['date_mutation']
            oldest_in_selection = recent_transactions[-1]['date_mutation']
            print(f"📊 Transaction la plus récente: {most_recent}")
            print(f"📅 Transaction la plus ancienne sélectionnée: {oldest_in_selection}")
        
        return recent_transactions
    
    def extract_relevant_data(self, transactions: List[Dict], analysis_type: str = "sale") -> List[Dict]:
        """
        Extrait les données pertinentes de chaque transaction
        
        Args:
            transactions: Liste des transactions
            analysis_type: "sale" pour ventes, "rental" pour estimation loyers
            
        Returns:
            Liste des données extraites avec valeur_fonciere, surface_relle_bati, nombre_pieces_principales
            et loyers estimés si analysis_type="rental"
        """
        extracted_data = []
        
        for transaction in transactions:
            valeur_fonciere = transaction.get('valeur_fonciere')
            surface_relle_bati = transaction.get('surface_relle_bati')
            nombre_pieces_principales = transaction.get('nombre_pieces_principales')
            date_mutation = transaction.get('date_mutation')
            voie = transaction.get('voie', '')
            commune = transaction.get('commune', '')
            nature_mutation = transaction.get('nature_mutation', '')
            
            # Ne garder que les transactions avec les données essentielles
            if (valeur_fonciere is not None and 
                surface_relle_bati is not None and 
                surface_relle_bati > 0 and
                valeur_fonciere > 0):
                
                prix_m2 = valeur_fonciere / surface_relle_bati
                
                # Calculer les loyers estimés si demandé
                loyer_5pct = loyer_6pct = loyer_m2_5pct = loyer_m2_6pct = None
                if analysis_type == "rental":
                    # Formule: Loyer mensuel = (Valeur foncière × Rendement) / (12 × 100)
                    loyer_5pct = round((valeur_fonciere * 5) / (12 * 100), 2)
                    loyer_6pct = round((valeur_fonciere * 6) / (12 * 100), 2)
                    loyer_m2_5pct = round(loyer_5pct / surface_relle_bati, 2)
                    loyer_m2_6pct = round(loyer_6pct / surface_relle_bati, 2)
                
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
                
                # Ajouter les données de location si demandé
                if analysis_type == "rental":
                    item_data.update({
                        'loyer_mensuel_5pct': loyer_5pct,
                        'loyer_mensuel_6pct': loyer_6pct,
                        'loyer_m2_5pct': loyer_m2_5pct,
                        'loyer_m2_6pct': loyer_m2_6pct
                    })
                
                extracted_data.append(item_data)
        
        return extracted_data
    
    def remove_outliers_iqr(self, data: List[Dict]) -> List[Dict]:
        """
        Supprime les outliers en utilisant la méthode IQR (Interquartile Range)
        Conserve seulement les données entre Q1 et Q3
        
        Args:
            data: Liste des données extraites
            
        Returns:
            Liste des données sans outliers
        """
        if len(data) < 4:  # Pas assez de données pour calculer les quartiles
            return data
        
        # Extraire les prix au m²
        prix_m2_list = [item['prix_m2'] for item in data]
        
        # Calculer Q1, Q3 et IQR (quartiles)
        q1 = statistics.quantiles(prix_m2_list, n=4)[0]  # 25e percentile
        q3 = statistics.quantiles(prix_m2_list, n=4)[2]  # 75e percentile
        iqr = q3 - q1
        
        # Utiliser la méthode IQR classique : Q1 - 1.5*IQR et Q3 + 1.5*IQR
        # Cela élimine les outliers plus efficacement
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # S'assurer que les limites restent raisonnables (pas de prix négatifs)
        lower_bound = max(lower_bound, 0)
        
        # Filtrer les données
        filtered_data = [
            item for item in data
            if lower_bound <= item['prix_m2'] <= upper_bound
        ]
        
        outliers_removed = len(data) - len(filtered_data)
        print(f"🗑️ Outliers supprimés: {outliers_removed} transactions")
        print(f"📊 Plage conservée: {lower_bound:.2f} - {upper_bound:.2f} €/m²")
        
        return filtered_data
    
    def calculate_statistics(self, data: List[Dict], analysis_type: str = "sale") -> Dict:
        """
        Calcule les statistiques sur les prix au m² ou loyers
        
        Args:
            data: Liste des données extraites
            analysis_type: "sale" pour ventes, "rental" pour loyers
            
        Returns:
            Dictionnaire avec les statistiques
        """
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
    
    def analyze_by_rooms(self, data: List[Dict]) -> Dict:
        """
        Analyse les prix par nombre de pièces
        
        Args:
            data: Liste des données extraites
            
        Returns:
            Dictionnaire avec les statistiques par nombre de pièces
        """
        rooms_data = {}
        
        for item in data:
            nb_pieces = item.get('nombre_pieces_principales')
            if nb_pieces is None:
                nb_pieces = 'Non renseigné'
            
            if nb_pieces not in rooms_data:
                rooms_data[nb_pieces] = []
            
            rooms_data[nb_pieces].append(item['prix_m2'])
        
        # Calculer les statistiques pour chaque nombre de pièces
        rooms_stats = {}
        for nb_pieces, prix_list in rooms_data.items():
            if prix_list:
                rooms_stats[nb_pieces] = {
                    'nb_transactions': len(prix_list),
                    'prix_m2_moyen': round(statistics.mean(prix_list), 2),
                    'prix_m2_median': round(statistics.median(prix_list), 2),
                    'prix_m2_min': min(prix_list),
                    'prix_m2_max': max(prix_list),
                }
        
        return rooms_stats
    
    def analyze_by_year(self, data: List[Dict]) -> Dict:
        """
        Analyse les prix par année
        
        Args:
            data: Liste des données extraites
            
        Returns:
            Dictionnaire avec les statistiques par année
        """
        years_data = {}
        
        for item in data:
            date_mutation = item.get('date_mutation')
            if date_mutation:
                year = date_mutation.split('-')[0]
                
                if year not in years_data:
                    years_data[year] = []
                
                years_data[year].append(item['prix_m2'])
        
        # Calculer les statistiques pour chaque année
        years_stats = {}
        for year, prix_list in years_data.items():
            if prix_list:
                years_stats[year] = {
                    'nb_transactions': len(prix_list),
                    'prix_m2_moyen': round(statistics.mean(prix_list), 2),
                    'prix_m2_median': round(statistics.median(prix_list), 2),
                    'prix_m2_min': min(prix_list),
                    'prix_m2_max': max(prix_list),
                }
        
        return years_stats
    
    def run_analysis(self, code_postal: str, max_results: int = 500, nb_pieces: Optional[int] = None, analysis_type: str = "sale") -> None:
        """
        Lance l'analyse complète pour un code postal donné
        
        Args:
            code_postal: Code postal à analyser
            max_results: Nombre maximum de transactions à analyser
            nb_pieces: Nombre de pièces à filtrer (optionnel)
            analysis_type: "sale" pour ventes, "rental" pour estimation loyers
        """
        pieces_filter = f" - {nb_pieces} pièces" if nb_pieces else ""
        type_analysis = "VENTES" if analysis_type == "sale" else "LOYERS ESTIMÉS"
        print(f"🏠 Analyse DVF {type_analysis} pour le code postal {code_postal}{pieces_filter}")
        print("=" * 60)
        
        # 1. Récupération des données
        print("📡 Récupération des données...")
        raw_data = self.fetch_data(code_postal)
        
        if not raw_data or 'resultats' not in raw_data:
            print("❌ Aucune donnée disponible")
            return
        
        total_results = raw_data.get('nb_resultats', 0)
        derniere_maj = raw_data.get('derniere_maj', 'Non renseigné')
        print(f"📊 {total_results} transactions trouvées au total")
        print(f"📅 Dernière mise à jour des données: {derniere_maj}")
        
        # 2. Filtrage sur les transactions récentes
        filter_text = f"{max_results} transactions les plus récentes"
        if nb_pieces:
            filter_text += f" avec {nb_pieces} pièces"
        print(f"\n🗓️ Filtrage sur les {filter_text}...")
        recent_data = self.filter_recent_transactions(raw_data['resultats'], max_results, nb_pieces)
        print(f"📅 {len(recent_data)} transactions finales sélectionnées")
        
        if not recent_data:
            print("❌ Aucune transaction récente trouvée")
            return
        
        # 3. Extraction des données pertinentes
        print(f"\n🔍 Extraction des données pertinentes ({type_analysis.lower()})...")
        extracted_data = self.extract_relevant_data(recent_data, analysis_type)
        print(f"✅ {len(extracted_data)} transactions avec données complètes")
        
        
        if not extracted_data:
            print("❌ Aucune transaction avec données complètes")
            return
        
        # 4. Suppression des outliers
        print("\n🧠 Suppression des outliers (méthode IQR)...")
        cleaned_data = self.remove_outliers_iqr(extracted_data)
        print(f"✅ {len(cleaned_data)} transactions après nettoyage")
        
        if not cleaned_data:
            print("❌ Aucune transaction après suppression des outliers")
            return
        
        # 5. Calcul des statistiques générales (sur données nettoyées)
        stats_title = "STATISTIQUES VENTES" if analysis_type == "sale" else "STATISTIQUES LOYERS ESTIMÉS"
        print(f"\n📈 {stats_title} (SANS OUTLIERS)")
        print("-" * 50)
        stats = self.calculate_statistics(cleaned_data, analysis_type)
        
        if analysis_type == "sale":
            for key, value in stats.items():
                label = {
                    'nb_transactions': 'Nombre de transactions',
                    'prix_m2_moyen': 'Prix moyen/m²',
                    'prix_m2_median': 'Prix médian/m²',
                    'prix_m2_min': 'Prix minimum/m²',
                    'prix_m2_max': 'Prix maximum/m²',
                    'prix_m2_ecart_type': 'Écart-type'
                }.get(key, key)
                
                if 'prix' in key and key != 'nb_transactions':
                    print(f"{label}: {value} €/m²")
                else:
                    print(f"{label}: {value}")
        else:  # rental
            print(f"Nombre de transactions: {stats['nb_transactions']}")
            print("\n💰 RENDEMENT 5% :")
            print(f"  Loyer moyen: {stats['loyer_5pct_moyen']} €/mois")
            print(f"  Loyer médian: {stats['loyer_5pct_median']} €/mois")
            print(f"  Loyer/m² moyen: {stats['loyer_m2_5pct_moyen']} €/m²/mois")
            print(f"  Loyer/m² médian: {stats['loyer_m2_5pct_median']} €/m²/mois")
            print(f"  Plage: {stats['loyer_5pct_min']} - {stats['loyer_5pct_max']} €/mois")
            if 'loyer_5pct_ecart_type' in stats:
                print(f"  Écart-type: {stats['loyer_5pct_ecart_type']} €/mois")
            
            print("\n💰 RENDEMENT 6% :")
            print(f"  Loyer moyen: {stats['loyer_6pct_moyen']} €/mois")
            print(f"  Loyer médian: {stats['loyer_6pct_median']} €/mois")
            print(f"  Loyer/m² moyen: {stats['loyer_m2_6pct_moyen']} €/m²/mois")
            print(f"  Loyer/m² médian: {stats['loyer_m2_6pct_median']} €/m²/mois")
            print(f"  Plage: {stats['loyer_6pct_min']} - {stats['loyer_6pct_max']} €/mois")
            if 'loyer_6pct_ecart_type' in stats:
                print(f"  Écart-type: {stats['loyer_6pct_ecart_type']} €/mois")
        
        # 6. Analyse par année (sur données nettoyées)
        print("\n📅 ANALYSE PAR ANNÉE (SANS OUTLIERS)")
        print("-" * 40)
        years_stats = self.analyze_by_year(cleaned_data)
        
        for year in sorted(years_stats.keys(), reverse=True):
            year_stats = years_stats[year]
            print(f"\n{year}:")
            for key, value in year_stats.items():
                label = {
                    'nb_transactions': '  • Transactions',
                    'prix_m2_moyen': '  • Prix moyen',
                    'prix_m2_median': '  • Prix médian',
                    'prix_m2_min': '  • Prix minimum',
                    'prix_m2_max': '  • Prix maximum'
                }.get(key, f"  • {key}")
                
                if 'prix' in key:
                    print(f"{label}: {value} €/m²")
                else:
                    print(f"{label}: {value}")
        
        # 7. Analyse par nombre de pièces (sur données nettoyées)
        print("\n🏘️ ANALYSE PAR NOMBRE DE PIÈCES (SANS OUTLIERS)")
        print("-" * 50)
        rooms_stats = self.analyze_by_rooms(cleaned_data)
        
        for nb_pieces, room_stats in sorted(rooms_stats.items()):
            print(f"\n{nb_pieces} pièce(s):")
            for key, value in room_stats.items():
                label = {
                    'nb_transactions': '  • Transactions',
                    'prix_m2_moyen': '  • Prix moyen',
                    'prix_m2_median': '  • Prix médian',
                    'prix_m2_min': '  • Prix minimum',
                    'prix_m2_max': '  • Prix maximum'
                }.get(key, f"  • {key}")
                
                if 'prix' in key:
                    print(f"{label}: {value} €/m²")
                else:
                    print(f"{label}: {value}")
        
        # 8. Affichage de quelques transactions récentes (données nettoyées)
        examples_title = "EXEMPLES DE VENTES" if analysis_type == "sale" else "EXEMPLES DE LOYERS ESTIMÉS"
        print(f"\n🏠 {examples_title} RÉCENTES (SANS OUTLIERS)")
        print("-" * 60)
        
        # Trier par date décroissante et prendre les 5 premières
        sorted_data = sorted(cleaned_data, 
                           key=lambda x: x['date_mutation'], 
                           reverse=True)[:5]
        
        for i, transaction in enumerate(sorted_data, 1):
            print(f"{i}. {transaction['date_mutation']} - {transaction['commune']}")
            print(f"   📍 {transaction['voie']}")
            
            if analysis_type == "sale":
                print(f"   💰 {transaction['valeur_fonciere']:,} € - {transaction['surface_relle_bati']} m² - {transaction['prix_m2']} €/m²")
            else:  # rental
                print(f"   💰 Valeur: {transaction['valeur_fonciere']:,} € - {transaction['surface_relle_bati']} m²")
                print(f"   🏠 Loyer 5%: {transaction['loyer_mensuel_5pct']} €/mois ({transaction['loyer_m2_5pct']} €/m²)")
                print(f"   🏠 Loyer 6%: {transaction['loyer_mensuel_6pct']} €/mois ({transaction['loyer_m2_6pct']} €/m²)")
            
            print(f"   🏷️ {transaction['nature_mutation']}", end="")
            if transaction['nombre_pieces_principales']:
                print(f" - {transaction['nombre_pieces_principales']} pièces")
            else:
                print()
            print()
        
        # 9. Comparaison avec/sans outliers
        print("\n📉 COMPARAISON AVEC/SANS OUTLIERS")
        print("-" * 40)
        original_stats = self.calculate_statistics(extracted_data)
        print(f"AVEC outliers    : {original_stats.get('nb_transactions', 0)} transactions - Prix moyen: {original_stats.get('prix_m2_moyen', 0)} €/m²")
        print(f"SANS outliers    : {stats.get('nb_transactions', 0)} transactions - Prix moyen: {stats.get('prix_m2_moyen', 0)} €/m²")
        print(f"Outliers supprimés: {original_stats.get('nb_transactions', 0) - stats.get('nb_transactions', 0)} transactions")
        print()


def main():
    """Fonction principale"""
    analyzer = DVFAnalyzer()
    
    # Configuration
    code_postal = "71100"  # Gennevilliers
    max_results = 20      # Nombre de transactions à analyser
    nb_pieces = None      # Nombre de pièces (None = tous, 1, 2, 3, 4, 5, etc.)
    analysis_type = "sale"  # "sale" pour ventes, "rental" pour loyers estimés
    
    # Lancer l'analyse
    analyzer.run_analysis(code_postal, max_results=max_results, nb_pieces=nb_pieces, analysis_type=analysis_type)
    
    # Exemples d'autres analyses possibles :
    # analyzer.run_analysis("92230", max_results=200, nb_pieces=2)  # Seulement les 2 pièces
    # analyzer.run_analysis("92230", max_results=100, nb_pieces=3)  # Seulement les 3 pièces


if __name__ == "__main__":
    main()