import streamlit as st
import pandas as pd
import requests
import time
import json
import html
import re
from pathlib import Path
from urllib.parse import quote_plus

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Property Triage",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# LOAD CSS FILE
# -----------------------------

#BASE_DIR = Path(__file__).resolve().parent

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

OLLAMA_URL = "http://localhost:11434/api/generate"
N8N_WEBHOOK = "http://localhost:5678/webhook-test/listing"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

CITY_CENTER_COORDINATES = {
    "Tel Aviv": (32.0853, 34.7818),
    "Jerusalem": (31.7683, 35.2137),
    "Haifa": (32.7940, 34.9896),
    "Beer Sheva": (31.2529, 34.7915),
    "Netanya": (32.3215, 34.8532),
    "Herzliya": (32.1663, 34.8433),
    "Ramat Gan": (32.0684, 34.8248),
    "Ashdod": (31.8044, 34.6553),
    "Rishon LeZion": (31.9730, 34.7925),
    "Modiin": (31.8980, 35.0104),
    "Caesarea": (32.5000, 34.9000),
    "Acre": (32.9236, 35.0725),
    "Nazareth": (32.6996, 35.3035),
    "Nahariya": (33.0059, 35.0941),
    "Afula": (32.6076, 35.2896),
    "Karmiel": (32.9199, 35.2901),
    "Kiryat Ata": (32.8115, 35.1132),
    "Majd al-Krum": (32.9216, 35.2567),
    "New York": (40.7128, -74.0060),
    "Miami": (25.7617, -80.1918),
}


