import os
import urllib.parse
from typing import Iterable, Tuple
import httpx
import dotenv
from flask import Flask, Response
import requests
import os
import logging

app = Flask(__name__)
dotenv.load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
IMGBB = os.getenv("IMGBB_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"

Coord = Tuple[float, float]

def geocode(address: str) -> Tuple[float, float, str]:
    """Forward-geocode address → (lat,lng,place_id)."""
    params = {"address": address, "key": GOOGLE_API_KEY}
    r = httpx.get(GEOCODE_URL, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocode failed for {address}: {data.get('status')}")
    loc = data["results"][0]["geometry"]["location"]
    place_id = data["results"][0]["place_id"]
    return float(loc["lat"]), float(loc["lng"]), place_id

def aggregated_maps_links(places: Iterable[str | Coord]):
    """
    Given addresses or coords, return one Google Maps link
    (interactive) and one Static Map URL (image with markers).
    """
    coords, place_ids = [], []

    for p in places:
        if isinstance(p, tuple) and len(p) == 2:
            coords.append((float(p[0]), float(p[1])))
        elif isinstance(p, str):
            lat, lng, pid = geocode(p)
            coords.append((lat, lng))
            place_ids.append(pid)
        else:
            raise ValueError(f"Unsupported place: {p}")

    # Interactive Maps link with directions-style layout
    if place_ids:
        # first = destination, rest = waypoints
        dest = place_ids[0]
        waypoints = "|".join(f"place_id:{pid}" for pid in place_ids[1:])
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination=place_id:{dest}"
        if waypoints:
            maps_url += f"&waypoints={urllib.parse.quote(waypoints)}"
    else:
        # fallback to plain query with lat,lng
        q = "|".join(f"{lat},{lng}" for lat, lng in coords)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(q)}"

    # Static Maps (image with all markers)
    if GOOGLE_API_KEY:
        markers_param = "|".join(f"{lat},{lng}" for lat, lng in coords)
        static_url = (
            STATIC_MAPS_URL
            + "?"
            + urllib.parse.urlencode(
                {"size": "640x400", "scale": "2", "markers": markers_param, "key": GOOGLE_API_KEY},
                safe=":,|"
            )
        )
    else:
        static_url = None

    return {"maps_url": maps_url, "static_map": static_url}


def fetch_and_save_map(url, output_path="paris_landmarks_map.png"):
    # Replace with your actual API key or use environment variables
    # Define the Static Map URL with your landmarks

    # Fetch the image from Google Maps
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Save the image as a PNG file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Map saved as {output_path}")
    else:
        logging.info(f"Failed to fetch map. Status code: {response.status_code}")

# Call the function to save the map

def upload_to_imgbb(image_path: str) -> str:
    """
    Uploads an image to ImgBB and returns the public image URL.

    Args:
        api_key (str): Your ImgBB API key.
        image_path (str): Path to the image file.

    Returns:
        str: Public URL of the uploaded image.

    Raises:
        RuntimeError: If the upload fails.
    """
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB},
            files={"image": f}
        )

    data = response.json()
    if response.status_code == 200 and data.get("success"):
        logging.info(f"Uploaded map to ImgBB: {data['data']['url']}")
        return data["data"]["url"]
    else:
        raise RuntimeError(f"Upload failed: {data}")


# --- Example ---
if __name__ == "__main__":
    places = [
        "Eiffel Tower, Paris",
        "Louvre Museum, Paris",
        (48.886705, 2.343104),  # Sacré-Cœur coords
    ]
    links = aggregated_maps_links(places)
    fetch_and_save_map(links["static_map"], "../tmp/static_map.png")
    print(upload_to_imgbb("../tmp/static_map.png"))