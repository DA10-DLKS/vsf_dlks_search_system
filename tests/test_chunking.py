from knowledge_engineering.chunking import ChunkingConfig, chunk_cms, chunk_document, chunk_hotel, chunk_reviews


def test_hotel_chunking_routes_fields_and_adds_context_prefix():
    hotel = {
        "hotel_id": 1,
        "name": "Khach san Bien Xanh",
        "city": "Da Nang",
        "star_rating": 5,
        "description_short": "Gan bien, phu hop cap doi.",
        "description": "Cau mot ve khach san. Cau hai ve ho boi. Cau ba ve spa.",
        "faq": [{"question": "Co ho boi khong?", "answer": "Co ho boi ngoai troi.", "category": "amenity"}],
    }

    chunks = chunk_hotel(hotel, ChunkingConfig(child_token_target=5, child_token_overlap=0))

    assert {chunk.metadata["section"] for chunk in chunks} >= {"overview", "description", "faq"}
    assert all(chunk.text.startswith("Khach san Bien Xanh") for chunk in chunks)
    assert all(chunk.metadata["city"] == "Da Nang" for chunk in chunks)
    assert any(chunk.strategy == "recursive_sentence" for chunk in chunks)


def test_review_chunking_is_atomic_and_deduplicates_exact_text():
    reviews = {
        "hotel_id": 1,
        "hotel_name": "Khach san Bien Xanh",
        "reviews": [
            {"review_id": "a", "rating": 10, "title": "Tot", "text": "Phong sach.", "reviewer_type": "Couple"},
            {"review_id": "b", "rating": 10, "title": "Tot", "text": "Phong sach.", "reviewer_type": "Couple"},
        ],
    }

    chunks = chunk_reviews(reviews)

    assert len(chunks) == 1
    assert chunks[0].strategy == "atomic"
    assert chunks[0].metadata["guest_type"] == "Couple"


def test_cms_chunking_uses_heading_breadcrumbs():
    document = {
        "document_id": "guide-1",
        "title": "Cam nang Da Nang",
        "body": "# Bien\nMy Khe dep. Phu hop nghi duong.\n## An uong\nHai san ngon.",
        "url": "https://example.test/guide",
    }

    chunks = chunk_cms(document, ChunkingConfig(cms_child_token_target=8, child_token_overlap=0))

    assert chunks
    assert any("Cam nang Da Nang - Bien" in chunk.text for chunk in chunks)
    assert any(chunk.metadata["url"] == "https://example.test/guide" for chunk in chunks)


def test_chunk_document_detects_review_bundle():
    chunks = chunk_document({"hotel_id": 1, "hotel_name": "A", "reviews": [{"text": "Great stay"}]})

    assert chunks[0].source_type == "review"
