import os
import urllib.parse
from typing import Iterable, Tuple, Union, Optional, List
import httpx
import dotenv
from flask import Flask, Response
import requests
import os
import logging
import re

app = Flask(__name__)
dotenv.load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
IMGBB = os.getenv("IMGBB_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
STATIC_MAPS_URL = "https://maps.googleapis.com/maps/api/staticmap"

Coord = Tuple[float, float]
Place = Union[str, Coord]  # address string OR (lat, lng)

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

def aggregated_maps_links(
    places: Iterable[Place],
    *,
    colors: Optional[List[str]] = None,   # e.g. ["red","#00FF00","blue"]
    labels: Optional[List[str]] = None,   # single letters "A".."Z" (Static Maps limitation)
):
    """
    Given addresses or coords, return ONE interactive Google Maps link (no custom colors)
    and ONE Static Map image URL (with colored markers).

    - `colors` and `labels` (optional) must have the same length as `places` if provided.
    - Static Maps supports named colors (red, blue, green, etc.) or hex without '#', e.g. "0x00FF00".
      It also supports one-letter labels (A–Z, 0–9).
    """
    coords: List[Coord] = []
    place_ids: List[str] = []

    places_list = list(places)
    n = len(places_list)
    if colors and len(colors) != n:
        raise ValueError("If provided, `colors` must match the length of `places`.")
    if labels and len(labels) != n:
        raise ValueError("If provided, `labels` must match the length of `places`.")

    # Normalize inputs → coords + place_ids
    for idx, p in enumerate(places_list):
        if isinstance(p, tuple) and len(p) == 2:
            lat, lng = float(p[0]), float(p[1])
            coords.append((lat, lng))
        elif isinstance(p, str):
            lat, lng, pid = geocode(p)
            coords.append((lat, lng))
            place_ids.append(pid)
        else:
            raise ValueError(f"Unsupported place: {p!r}")

    # --- Interactive link (cannot color markers via public URL)
    # Use directions-style link with waypoints if we have place_ids from geocoding;
    # otherwise fall back to a search link with coordinate query.
    if place_ids:
        dest = place_ids[0]
        waypoints = "|".join(f"place_id:{pid}" for pid in place_ids[1:])
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination=place_id:{dest}"
        if waypoints:
            maps_url += f"&waypoints={urllib.parse.quote(waypoints)}"
    else:
        q = "|".join(f"{lat},{lng}" for lat, lng in coords)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(q)}"

    # --- Static Map with colored markers
    static_url = None
    if GOOGLE_API_KEY:
        # Group markers by (color,label) → one `markers=` per group.
        # If no colors/labels provided, we put all into one group.
        groups: dict[Tuple[str, str], List[Coord]] = {}
        for i, (lat, lng) in enumerate(coords):
            color = colors[i] if colors else ""  # empty → default red
            # Static Maps expects hex as 0xRRGGBB or names like "blue"
            color = color.strip()
            if color.startswith("#"):
                color = "0x" + color[1:]
            label = (labels[i].strip()[:1].upper() if labels and labels[i] else "")
            key = (color, label)
            groups.setdefault(key, []).append((lat, lng))

        params = [("size", "640x400"), ("scale", "2"), ("key", GOOGLE_API_KEY)]
        for (color, label), pts in groups.items():
            style_parts = []
            if color:
                style_parts.append(f"color:{color}")
            if label:
                style_parts.append(f"label:{label}")
            # If no style parts, omit them → default style (red pin, no label).
            prefix = "|".join(style_parts) if style_parts else ""
            coords_part = "|".join(f"{lat},{lng}" for lat, lng in pts)
            if prefix:
                markers_val = f"{prefix}|{coords_part}"
            else:
                markers_val = coords_part
            params.append(("markers", markers_val))

        static_url = STATIC_MAPS_URL + "?" + urllib.parse.urlencode(params, doseq=True, safe=":,|")

    return {"maps_url": maps_url, "static_map": static_url}



def fetch_and_save_map(url, output_path="paris_landmarks_map.png"):
    # Replace with your actual API key or use environment variables
    # Define the Static Map URL with your landmarks

    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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


def floats_to_blue_red_hex(values):
    if not values:
        return []
    logging.info(values)
    vals = [float(v) for v in values]  # ensure numeric
    vmin, vmax = min(vals), max(vals)
    if vmin == vmax:
        return ["#800080"] * len(vals)
    out = []
    for v in vals:
        t = (v - vmin) / (vmax - vmin)
        r = int(255 * t)
        b = int(255 * (1 - t))
        out.append(f"#{r:02X}00{b:02X}")
    return out

def parse_price_to_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, list):  # <-- handle list of prices
        if x:
            return parse_price_to_float(x[0])
        return None
    if isinstance(x, str):
        s = x.strip()
        # Remove enclosing brackets like x"[840]"
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        s = s.replace("\xa0", " ")
        s = re.sub(r"[^\d.,\-]", "", s)
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


# --- Example ---
if __name__ == "__main__":
    places = [
        "Eiffel Tower, Paris",
        "Louvre Museum, Paris",
        (48.886705, 2.343104),  # Sacré-Cœur coords
    ]
    links = aggregated_maps_links(places, colors=["red", "#00FF00", "blue"],  # hex ok; will be converted to 0x00FF00
    labels=["E", "L", "S"])
    fetch_and_save_map(links["static_map"], "/tmp/static_map.png")
    print(upload_to_imgbb("/tmp/static_map.png"))