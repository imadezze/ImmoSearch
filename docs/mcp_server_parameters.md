# MCP Server Parameters Documentation

## Overview
This document lists all parameters and fields returned by the Leboncoin MCP server tools.

## MCP Tool Functions

### 1. `search_leboncoin_properties`
Searches Leboncoin for properties using Piloterr API.

**Input Parameters:**
- `location` (string, required): Location name (e.g., "le bourget", "paris", "marseille")
- `api_key` (string, optional): Piloterr API key (uses PILOTERR_API_KEY env var if not provided)

**Return Structure:**
```json
{
  "location": "string",
  "search_summary": {
    "total_results": "number",
    "ads_returned": "number"
  },
  "properties": [...],
  "returned_count": "number",
  "status": "success|error",
  "error": "string (if status=error)"
}
```

### 2. `search_and_save_leboncoin_properties`
Searches properties and saves results to JSON files.

**Input Parameters:**
- `location` (string, required): Location name
- `api_key` (string, optional): Piloterr API key

**Return Structure:**
```json
{
  "location": "string",
  "search_summary": {...},
  "files_saved": ["array of file paths"],
  "property_count": "number",
  "status": "success|error",
  "error": "string (if status=error)"
}
```

## Property Data Structure

Each property in the `properties` array contains:

### Basic Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `title` | string | Property title/description | "Appartement 2 pièces 36 m²" |
| `price` | string | Property price | "[786]" (needs cleaning) |
| `category` | string | Property category | "Locations", "Ventes immobilières" |
| `ad_type` | string | Type of advertisement | "offer" |
| `url` | string | Direct link to Leboncoin listing | "https://www.leboncoin.fr/ad/..." |

### Location Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `location` | string | Formatted location string | "Le Bourget (93350)" |
| `zipcode` | string | Postal code | "93350" |
| `district` | string | District/neighborhood | "Centre-ville" |
| `department_name` | string | Department name | "Seine-Saint-Denis" |
| `region_name` | string | Region name | "Ile-de-France" |

### Property Attributes
All attributes are stored in the `key_attributes` object:

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `furnished` | string | Furniture status | "Meublé", "Non meublé" |
| `rooms` | string | Total number of rooms | "1", "2", "3", "4" |
| `bedrooms` | string | Number of bedrooms | "1", "2", "3" |
| `surface` | string | Surface area in m² | "25", "45", "65" |
| `energy_rate` | string | Energy efficiency rating | "A", "B", "C", "D", "E", "F", "G" |
| `ges` | string | Greenhouse gas rating | "A", "B", "C", "D", "E", "F", "G" |
| `heating_type` | string | Type of heating | "Collectif", "Individuel" |
| `floor_number` | string | Floor number | "0", "1", "2", "3" |
| `charges_included` | string | Whether charges are included | "Oui", "Non" |
| `land_size` | string | Land size (if applicable) | "100", "200" |

### Media Information
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `images_count` | number | Number of images available | 6, 8, 12 |

## Search Summary Structure

| Field | Type | Description |
|-------|------|-------------|
| `total_results` | number | Total number of properties found |
| `ads_returned` | number | Number of ads returned in response |

## Configuration

### Environment Variables
- `PILOTERR_API_KEY`: Required API key for Piloterr service
- `MISTRAL_API_KEY`: Required for AI client interaction

### Limits
- **Property Limit**: Maximum 20 properties returned per search
- **API Timeout**: Standard HTTP timeout for Piloterr API calls

### File Output
When using `search_and_save_leboncoin_properties`:
- Files saved to `results/` directory
- Naming pattern: `raw_leboncoin_{location}.json` and `formatted_leboncoin_{location}.json`
- Location spaces replaced with underscores in filenames

## Data Quality Notes

### Known Issues
1. **Price Format**: Prices may contain brackets `[786]` that need cleaning
2. **Missing Data**: Some properties may have `"N/A"` for missing fields

### Data Sources
- **Primary Source**: Leboncoin.fr via Piloterr API
- **Real Estate Type**: Defaults to type `2` (real estate sales)
- **Location Encoding**: URLs are properly encoded for special characters

## Usage Examples

### Basic Search
```python
result = search_leboncoin_properties("le bourget")
```

### Search with Custom API Key
```python
result = search_leboncoin_properties("paris", api_key="your-key-here")
```

### Search and Save
```python
result = search_and_save_leboncoin_properties("marseille")
```