def section_header(label, title, subtitle):
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="eyebrow">{label}</div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label, state="online"):
    st.markdown(
        f"""
        <div class="status-pill {state}">
            <span></span>
            <strong>{label}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_value(value, fallback="Not specified"):
    if value is None:
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    return str(value)


def escape_html(value):
    return html.escape(clean_value(value), quote=True)


def normalize_listing_result(result):
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0]
    if isinstance(result, dict):
        return result
    return None


def merge_location_context(listing, submitted_payload=None):
    context = {}
    if isinstance(submitted_payload, dict):
        context.update(submitted_payload)
    if isinstance(listing, dict):
        for key, value in listing.items():
            if value not in (None, "", []):
                context[key] = value
    return context


def safe_maps_url(url):
    if not isinstance(url, str):
        return ""
    url = url.strip()
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return ""


def city_center_coordinates(location_text):
    location_text = clean_value(location_text, "").lower()
    if not location_text:
        return None

    for city, coordinates in CITY_CENTER_COORDINATES.items():
        if city.lower() in location_text:
            return coordinates
    return None


def google_maps_search_url(location_text):
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(clean_value(location_text, ''))}"


def parse_number(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def normalize_search_listing(raw_listing):
    city = clean_value(raw_listing.get("city") or raw_listing.get("location"), "")
    latitude = raw_listing.get("latitude")
    longitude = raw_listing.get("longitude")
    return {
        "title": clean_value(raw_listing.get("title"), "Untitled listing"),
        "property_type": clean_value(raw_listing.get("property_type"), ""),
        "price": raw_listing.get("price"),
        "rooms": raw_listing.get("rooms"),
        "city": city,
        "neighborhood": clean_value(raw_listing.get("neighborhood"), ""),
        "address": clean_value(raw_listing.get("address"), ""),
        "latitude": latitude,
        "longitude": longitude,
        "image_url": clean_value(raw_listing.get("image_url"), ""),
        "description": clean_value(raw_listing.get("description"), ""),
        "location": clean_value(raw_listing.get("location") or city, ""),
        "listing_id": clean_value(raw_listing.get("listing_id"), raw_listing.get("title", "listing")),
    }


@st.cache_data
def load_property_search_listings():
    listing_files = [
        PROJECT_ROOT / "seed_data" / "property_listings.json",
        PROJECT_ROOT / "data" / "synthetic_listings" / "property_listings.json",
    ]
    listings = []
    seen = set()

    for listing_file in listing_files:
        if not listing_file.exists():
            continue
        with open(listing_file) as f:
            raw_listings = json.load(f)
        for raw_listing in raw_listings:
            listing = normalize_search_listing(raw_listing)
            dedupe_key = listing["listing_id"] or listing["title"]
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            listings.append(listing)

    return listings


def listing_matches_request(listing, request_text):
    if not request_text.strip():
        return True

    search_blob = " ".join(
        [
            listing.get("title", ""),
            listing.get("property_type", ""),
            listing.get("city", ""),
            listing.get("neighborhood", ""),
            listing.get("description", ""),
        ]
    ).lower()
    request_words = [
        word.strip(".,;:!?()[]").lower()
        for word in request_text.split()
        if len(word.strip(".,;:!?()[]")) > 2
    ]
    return any(word in search_blob for word in request_words)


def derive_search_filters_from_request(request_text, listings):
    request_lower = request_text.lower()
    derived = {
        "city": "",
        "property_type": "",
        "rooms": "",
    }

    cities = sorted({listing.get("city", "") for listing in listings if listing.get("city")}, key=len, reverse=True)
    property_types = sorted(
        {listing.get("property_type", "") for listing in listings if listing.get("property_type")},
        key=len,
        reverse=True,
    )

    for city in cities:
        if city.lower() in request_lower:
            derived["city"] = city
            break

    for property_type in property_types:
        if property_type.lower() in request_lower:
            derived["property_type"] = property_type
            break

    rooms_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(room|rooms|bedroom|bedrooms)", request_lower)
    if rooms_match:
        derived["rooms"] = rooms_match.group(1)

    return derived


def detect_location_from_description(description):
    description_lower = description.lower()
    known_cities = sorted(
        {listing.get("city", "") for listing in load_property_search_listings() if listing.get("city")},
        key=len,
        reverse=True,
    )

    for city in known_cities:
        if city.lower() in description_lower:
            return city

    city_state_match = re.search(
        r"\b(?:in|near|at)\s+([A-Z][A-Za-z .'-]+,\s*[A-Z]{2})\b",
        description,
    )
    if city_state_match:
        return city_state_match.group(1).strip()

    return ""


def search_property_listings(
    request_text,
    city,
    property_type,
    rooms,
    budget_min,
    budget_max,
    neighborhood,
):
    listings = load_property_search_listings()
    derived_filters = derive_search_filters_from_request(request_text, listings)
    requested_rooms = parse_number(rooms)
    if requested_rooms is None:
        requested_rooms = parse_number(derived_filters["rooms"])
    min_budget = parse_number(budget_min)
    max_budget = parse_number(budget_max)
    city_query = (city.strip() or derived_filters["city"]).lower()
    property_type_query = (property_type.strip() or derived_filters["property_type"]).lower()
    neighborhood_query = neighborhood.strip().lower()

    matches = []
    for listing in listings:
        listing_price = parse_number(listing.get("price"))
        listing_rooms = parse_number(listing.get("rooms"))
        listing_city = listing.get("city", "").lower()
        listing_neighborhood = listing.get("neighborhood", "").lower()
        listing_type = listing.get("property_type", "").lower()

        if city_query and city_query not in listing_city:
            continue
        if property_type_query and property_type_query not in listing_type:
            continue
        if neighborhood_query and neighborhood_query not in listing_neighborhood:
            continue
        if requested_rooms is not None and listing_rooms != requested_rooms:
            continue
        if min_budget is not None and listing_price is not None and listing_price < min_budget:
            continue
        if max_budget is not None and listing_price is not None and listing_price > max_budget:
            continue
        if not listing_matches_request(listing, request_text):
            continue

        matches.append(listing)

    return matches


def format_price(value):
    numeric_value = parse_number(value)
    if numeric_value is None:
        return clean_value(value)
    return f"{numeric_value:,.0f} ILS"


def has_listing_coordinates(listing):
    return listing.get("latitude") not in (None, "") and listing.get("longitude") not in (None, "")


def get_listing_images(listing):
    images = []
    if listing.get("image_url"):
        images.append(listing["image_url"])
    raw_images = listing.get("images") or listing.get("image_urls") or []
    if isinstance(raw_images, str):
        raw_images = [raw_images]
    for image_url in raw_images:
        if image_url and image_url not in images:
            images.append(image_url)
    return images


def score_listing_for_request(listing, request_text):
    listings = load_property_search_listings()
    derived = derive_search_filters_from_request(request_text, listings)
    score = 0
    request_lower = request_text.lower()
    listing_text = " ".join(
        [
            listing.get("title", ""),
            listing.get("property_type", ""),
            listing.get("city", ""),
            listing.get("neighborhood", ""),
            listing.get("description", ""),
            " ".join(listing.get("features") or []),
        ]
    ).lower()

    if derived["city"] and derived["city"].lower() == listing.get("city", "").lower():
        score += 40
    if derived["property_type"] and derived["property_type"].lower() == listing.get("property_type", "").lower():
        score += 30
    requested_rooms = parse_number(derived["rooms"])
    listing_rooms = parse_number(listing.get("rooms"))
    if requested_rooms is not None and listing_rooms is not None:
        score += max(0, 20 - int(abs(requested_rooms - listing_rooms) * 8))
    for word in request_lower.split():
        token = word.strip(".,;:!?()[]").lower()
        if len(token) > 2 and token in listing_text:
            score += 2

    return score


def recommend_property_for_request(request_text):
    listings = load_property_search_listings()
    if not listings:
        return None, []

    scored_listings = [
        (score_listing_for_request(listing, request_text), listing)
        for listing in listings
    ]
    scored_listings.sort(
        key=lambda item: (
            item[0],
            1 if has_listing_coordinates(item[1]) else 0,
            parse_number(item[1].get("price")) or 0,
        ),
        reverse=True,
    )
    recommendation_score, recommendation = scored_listings[0]
    if recommendation_score <= 0 and request_text.strip():
        return None, scored_listings
    return recommendation, scored_listings


def build_match_reasons(listing, request_text):
    reasons = []
    derived = derive_search_filters_from_request(request_text, load_property_search_listings())
    features = listing.get("features") or []

    if derived["city"] and derived["city"].lower() == listing.get("city", "").lower():
        reasons.append(f"Located in {listing['city']}, matching the requested city.")
    if derived["property_type"] and derived["property_type"].lower() == listing.get("property_type", "").lower():
        reasons.append(f"Property type matches the requested {listing['property_type']}.")
    if derived["rooms"] and parse_number(derived["rooms"]) == parse_number(listing.get("rooms")):
        reasons.append(f"Room count matches the requested {clean_value(listing.get('rooms'))}-room profile.")
    elif derived["rooms"]:
        reasons.append(f"Room count is close to the requested profile at {clean_value(listing.get('rooms'))} rooms.")
    if features:
        reasons.append(f"Includes attractive features such as {', '.join(features[:3])}.")
    if listing.get("description"):
        reasons.append("Description aligns with the client's stated search intent.")

    return reasons[:5] or ["This listing is the closest available match in the current property data."]


def render_recommended_property_report(listing, request_text, scored_listings=None):
    images = get_listing_images(listing)
    location_label = ", ".join(
        [part for part in [listing.get("neighborhood"), listing.get("city")] if part]
    ) or "Location not available"
    features = listing.get("features") or []
    match_reasons = build_match_reasons(listing, request_text)
    map_url = ""

    if has_listing_coordinates(listing):
        map_url = (
            "https://www.google.com/maps/search/?api=1&query="
            f"{listing['latitude']},{listing['longitude']}"
        )

    st.markdown(
        """
        <div class="report-header">
            <div>
                <div class="eyebrow">Recommended Property</div>
                <h2>Client Property Match</h2>
            </div>
            <div class="generated-badge"><span></span>Recommended</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        image_col, detail_col = st.columns([1.1, 1.9])
        with image_col:
            if images:
                st.image(images[0], width="stretch")
            else:
                st.markdown(
                    '<div class="recommendation-image-placeholder">Image not available</div>',
                    unsafe_allow_html=True,
                )

        with detail_col:
            st.markdown(
                f"""
                <div class="recommendation-hero-copy">
                    <div class="eyebrow">{escape_html(clean_value(listing.get("property_type"), "Property"))}</div>
                    <h2>{escape_html(listing.get("title"))}</h2>
                    <div class="listing-price">{escape_html(format_price(listing.get("price")))}</div>
                    <div class="search-result-meta">
                        <span>{escape_html(location_label)}</span>
                        <span>{escape_html(clean_value(listing.get("rooms")))} rooms</span>
                        <span>{escape_html(clean_value(listing.get("property_type")))}</span>
                    </div>
                    <p>{escape_html(listing.get("description"))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    facts = [
        ("Price", format_price(listing.get("price"))),
        ("Rooms", clean_value(listing.get("rooms"))),
        ("Location", location_label),
        ("Property Type", clean_value(listing.get("property_type"))),
        ("Availability / Condition", clean_value(listing.get("condition"))),
    ]
    fact_cols = st.columns(5)
    for column, (label, value) in zip(fact_cols, facts):
        with column:
            st.markdown(
                f"""
                <div class="fact-card">
                    <span>{label}</span>
                    <strong>{escape_html(value)}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Image Gallery")
    if images:
        gallery_cols = st.columns(min(3, len(images)))
        for index, image_url in enumerate(images[:3]):
            with gallery_cols[index]:
                with st.container(border=True):
                    st.image(image_url, width="stretch")
    else:
        st.markdown(
            '<div class="search-image-placeholder">No listing images are available for this property.</div>',
            unsafe_allow_html=True,
        )

    if features:
        chips = "".join(
            f'<span class="feature-chip">{escape_html(feature)}</span>'
            for feature in features
        )
        st.markdown(
            f"""
            <div class="report-section">
                <div class="section-title-row">
                    <div>
                        <div class="eyebrow">Key Features</div>
                        <h3>Property highlights</h3>
                    </div>
                </div>
                <div class="feature-chip-row">{chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    reason_cards = "".join(
        f"""
        <div class="selling-point-card">
            <strong>{index:02d}</strong>
            <p>{escape_html(reason)}</p>
        </div>
        """
        for index, reason in enumerate(match_reasons, start=1)
    )
    st.markdown(
        f"""
        <div class="report-section">
            <div class="section-title-row">
                <div>
                    <div class="eyebrow">Why This Match</div>
                    <h3>Why this property fits the client request</h3>
                </div>
            </div>
            <div class="selling-point-grid">{reason_cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            """
            <div class="map-section-heading">
                <div class="eyebrow">Property Location Map</div>
                <h3>Map location is shown only from coordinates stored with the matched listing.</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="map-location-label">{escape_html(clean_value(listing.get("address")) if listing.get("address") else location_label)}</div>',
            unsafe_allow_html=True,
        )
        if has_listing_coordinates(listing):
            map_df = pd.DataFrame(
                {
                    "lat": [float(listing["latitude"])],
                    "lon": [float(listing["longitude"])],
                }
            )
            st.map(map_df, zoom=14, height=320)
            st.link_button("View on Google Maps", map_url, width="content")
        elif listing.get("city") or listing.get("neighborhood"):
            st.info("Approximate location only. Exact coordinates are not available in the matched listing data.")
        else:
            st.info("Location not available.")

    with st.expander("Internal Analysis / Developer Details", expanded=False):
        st.markdown("#### Matched Listing Data")
        st.json(listing)
        if scored_listings is not None:
            st.markdown("#### Search Debug")
            st.json(
                [
                    {"score": score, "title": match.get("title"), "listing_id": match.get("listing_id")}
                    for score, match in scored_listings[:10]
                ]
            )


def render_image_preview_gallery(image_urls, title="Image Preview Gallery"):
    if not image_urls:
        return

    st.markdown(
        f"""
        <div class="report-section">
            <div class="section-title-row">
                <div>
                    <div class="eyebrow">Visual Assets</div>
                    <h3>{escape_html(title)}</h3>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for start in range(0, min(len(image_urls), 6), 3):
        row_urls = image_urls[start:start + 3]
        gallery_cols = st.columns(len(row_urls))
        for column, image_url in zip(gallery_cols, row_urls):
            with column:
                with st.container(border=True):
                    st.image(image_url, width="stretch")


def build_listing_markdown(listing):
    title = clean_value(listing.get("listing_title"), "Property Listing")
    property_type = clean_value(listing.get("property_type"))
    location = clean_value(listing.get("location"))
    price = clean_value(listing.get("price"))
    rooms = clean_value(listing.get("rooms"))
    condition = clean_value(listing.get("condition_summary"))
    marketing_description = clean_value(listing.get("marketing_description"), "")
    features = listing.get("key_features") or []
    selling_points = listing.get("selling_points") or []
    brief = listing.get("listing_brief_markdown") or ""

    lines = [
        f"# {title}",
        "",
        f"**Price:** {price}",
        f"**Location:** {location}",
        f"**Property Type:** {property_type}",
        f"**Rooms / Bedrooms:** {rooms}",
        f"**Condition:** {condition}",
        "",
        "## Marketing Description",
        marketing_description,
    ]

    if features:
        lines.extend(["", "## Key Features"])
        lines.extend([f"- {clean_value(feature)}" for feature in features])

    if selling_points:
        lines.extend(["", "## Selling Points"])
        lines.extend([f"- {clean_value(point)}" for point in selling_points])

    if brief:
        lines.extend(["", "## Formatted Listing Brief", str(brief)])

    return "\n".join(lines).strip()


def condition_review_label(score):
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        return "Verification recommended"

    if numeric_score >= 4:
        return "Market-ready"
    if numeric_score >= 3:
        return "Minor review recommended"
    return "Verification recommended"


def render_property_location_map(result):
    address = clean_value(result.get("address"), "")
    city = clean_value(result.get("city"), "")
    state = clean_value(result.get("state"), "")
    country = clean_value(result.get("country"), "")
    location = clean_value(result.get("location"), "")
    lat = result.get("latitude")
    lon = result.get("longitude")
    maps_link = safe_maps_url(result.get("maps_link", ""))
    show_exact = result.get("show_exact_location", True)

    approximate_location = ", ".join([value for value in [city, state, country] if value])
    display_location = address if address and show_exact else location or approximate_location
    has_coordinates = lat not in (None, "") and lon not in (None, "")
    city_coordinates = city_center_coordinates(display_location or approximate_location or location)

    with st.container(border=True):
        st.markdown(
            """
            <div class="map-section-heading">
                <div class="eyebrow">Property Location</div>
                <h3>Explore the property's surrounding area and neighborhood context.</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if display_location:
            st.markdown(
                f'<div class="map-location-label">{escape_html(display_location)}</div>',
                unsafe_allow_html=True,
            )
        elif has_coordinates and show_exact:
            st.markdown(
                '<div class="map-location-label">Exact property pin provided</div>',
                unsafe_allow_html=True,
            )
        elif maps_link and show_exact:
            st.markdown(
                '<div class="map-location-label">Google Maps location provided</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Location not provided.")
            return

        if has_coordinates and show_exact:
            try:
                map_df = pd.DataFrame({"lat": [float(lat)], "lon": [float(lon)]})
            except (TypeError, ValueError):
                st.info("Location map is not available because the provided coordinates are invalid.")
                return

            st.map(map_df, zoom=14, height=320)
            google_maps_url = maps_link or f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            st.link_button("View on Google Maps", google_maps_url, width="content")
        elif maps_link and show_exact:
            st.link_button("View on Google Maps", maps_link, width="content")
        elif city_coordinates and display_location:
            map_df = pd.DataFrame(
                {
                    "lat": [city_coordinates[0]],
                    "lon": [city_coordinates[1]],
                }
            )
            st.map(map_df, zoom=11, height=280)
            st.info("Approximate location shown. Exact apartment address was not provided.")
            st.link_button("View on Google Maps", google_maps_search_url(display_location), width="content")
        elif approximate_location or location:
            st.info("Approximate location shown. Exact property address was not provided.")
            st.link_button("View on Google Maps", google_maps_search_url(display_location), width="content")
        else:
            st.info("Location map is not available because no address or coordinates were provided.")


def render_internal_details(result, listing=None, submitted_payload=None, location_metadata=None):
    with st.expander("Internal Analysis / Developer Details", expanded=False):
        if listing:
            st.markdown("#### Image Summary")
            st.write(listing.get("image_summary", "Not provided."))

            st.markdown("#### Average Condition Score")
            st.write(listing.get("average_condition_score", "Not provided."))

        st.markdown("#### Raw JSON")
        if isinstance(result, (dict, list)):
            st.json(result)
        else:
            st.write(result)

        if submitted_payload is not None:
            st.markdown("#### Submitted Payload")
            st.json(submitted_payload)

        if location_metadata is not None:
            st.markdown("#### Location Metadata")
            st.json(location_metadata)

        st.markdown("#### Model Response")
        st.write(result)


def render_enterprise_listing_report(result, submitted_payload=None, location_metadata=None):
    listing = normalize_listing_result(result)

    if not listing:
        st.info("The pipeline response is available for internal review.")
        render_internal_details(
            result,
            submitted_payload=submitted_payload,
            location_metadata=location_metadata,
        )
        return

    location_context = merge_location_context(listing, location_metadata)
    submitted_images = []
    if isinstance(submitted_payload, dict):
        raw_submitted_images = submitted_payload.get("image_urls") or []
        if isinstance(raw_submitted_images, str):
            raw_submitted_images = [raw_submitted_images]
        submitted_images = [image_url for image_url in raw_submitted_images if image_url]

    title = escape_html(listing.get("listing_title") or "Property Listing")
    property_type = escape_html(listing.get("property_type"))
    location = escape_html(listing.get("location") or location_context.get("location"))
    price = escape_html(listing.get("price"))
    rooms = escape_html(listing.get("rooms"))
    condition = escape_html(listing.get("condition_summary"))
    marketing_description = escape_html(listing.get("marketing_description"))
    features = listing.get("key_features") or []
    selling_points = listing.get("selling_points") or []
    listing_brief = listing.get("listing_brief_markdown")
    listing_markdown = build_listing_markdown(listing)
    condition_review = escape_html(condition_review_label(listing.get("average_condition_score")))

    st.markdown(
        """
        <div class="report-header">
            <div>
                <div class="eyebrow">Client-ready listing analysis</div>
                <h2>Property Intelligence Report</h2>
            </div>
            <div class="generated-badge"><span></span>Generated</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="enterprise-hero-card">
            <div class="enterprise-hero-content">
                <div class="eyebrow">Luxury Listing Overview</div>
                <div class="listing-hero-topline">
                    <h2>{title}</h2>
                    <span class="condition-badge">{condition}</span>
                </div>
                <div class="listing-hero-meta">
                    <span>{location}</span>
                    <span>{property_type}</span>
                    <span>{rooms}</span>
                </div>
                <div class="listing-price">{price}</div>
                <div class="client-note">Additional image verification may be recommended before final publication.</div>
            </div>
            <div class="hero-side-panel">
                <span>Condition Review</span>
                <strong>{condition_review}</strong>
                <p>Client-safe quality guidance based on the returned listing analysis.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([1.1, 2.2, 1.2, 2.5])
    with btn_cols[0]:
        if st.button("Copy Listing", key="copy_listing", width="content"):
            st.toast("Listing text is ready in the exported markdown.")
    with btn_cols[1]:
        if st.button("Copy Marketing Description", key="copy_marketing_description", width="content"):
            st.toast("Marketing description is shown in the Executive Summary.")
    with btn_cols[2]:
        st.download_button(
            "Export Markdown",
            data=listing_markdown,
            file_name="property-intelligence-report.md",
            mime="text/markdown",
            width="content",
        )

    facts = [
        ("Price", price),
        ("Location", location),
        ("Property Type", property_type),
        ("Rooms / Bedrooms", rooms),
        ("Condition", condition),
    ]
    fact_cols = st.columns(5)
    for column, (label, value) in zip(fact_cols, facts):
        with column:
            st.markdown(
                f"""
                <div class="fact-card">
                    <span>{label}</span>
                    <strong>{value}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_image_preview_gallery(submitted_images, title="Image Gallery")

    render_property_location_map(location_context)

    st.markdown(
        f"""
        <div class="report-section executive-summary">
            <div class="section-title-row">
                <div>
                    <div class="eyebrow">Executive Summary</div>
                    <h3>Client-facing marketing narrative</h3>
                </div>
            </div>
            <p>{marketing_description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if features:
        chips = "".join(
            f'<span class="feature-chip">{escape_html(feature)}</span>'
            for feature in features
        )
        st.markdown(
            f"""
            <div class="report-section">
                <div class="section-title-row">
                    <div>
                        <div class="eyebrow">Key Features</div>
                        <h3>Listing highlights</h3>
                    </div>
                </div>
                <div class="feature-chip-row">{chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if selling_points:
        point_cards = "".join(
            f"""
            <div class="selling-point-card">
                <strong>{index:02d}</strong>
                <p>{escape_html(point)}</p>
            </div>
            """
            for index, point in enumerate(selling_points, start=1)
        )
        st.markdown(
            f"""
            <div class="report-section">
                <div class="section-title-row">
                    <div>
                        <div class="eyebrow">Selling Points</div>
                        <h3>Broker-ready value drivers</h3>
                    </div>
                </div>
                <div class="selling-point-grid">{point_cards}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if listing_brief:
        with st.expander("Formatted Listing Brief", expanded=False):
            st.markdown(str(listing_brief))

    render_internal_details(
        result,
        listing=listing,
        submitted_payload=submitted_payload,
        location_metadata=location_metadata,
    )


def render_ai_property_workspace():
    with st.sidebar:
        st.markdown('<div class="sidebar-kicker">AI Property Triage</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-brand">Real Estate Intelligence Workspace</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sidebar-panel">
                <p class="sidebar-copy">Prepare polished listing intelligence reports from property dossiers, visual assets, and the existing publishing pipeline.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        status_pill("Webhook workflow ready")
        status_pill("Assistant local model endpoint")

    st.markdown(
        """
        <div class="hero-header">
            <div>
                <div class="eyebrow">Professional AI Property Workspace</div>
                <h1>AI Property Intelligence</h1>
                <p>Paste a listing dossier or client request, add image links if available, and generate a clean client-facing real estate report.</p>
            </div>
            <div class="hero-badge">
                <span>Client Report</span>
                <strong>Premium UI</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    report_tab, assistant_tab = st.tabs(
        ["Listing Intelligence Report", "Real Estate Intelligence Assistant"]
    )

    with report_tab:
        section_header(
            "Intake",
            "Listing Dossier",
            "Keep the workflow simple: broker identity, property description, optional visual assets, then generate the client report.",
        )

        agent_name = st.text_input(
            "Agent / Broker Identity",
            placeholder="e.g. Mohammed Sgier, Premium Property Advisory",
            key="agent_identity",
        )

        description = st.text_area(
            "Listing Dossier Description",
            placeholder="Paste the property description, listing notes, or client request here. Example: I want a 3-room apartment in Tel Aviv.",
            height=190,
            key="listing_dossier_description",
        )

        detected_location = detect_location_from_description(description) if description else ""
        st.markdown(
            f"""
            <div class="location-intake-card">
                <div>
                    <div class="eyebrow">Property Location</div>
                    <p>We'll use the city/state detected from the listing description. Exact map pins are shown only when real listing data includes address and coordinates.</p>
                </div>
                <strong>Detected location: {escape_html(detected_location or "Not detected yet")}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        image_urls_text = st.text_area(
            "Visual Asset URLs, one per line",
            placeholder="https://example.com/kitchen.jpg\nhttps://example.com/living-room.jpg",
            height=120,
            key="visual_asset_urls",
        )
        image_urls = [
            line.strip()
            for line in image_urls_text.splitlines()
            if line.strip()
        ]

        if image_urls:
            render_image_preview_gallery(image_urls)

        if st.button("Generate / Publish Report", key="btn_submission", width="content"):
            if not description.strip():
                st.error("Please add a listing dossier description before generating the report.")
                return

            payload = {
                "agent_name": agent_name,
                "description": description,
                "image_urls": image_urls,
            }
            location_metadata = {
                "location": detected_location,
                "show_exact_location": True,
            }

            progress = st.progress(0)
            with st.spinner("Generating client-facing property intelligence report..."):
                for step in range(1, 4):
                    time.sleep(0.2)
                    progress.progress(step / 4)

                try:
                    response = requests.post(N8N_WEBHOOK, json=payload, timeout=60)
                except requests.RequestException as exc:
                    progress.empty()
                    st.error("The publishing workflow could not be reached. Details are available for internal review.")
                    with st.expander("Internal Analysis / Developer Details", expanded=False):
                        st.write(str(exc))
                        st.json(payload)
                    return

                progress.progress(1.0)
                progress.empty()

            if response.status_code >= 400:
                st.error("The publishing workflow returned an error. Details are available for internal review.")
                with st.expander("Internal Analysis / Developer Details", expanded=False):
                    st.write(response.text)
                    st.json(payload)
                return

            try:
                result = response.json()
            except ValueError:
                result = response.text

            st.session_state["last_listing_result"] = result
            st.session_state["last_listing_payload"] = payload
            st.session_state["last_location_metadata"] = location_metadata

        result = st.session_state.get("last_listing_result")
        if result is not None:
            render_enterprise_listing_report(
                result,
                submitted_payload=st.session_state.get("last_listing_payload"),
                location_metadata=st.session_state.get("last_location_metadata"),
            )
        else:
            st.info("Generate a report to see the professional client-facing output here.")

    with assistant_tab:
        section_header(
            "Assistant",
            "Real Estate Intelligence Assistant",
            "Ask follow-up questions about positioning, client messaging, valuation concerns, or listing presentation.",
        )

        user_question = st.text_area(
            "Ask the assistant",
            placeholder="How should I position this property for an investor client?",
            height=140,
            key="assistant_question",
        )

        if st.button("Ask Assistant", key="btn_chatbot", width="content"):
            if not user_question.strip():
                st.error("Please enter a question for the assistant.")
                return

            assistant_payload = {
                "model": "llama3.1",
                "prompt": user_question,
                "stream": False,
            }

            with st.spinner("Preparing assistant response..."):
                try:
                    response = requests.post(OLLAMA_URL, json=assistant_payload, timeout=90)
                except requests.RequestException as exc:
                    st.error("The assistant endpoint could not be reached. Details are available for internal review.")
                    with st.expander("Internal Analysis / Developer Details", expanded=False):
                        st.write(str(exc))
                    return

            if response.status_code >= 400:
                st.error("The assistant returned an error. Details are available for internal review.")
                with st.expander("Internal Analysis / Developer Details", expanded=False):
                    st.write(response.text)
                return

            try:
                assistant_result = response.json()
            except ValueError:
                assistant_result = {"response": response.text}

            answer = clean_value(assistant_result.get("response"), "No assistant response was returned.")
            st.markdown(
                f"""
                <div class="report-section executive-summary">
                    <div class="section-title-row">
                        <div>
                            <div class="eyebrow">Assistant Response</div>
                            <h3>Real estate intelligence guidance</h3>
                        </div>
                    </div>
                    <p>{escape_html(answer)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Internal Analysis / Developer Details", expanded=False):
                st.json(assistant_result)


render_ai_property_workspace()
