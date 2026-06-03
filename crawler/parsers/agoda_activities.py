"""Parse Agoda Activities listing + detail API responses."""


def safe(d, *keys, default=None):
    """Deep-dict access without KeyError."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d


def parse_autocomplete(body: dict) -> list[dict]:
    """Parse autocomplete API response -> list of {city_id, name, country}.

    Filter results to keep only cities (ObjectTypeID=17 or has CityId).
    """
    results = []
    for group in (safe(body, "SuggestionList", default=[]) or []):
        oid = group.get("ObjectID")
        otype = group.get("ObjectTypeID")
        name = group.get("Name", "")
        if otype in (17, 19):  # city / region
            results.append({"city_id": oid, "name": name, "object_type": otype})
    return results


def parse_activity_list(body: dict) -> list[dict]:
    """Parse activities GraphQL response -> list of basic activity records.

    Expected structure: data.search.result.activities[]
    Each activity has: masterActivityId, content.activity.{title,description},
                       content.reviewSummary, activityRepresentativeInfo.pricingSummary
    """
    acts = safe(body, "data", "search", "result", "activities", default=[]) or []
    out = []
    for a in acts:
        act = safe(a, "content", "activity", default={}) or {}
        pricing = safe(a, "activityRepresentativeInfo", "pricingSummary",
                       "pricing", default=[]) or []
        price = pricing[0] if pricing else None
        price_amount = None
        currency = "VND"
        if price:
            price_amount = safe(price, "display", "perBook", "total",
                                "allInclusive", "chargeTotal")
            currency = price.get("currency", "VND")

        location = safe(a, "content", "location", default={}) or {}
        lat = safe(location, "coordinates", "latitude")
        lng = safe(location, "coordinates", "longitude")

        images = safe(a, "content", "media", "images", default=[]) or []
        image_urls = []
        if isinstance(images, list):
            image_urls = [img.get("url") for img in images if img.get("url")]

        out.append({
            "activity_id": a.get("masterActivityId"),
            "title": act.get("title"),
            "description": safe(a, "content", "activity", "description", default=""),
            "price_amount": price_amount,
            "currency": currency,
            "review_score": safe(a, "content", "reviewSummary", "averageScore"),
            "review_count": safe(a, "content", "reviewSummary", "totalCount"),
            "duration": safe(a, "content", "activity", "duration"),
            "category": safe(a, "content", "activity", "category"),
            "images": image_urls,
            "latitude": lat,
            "longitude": lng,
            "includes": safe(a, "content", "activity", "includes", default=[]) or [],
            "highlights": safe(a, "content", "activity", "highlights", default=[]) or [],
        })
    return out


def parse_detail(body: dict) -> dict:
    """Parse activity detail API response -> enriched activity record.

    Returns fields beyond the listing: full description, itinerary,
    cancellation policy, provider info.
    """
    act = safe(body, "data", "activity", default={}) or {}
    detail = safe(act, "content", "activity", default={}) or {}

    location = safe(act, "content", "location", default={}) or {}
    lat = safe(location, "coordinates", "latitude")
    lng = safe(location, "coordinates", "longitude")

    images = safe(act, "content", "media", "images", default=[]) or []
    image_urls = []
    if isinstance(images, list):
        image_urls = [img.get("url") for img in images if img.get("url")]

    reviews = safe(act, "content", "reviewSummary", default={}) or {}
    pricing = safe(act, "activityRepresentativeInfo", "pricingSummary",
                   "pricing", default=[]) or []
    price = pricing[0] if pricing else None
    price_amount = None
    if price:
        price_amount = safe(price, "display", "perBook", "total",
                            "allInclusive", "chargeTotal")

    return {
        "activity_id": act.get("masterActivityId"),
        "title": detail.get("title"),
        "description": detail.get("description", ""),
        "price_amount": price_amount,
        "currency": price.get("currency", "VND") if price else "VND",
        "review_score": reviews.get("averageScore"),
        "review_count": reviews.get("totalCount"),
        "duration": detail.get("duration"),
        "category": detail.get("category"),
        "images": image_urls,
        "itinerary": safe(act, "content", "itinerary", default=[]) or [],
        "includes": detail.get("includes", []) or [],
        "highlights": detail.get("highlights", []) or [],
        "cancellation_policy": safe(act, "content", "cancellationPolicy"),
        "provider": safe(act, "content", "provider", "name"),
        "latitude": lat,
        "longitude": lng,
        "address": location.get("address"),
        "city": safe(location, "city", "name"),
        "province": safe(location, "state", "name"),
        "country": safe(location, "country", "name"),
    }
