"""Streamlit Explainable Retrieval Console for DA10.

This is a frontend/debug display layer only. It does not calculate retrieval,
ranking, context, or evaluation metrics. It calls the DA10 backend endpoints and
shows raw responses next to mentor-facing UI sections.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import streamlit as st


DEFAULT_QUERY = "khach san phu hop cho tre nho gan VinWonders Phu Quoc"
DEFAULT_API_BASE = "http://localhost:8000"
LAN_HINT = "Neu localhost bi 404 do port conflict, thu API base URL dang: http://192.168.10.48:8000"


@dataclass
class ApiResult:
    ok: bool
    method: str
    url: str
    status_code: int | None
    elapsed_ms: int
    data: Any = None
    text: str = ""
    error: str = ""


def call_api(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> ApiResult:
    start = time.perf_counter()
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            parsed = parse_json(raw)
            return ApiResult(
                ok=200 <= response.status < 300,
                method=method,
                url=url,
                status_code=response.status,
                elapsed_ms=elapsed_ms,
                data=parsed,
                text=raw,
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ApiResult(
            ok=False,
            method=method,
            url=url,
            status_code=exc.code,
            elapsed_ms=elapsed_ms,
            data=parse_json(raw),
            text=raw,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001 - debug console must surface all errors
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ApiResult(
            ok=False,
            method=method,
            url=url,
            status_code=None,
            elapsed_ms=elapsed_ms,
            error=f"{type(exc).__name__}: {exc}",
        )


def parse_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return None


def endpoint(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    clean = base_url.rstrip("/")
    if not params:
        return f"{clean}{path}"
    query = urllib.parse.urlencode(params)
    return f"{clean}{path}?{query}"


def status_badge(result: ApiResult | None, label: str) -> None:
    if result is None:
        st.info(f"{label}: chua goi")
        return
    if result.ok:
        st.success(f"{label}: OK - {result.status_code} - {result.elapsed_ms} ms")
    else:
        code = result.status_code if result.status_code is not None else "NO_RESPONSE"
        st.error(f"{label}: LOI - {code} - {result.elapsed_ms} ms")


def show_raw(result: ApiResult | None, title: str) -> None:
    with st.expander(title, expanded=False):
        if result is None:
            st.write("Chua co response.")
            return
        st.write(
            {
                "method": result.method,
                "url": result.url,
                "status_code": result.status_code,
                "elapsed_ms": result.elapsed_ms,
                "error": result.error,
            }
        )
        if result.data is not None:
            st.json(result.data)
        elif result.text:
            st.code(result.text)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def fmt(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def local_query_tags(query: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    q = normalize_text(query)
    tags: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    def add(tag: str, label: str, matched: str, confidence: float) -> None:
        tags.append(
            {
                "tag": tag,
                "label": label,
                "matched_text": matched,
                "source": "frontend fallback",
                "confidence": confidence,
            }
        )

    if "khach san" in q or "khách sạn" in q or "hotel" in q:
        add("OBJ_HOTEL", "Doi tuong luu tru", "khach san", 0.95)
    if "resort" in q:
        add("OBJ_RESORT", "Loai hinh resort", "resort", 0.92)
    if "tre nho" in q or "trẻ nhỏ" in q or "tre em" in q or "gia dinh" in q:
        add("PURPOSE_FAMILY", "Phu hop gia dinh/tre nho", "tre nho / gia dinh", 0.90)
        add("AMEN_KIDS_FRIENDLY", "Tien ich than thien tre em", "tre nho", 0.82)
        edges.extend(
            [
                {"from": "PURPOSE_FAMILY", "to": "AMEN_KIDS_CLUB", "reason": "boost tien ich tre em"},
                {"from": "PURPOSE_FAMILY", "to": "AMEN_KIDS_POOL", "reason": "boost ho boi tre em"},
                {"from": "PURPOSE_FAMILY", "to": "ROOM_FAMILY", "reason": "boost phong gia dinh"},
            ]
        )
    if "vinwonders" in q or "vin wonder" in q:
        add("LMK_VINWONDERS_PHU_QUOC", "Moc gan VinWonders Phu Quoc", "VinWonders Phu Quoc", 0.94)
        edges.append({"from": "LMK_VINWONDERS_PHU_QUOC", "to": "LOC_PHU_QUOC", "reason": "suy ra vi tri"})
    if "phu quoc" in q or "phú quốc" in q:
        add("LOC_PHU_QUOC", "Vi tri Phu Quoc", "Phu Quoc", 0.93)
    if "bien" in q or "biển" in q:
        add("LOC_NEAR_BEACH", "Gan bien", "bien", 0.84)
    if "yen tinh" in q or "yên tĩnh" in q:
        add("STYLE_QUIET", "Khong gian yen tinh", "yen tinh", 0.86)

    return tags, edges


def explain_bm25_result(hotel: dict[str, Any], tags: list[dict[str, Any]]) -> list[str]:
    haystack = normalize_text(
        " ".join(
            str(hotel.get(key, ""))
            for key in ("name", "hotel_name", "city", "address", "accommodation_type", "description", "amenities")
        )
    )
    reasons: list[str] = []
    tag_ids = {tag["tag"] for tag in tags}

    if "LOC_PHU_QUOC" in tag_ids and ("phu quoc" in haystack or "phú quốc" in haystack):
        reasons.append("Khop vi tri Phu Quoc trong ten/dia chi/mo ta.")
    if "LMK_VINWONDERS_PHU_QUOC" in tag_ids and ("vinwonders" in haystack or "vinpearl" in haystack):
        reasons.append("Co dau hieu lien quan VinWonders/Vinpearl.")
    if "PURPOSE_FAMILY" in tag_ids and (
        "gia dinh" in haystack or "gia đình" in haystack or "tre em" in haystack or "trẻ em" in haystack
    ):
        reasons.append("Co tin hieu phu hop gia dinh/tre em.")
    if "AMEN_KIDS_FRIENDLY" in tag_ids and (
        "tre em" in haystack or "trẻ em" in haystack or "ho boi" in haystack or "hồ bơi" in haystack
    ):
        reasons.append("Co tien ich/ngu canh than thien tre em.")
    if hotel.get("review_score") is not None:
        reasons.append(f"review_score = {fmt(hotel.get('review_score'))}.")
    if hotel.get("score") is not None:
        reasons.append(f"BM25 score = {fmt(hotel.get('score'))}.")
    if not reasons:
        reasons.append("BM25 tra ve do khop tu khoa trong name/description/address.")
    return reasons[:5]


def render_backend_status(results: dict[str, ApiResult | None]) -> None:
    cols = st.columns(4)
    with cols[0]:
        status_badge(results.get("health"), "Health")
    with cols[1]:
        status_badge(results.get("search"), "GET /search")
    with cols[2]:
        status_badge(results.get("hybrid"), "GET /hybrid_search")
    with cols[3]:
        status_badge(results.get("context"), "POST /context")


def render_search_results(search_result: ApiResult | None, tags: list[dict[str, Any]]) -> None:
    st.subheader("Ket qua BM25 that tu GET /search")
    if not search_result:
        st.info("Chua goi GET /search.")
        return
    if not search_result.ok:
        st.error("GET /search dang loi. Xem Raw debug de doc response.")
        return

    data = search_result.data or {}
    results = as_list(data.get("results"))
    total_hits = data.get("total_hits") or len(results)
    st.caption(f"query={data.get('query')} | results={len(results)} | total_hits fallback={total_hits} | took_ms={data.get('took_ms')}")

    if not results:
        st.warning("Khong co ket qua search.")
        return

    for index, hotel in enumerate(results[:10], start=1):
        title = hotel.get("name") or hotel.get("hotel_name") or hotel.get("id") or f"Hotel #{index}"
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"**#{index} {title}**")
                st.caption(f"{hotel.get('city', '-')} | {hotel.get('accommodation_type', '-')}")
                st.write(str(hotel.get("description", ""))[:420] + "...")
            with cols[1]:
                st.metric("BM25 score", fmt(hotel.get("score")))
                st.metric("Review", fmt(hotel.get("review_score")))
            with cols[2]:
                st.metric("Stars", fmt(hotel.get("star_rating")))
                st.metric("ID", fmt(hotel.get("id")))
            reasons = explain_bm25_result(hotel, tags)
            st.markdown("**Vi sao co the khop query?**")
            for reason in reasons:
                st.write(f"- {reason}")


def render_query_understanding(query: str, hybrid_result: ApiResult | None) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    st.subheader("Query -> ontology tags")
    if hybrid_result and hybrid_result.ok and isinstance(hybrid_result.data, dict):
        intent = hybrid_result.data.get("intent") or {}
        rows: list[dict[str, Any]] = []
        for field in ("concepts", "hard_concepts", "feel_concepts", "purposes", "landmarks", "location_concepts"):
            for value in as_list(intent.get(field)):
                rows.append({"tag": value, "field": field, "source": "backend /hybrid_search"})
        if rows:
            st.success("Dang hien thi ontology/intent tu backend /hybrid_search.")
            st.dataframe(rows, use_container_width=True, hide_index=True)
            return rows, []

    tags, edges = local_query_tags(query)
    st.warning("Backend /hybrid_search chua tra duoc intent. Dang hien thi fallback frontend de debug/demo.")
    st.dataframe(tags, use_container_width=True, hide_index=True)
    if edges:
        st.markdown("**Mo rong ontology fallback**")
        st.dataframe(edges, use_container_width=True, hide_index=True)
    return tags, edges


def render_hybrid(hybrid_result: ApiResult | None) -> None:
    st.subheader("Hybrid trace")
    if not hybrid_result:
        st.info("Chua goi /hybrid_search.")
        return
    if not hybrid_result.ok:
        st.error("GET /hybrid_search dang loi backend.")
        st.write(
            {
                "status_code": hybrid_result.status_code,
                "elapsed_ms": hybrid_result.elapsed_ms,
                "error": hybrid_result.error,
                "body": hybrid_result.data or hybrid_result.text,
            }
        )
        st.warning(
            "Huong sua backend: neu vector/BGE-M3/Qdrant timeout thi /hybrid_search nen fallback ve BM25 + "
            "business ranking thay vi tra HTTP 500."
        )
        return

    data = hybrid_result.data or {}
    cols = st.columns(4)
    cols[0].metric("n_candidates", fmt(data.get("n_candidates")))
    cols[1].metric("n_fused", fmt(data.get("n_fused")))
    cols[2].metric("top_hotels", len(as_list(data.get("top_hotels"))))
    cols[3].metric("context chunks", len(as_list((data.get("context_package") or {}).get("chunks"))))
    st.json(data)


def render_context(context_result: ApiResult | None) -> None:
    st.subheader("Context package va evidence")
    if not context_result:
        st.info("Chua goi /context. Chon hotel_id tu ket qua search roi bam Run full trace.")
        return
    if not context_result.ok:
        st.error("POST /context dang loi.")
        st.write(context_result.data or context_result.text or context_result.error)
        return

    data = context_result.data or {}
    cols = st.columns(4)
    cols[0].metric("result_id", fmt(data.get("result_id")))
    cols[1].metric("citations", len(as_list(data.get("citations"))))
    cols[2].metric("source_documents", len(as_list(data.get("source_documents"))))
    cols[3].metric("context_chunks", len(as_list(data.get("context_chunks"))))

    llm_context = data.get("llm_context") or data.get("context_text")
    if llm_context:
        st.markdown("**LLM context**")
        st.text_area("llm_context", value=str(llm_context), height=180)
    else:
        st.warning("Backend tra /context thanh cong nhung llm_context dang rong.")

    evidence = data.get("evidence") or {}
    if evidence:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Positive evidence**")
            st.json(evidence.get("positives", []))
        with c2:
            st.markdown("**Negative evidence**")
            st.json(evidence.get("negatives", []))

    st.markdown("**Raw context response**")
    st.json(data)


def run_trace(api_base: str, query: str, top_n: int, selected_result_id: str) -> dict[str, ApiResult | None]:
    results: dict[str, ApiResult | None] = {}
    results["health"] = call_api("GET", endpoint(api_base, "/health"), timeout=10)
    results["search"] = call_api("GET", endpoint(api_base, "/search", {"q": query}), timeout=25)
    results["hybrid"] = call_api(
        "GET",
        endpoint(api_base, "/hybrid_search", {"q": query, "top_n": top_n, "answer": "false"}),
        timeout=45,
    )
    if selected_result_id:
        result_id = selected_result_id if selected_result_id.startswith("hotel_") else f"hotel_{selected_result_id}"
        results["context"] = call_api(
            "POST",
            endpoint(api_base, "/context"),
            payload={"result_id": result_id, "query": query},
            timeout=30,
        )
    else:
        results["context"] = None
    return results


def main() -> None:
    st.set_page_config(page_title="DA10 Explainable Retrieval Console", layout="wide")
    st.title("DA10 Explainable Retrieval Console")
    st.caption("Streamlit frontend/debug console. Hieu chi hien thi output backend, khong sua retrieval/ranking/evaluation.")

    with st.sidebar:
        st.header("Cau hinh")
        api_base = st.text_input("API base URL", value=DEFAULT_API_BASE)
        st.caption(LAN_HINT)
        query = st.text_area("Query", value=DEFAULT_QUERY, height=90)
        top_n = st.selectbox("Top N", [5, 10, 20], index=1)
        selected_result_id = st.text_input("result_id/hotel_id cho POST /context", value="17242876")
        run_button = st.button("Run full trace", type="primary", use_container_width=True)
        health_button = st.button("Chi test /health", use_container_width=True)

        st.divider()
        st.markdown("**Endpoint can debug**")
        st.write("- GET /health")
        st.write("- GET /search")
        st.write("- GET /hybrid_search")
        st.write("- POST /context")

    if "results" not in st.session_state:
        st.session_state.results = {"health": None, "search": None, "hybrid": None, "context": None}

    if health_button:
        st.session_state.results["health"] = call_api("GET", endpoint(api_base, "/health"), timeout=10)

    if run_button:
        with st.spinner("Dang goi backend..."):
            st.session_state.results = run_trace(api_base, query, int(top_n), selected_result_id)

    results = st.session_state.results
    render_backend_status(results)

    health_result = results.get("health")
    if health_result and health_result.status_code == 404 and "localhost" in api_base:
        st.error(
            "localhost:8000 dang tra 404. Kha nang cao la port 8000 bi process local khac chiem. "
            "Thu API base URL bang IP LAN, vi du http://192.168.10.48:8000."
        )

    st.divider()
    tags, _ = render_query_understanding(query, results.get("hybrid"))

    tab_search, tab_hybrid, tab_context, tab_raw = st.tabs(
        ["BM25 Search", "Hybrid Trace", "Context/Evidence", "Raw Debug"]
    )
    with tab_search:
        render_search_results(results.get("search"), tags)
    with tab_hybrid:
        render_hybrid(results.get("hybrid"))
    with tab_context:
        render_context(results.get("context"))
    with tab_raw:
        show_raw(results.get("health"), "Raw GET /health")
        show_raw(results.get("search"), "Raw GET /search")
        show_raw(results.get("hybrid"), "Raw GET /hybrid_search")
        show_raw(results.get("context"), "Raw POST /context")


if __name__ == "__main__":
    main()
