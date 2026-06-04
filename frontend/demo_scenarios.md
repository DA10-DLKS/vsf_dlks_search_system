# Demo Scenarios

## Scenario 1: Quiet Beach Resort for Family

Query:

```text
Tôi muốn resort yên tĩnh gần biển cho gia đình
```

Expected UI behavior:

- Search box accepts the Vietnamese natural-language query.
- Top-K results show resort options near the beach.
- Result cards show score, location, category, amenities, and ranking info.
- Citations point to hotel detail source documents.
- Context chunks explain family-friendly beach resort evidence.
- LLM preview summarizes the context package.

Expected metadata/citation/context:

- Location: Nha Trang or Phú Quốc.
- Category: beach resort or villa resort.
- Amenities: beach, pool, kids club, family services.
- Citation/source document linked to hotel detail JSON.
- Context mentions family and quiet beach resort intent.

## Scenario 2: Business Hotel in Central Area

Query:

```text
Khách sạn phù hợp cho chuyến công tác ở trung tâm
```

Expected UI behavior:

- Results prioritize central city hotels.
- Metadata highlights location, business category, meeting room, Wi-Fi, and business services.
- One result intentionally lacks citation/context to verify fallback behavior.

Expected metadata/citation/context:

- Location: TP. Hồ Chí Minh or Đà Nẵng.
- Category: business hotel or city hotel.
- Citation explains business stay evidence when available.
- Missing citation/context displays fallback text.

## Scenario 3: Resort with Children Amenities

Query:

```text
Địa điểm nghỉ dưỡng có tiện ích cho trẻ em
```

Expected UI behavior:

- Results prioritize family resorts.
- Metadata shows kids club, pool, beach, and family activities.
- Citations and context chunks show evidence for children-friendly facilities.

Expected metadata/citation/context:

- Location: Phú Quốc or Nam Hội An.
- Category: family resort.
- Amenities: kids club, family activities, pool.
- Context mentions children-friendly facilities.
