import os
import json
from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import NotFoundError

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
RUNTIME_INDEX_NAME = os.environ.get('BM25_INDEX', 'vsf_hotels_bm25_current')
TARGET_INDEX_NAME = os.environ.get('BM25_TARGET_INDEX') or RUNTIME_INDEX_NAME
BM25_ALIAS = os.environ.get('BM25_ALIAS', RUNTIME_INDEX_NAME)
BM25_PROMOTE_ALIAS = os.environ.get('BM25_PROMOTE_ALIAS', 'false').lower() in ('1', 'true', 'yes', 'y')
DATA_DIR = os.environ.get('CLEANED_DATA_DIR', 'data/cleaned')
BULK_CHUNK_SIZE = int(os.environ.get('BULK_CHUNK_SIZE', '50'))
BULK_MAX_CHUNK_BYTES = int(os.environ.get('BULK_MAX_CHUNK_BYTES', str(5 * 1024 * 1024)))

client = OpenSearch(OPENSEARCH_URL)


def parse_price(price_str):
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    price_str = price_str.strip()
    if any(c in price_str for c in ['₫', 'đ', 'VND', '\u20ab']):
        # VND price, dot is thousands separator, keep only digits
        val_str = "".join([c for c in price_str if c.isdigit()])
        try:
            return float(val_str)
        except ValueError:
            return None
    else:
        # Standard float representation
        clean_str = "".join([c for c in price_str if c.isdigit() or c in ('.', ',')])
        if not clean_str:
            return None
        if ',' in clean_str and '.' not in clean_str:
            clean_str = clean_str.replace(',', '.')
        try:
            return float(clean_str)
        except ValueError:
            val_str = "".join([c for c in clean_str if c.isdigit()])
            try:
                return float(val_str)
            except ValueError:
                return None


def iter_docs(data_dir, index_name=TARGET_INDEX_NAME):
    for fname in os.listdir(data_dir):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(data_dir, fname)
        with open(path, 'r', encoding='utf-8') as f:
            try:
                doc = json.load(f)
            except Exception:
                continue

            hotel_id = doc.get('hotel_id')
            if not hotel_id:
                continue

            # Process nested rooms
            rooms = []
            for r in doc.get('rooms', []):
                rooms.append({
                    "hotel_id": hotel_id,
                    "room_type_id": r.get('room_type_id'),
                    "name": r.get('name'),
                    "price": parse_price(r.get('price')),
                    "room_size": r.get('room_size'),
                    "max_occupancy": r.get('max_occupancy'),
                    "bed_type": r.get('bed_type'),
                    "room_view": r.get('room_view'),
                    "room_amenities": ", ".join(r.get('room_amenities', [])) if isinstance(r.get('room_amenities'), list) else r.get('room_amenities'),
                    "images": r.get('image_urls', r.get('images', [])),
                    "review_score": r.get('review_score'),
                })

            # Process nested nearby_places
            nearby_places = []
            for p in doc.get('nearby_places', []):
                nearby_places.append({
                    "hotel_id": hotel_id,
                    "name": p.get('name'),
                    "type": p.get('type'),
                    "distance_km": p.get('distance_km'),
                })

            # Process nested activities
            activities = []
            for a in doc.get('activities', []):
                activities.append({
                    "hotel_id": hotel_id,
                    "title": a.get('title'),
                    "description": a.get('description'),
                    "price_amount": parse_price(a.get('price_amount')),
                    "review_score": a.get('review_score'),
                })

            # Map amenities as joined string or list
            amenities = doc.get('amenities')
            if isinstance(amenities, list):
                amenities = ", ".join(amenities)

            # Map suitable_for
            suitable_for = doc.get('suitable_for')
            if isinstance(suitable_for, list):
                suitable_for = ", ".join(suitable_for)

            # Construct index doc conforming strictly to index_mapping.json
            index_doc = {
                "_op_type": "index",
                "_index": index_name,
                "_id": str(hotel_id),
                "id": hotel_id,
                "name": doc.get('name'),
                "accommodation_type": doc.get('accommodation_type'),
                "star_rating": doc.get('star_rating'),
                "is_luxury": doc.get('is_luxury'),
                "review_score": doc.get('review_score'),
                "review_count": doc.get('review_count'),
                "address": doc.get('address'),
                "city": doc.get('city'),
                "latitude": doc.get('latitude'),
                "longitude": doc.get('longitude'),
                "description": doc.get('description'),
                "amenities": amenities,
                "useful_info": doc.get('useful_info', {}),
                "policyNotes": ", ".join(doc.get('policyNotes', [])) if isinstance(doc.get('policyNotes'), list) else doc.get('policyNotes'),
                "suitable_for": suitable_for,
                "reviews_detail": doc.get('reviews_detail', {}),
                "images": doc.get('image_urls', []),
                "source_url": doc.get('source_url'),
                "crawled_at": doc.get('crawled_at'),
                "rooms": rooms,
                "nearby_places": nearby_places,
                "activities": activities,
            }
            yield index_doc


def promote_alias(opensearch_client, alias_name, target_index):
    """Atomically point the stable BM25 alias to a validated versioned index."""
    try:
        existing_aliases = opensearch_client.indices.get_alias(name=alias_name)
        existing_indices = list(existing_aliases.keys())
    except NotFoundError:
        existing_indices = []

    actions = [
        {"remove": {"index": index_name, "alias": alias_name}}
        for index_name in existing_indices
    ]
    actions.append({"add": {"index": target_index, "alias": alias_name}})

    opensearch_client.indices.update_aliases(
        body={"actions": actions}
    )


def run_indexing(opensearch_client=client):
    # ensure index exists
    if not opensearch_client.indices.exists(index=TARGET_INDEX_NAME):
        print(f"Index {TARGET_INDEX_NAME} does not exist. Please create it with the agreed mapping before running this script.")
        return 1

    print(f"Runtime BM25 index/alias: {RUNTIME_INDEX_NAME}")
    print(f"Target BM25 index: {TARGET_INDEX_NAME}")
    print(f"Alias promotion: {BM25_PROMOTE_ALIAS} ({BM25_ALIAS} -> {TARGET_INDEX_NAME})")
    print(f"Indexing documents from {DATA_DIR} into {TARGET_INDEX_NAME}...")
    print(f"Bulk chunk size: {BULK_CHUNK_SIZE}, max chunk bytes: {BULK_MAX_CHUNK_BYTES}")
    try:
        success = 0
        failed = 0
        first_failures = []

        for ok, item in helpers.streaming_bulk(
            opensearch_client,
            iter_docs(DATA_DIR, TARGET_INDEX_NAME),
            chunk_size=BULK_CHUNK_SIZE,
            max_chunk_bytes=BULK_MAX_CHUNK_BYTES,
            raise_on_error=False,
            raise_on_exception=False,
        ):
            if ok:
                success += 1
            else:
                failed += 1
                if len(first_failures) < 3:
                    first_failures.append(item)

        print(f"Indexed: {success} successfully. Failed: {failed}")
        if first_failures:
            print("First few failure errors:")
            for item in first_failures:
                print(json.dumps(item, indent=2, ensure_ascii=True))
        if BM25_PROMOTE_ALIAS and failed == 0:
            promote_alias(opensearch_client, BM25_ALIAS, TARGET_INDEX_NAME)
            print(f"Promoted alias {BM25_ALIAS} -> {TARGET_INDEX_NAME}")
        elif BM25_PROMOTE_ALIAS:
            print(f"Skipped alias promotion because {failed} documents failed.")
    except Exception as e:
        print("Bulk indexing exception:", e)
        return 1
    print("Done.")
    return 0


if __name__ == '__main__':
    raise SystemExit(run_indexing())
