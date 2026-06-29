"""discovery_cluster.py — TẦNG 2 pipeline Discovery: gom cụm lạ đồng nghĩa bằng embedding.

Owner: Trương Anh Long (KE, DA10). Đọc raw_discovery.jsonl (phát hiện novel của Tầng 1 trong
absa.py) -> gom các phrase ĐỒNG NGHĨA thành CLUSTER bằng vector (bge-m3) + union-find cosine.
Giải bài toán gộp/tách bằng VECTOR, không đoán tay: "cổ điển/cổ kính/hoài cổ" gần -> 1 cluster;
"retro" xa hơn -> cluster riêng.

NGUYÊN TẮC:
  - KHÔNG sửa code indexing/embedding/ (Khánh Duy) — chỉ import qua registry.
  - offline=True dùng HashEmbeddingModel = vector NGẪU NHIÊN -> CHỈ smoke-test pipeline chạy
    không vỡ, KHÔNG verify được gộp/tách. Nghiệm thu cụm BẮT BUỘC bge-m3 thật (~2GB).
  - Output clusters.json là DERIVED -> gitignore, tái sinh bằng script.

Chạy:
  # smoke (chỉ kiểm chạy, vector ngẫu nhiên):
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_cluster --offline
  # thật (cần sentence-transformers + tải bge-m3):
  .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.enrichment.discovery_cluster
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from knowledge_engineering.common.normalize import normalize

RAW_DISCOVERY = "knowledge_engineering/enrichment/raw_discovery.jsonl"
OUT_JSON = "knowledge_engineering/enrichment/clusters.json"

# Ngưỡng VÀO: phrase quá hiếm = nhiễu LLM, bỏ trước khi embed (embed tốn).
DEFAULT_MIN_FREQ = 3
DEFAULT_MIN_HOTELS = 2
# Ngưỡng GOM: cosine >= threshold -> cùng cluster. bge-m3 đã L2-normalize -> cosine = dot.
# 0.70 (KHÔNG phải 0.80) — đo THẬT trên bge-m3 (2026-06-11): nhóm đồng nghĩa tiếng Việt
# "cổ điển/cổ kính/hoài cổ/retro" chỉ ~0.69–0.75; 0.80 sẽ TÁCH chúng thành 4 cluster vụn.
# 0.70 gom đúng nhóm cổ điển MÀ vẫn tách "hiện đại" (cổ điển~hiện đại = 0.61). Chỉnh qua --threshold.
DEFAULT_THRESHOLD = 0.70
MAX_EXAMPLES = 8


def load_phrases(path: str, min_freq: int, min_hotels: int) -> list[dict]:
    """Đọc raw_discovery.jsonl -> gom theo phrase_norm (fold). DEDUPE (review_id, phrase_norm) để
    không đếm trùng khi jsonl có dòng lặp. Trả list dict đã lọc theo ngưỡng vào, sort freq giảm."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Chưa có {path} — chạy absa.py (Tầng 1) để sinh raw_discovery trước.")

    # phrase_norm -> trạng thái tích lũy
    freq: dict[str, int] = defaultdict(int)
    hotels: dict[str, set] = defaultdict(set)
    sent: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    display_votes: dict[str, Counter] = defaultdict(Counter)   # chọn dạng hiển thị có dấu phổ biến
    seen_pairs: set[tuple] = set()                             # (review_id, phrase_norm) chống trùng

    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ph = (r.get("phrase") or "").strip()
            if not ph:
                continue
            norm = normalize(ph, fold=True).replace("_", " ").strip()
            if not norm:
                continue
            pair = (r.get("review_id"), norm)
            if pair in seen_pairs:
                continue                       # đã đếm phát hiện này (jsonl lặp) -> bỏ
            seen_pairs.add(pair)
            freq[norm] += 1
            hid = r.get("hotel_id")
            if hid is not None:
                hotels[norm].add(hid)
            sent[norm][r.get("sentiment", "neutral")] += 1
            display_votes[norm][ph] += 1
            span = (r.get("span") or "").strip()
            if span and len(examples[norm]) < MAX_EXAMPLES:
                examples[norm].append(span)

    phrases = []
    for norm, f in freq.items():
        nh = len(hotels[norm])
        if f < min_freq or nh < min_hotels:
            continue
        display = display_votes[norm].most_common(1)[0][0]   # dạng có dấu xuất hiện nhiều nhất
        phrases.append({
            "norm": norm, "display": display, "freq": f,
            "hotels": sorted(hotels[norm]), "hotel_count": nh,
            "sentiment_dist": dict(sent[norm]), "examples": examples[norm],
        })
    phrases.sort(key=lambda x: -x["freq"])
    return phrases


def _union_find_cluster(vectors, threshold: float) -> list[int]:
    """Union-find theo cosine. vectors: list[list[float]] (đã L2-normalize -> cosine = dot).
    Trả root[i] = chỉ số cluster của phrase i. O(N^2) — N vài trăm-vài nghìn thì chấp nhận."""
    import numpy as np

    n = len(vectors)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]      # path compression
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    if n == 0:
        return []
    V = np.asarray(vectors, dtype="float32")
    sim = V @ V.T                              # ma trận cosine (vector đã chuẩn L2)
    for i in range(n):
        # chỉ xét j>i; nối nếu đủ gần
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                union(i, j)
    return [find(i) for i in range(n)]


def cluster(phrases: list[dict], threshold: float, offline: bool) -> dict:
    """Embed phrase -> union-find -> clusters.json dict. offline=True dùng HashEmbeddingModel."""
    from indexing.embedding.registry import get_embedding_model

    model = get_embedding_model("bge-m3", offline=offline)
    results = model.embed([p["display"] for p in phrases])
    vectors = [r.vector for r in results]
    roots = _union_find_cluster(vectors, threshold)

    # gom phrase theo root
    groups: dict[int, list[int]] = defaultdict(list)
    for idx, root in enumerate(roots):
        groups[root].append(idx)

    clusters = []
    for members_idx in groups.values():
        members = [phrases[i] for i in members_idx]
        members.sort(key=lambda x: -x["freq"])
        hotels: set = set()
        sent = Counter()
        examples: list[str] = []
        freq_total = 0
        for m in members:
            hotels.update(m["hotels"])
            sent.update(m["sentiment_dist"])
            freq_total += m["freq"]
            for ex in m["examples"]:
                if ex not in examples and len(examples) < MAX_EXAMPLES:
                    examples.append(ex)
        pos = sent.get("positive", 0)
        neg = sent.get("negative", 0)
        neu = sent.get("neutral", 0)
        mix = sent.get("mixed", 0)
        total_sent = max(1, pos + neg + neu + mix)
        clusters.append({
            "members": [m["display"] for m in members],
            "label_hint": members[0]["display"],          # member freq cao nhất -> gợi ý Tầng 3
            "hotel_count": len(hotels),
            "freq": freq_total,
            "sentiment_dist": {"positive": pos, "negative": neg, "neutral": neu, "mixed": mix},
            "neg_ratio": round(neg / total_sent, 2),
            "examples": examples,
            "hotels": sorted(hotels),                      # cần cho backfill khoanh hotel về sau
        })
    clusters.sort(key=lambda c: -c["hotel_count"])         # phổ biến lên đầu cho người duyệt
    for i, c in enumerate(clusters, 1):
        c["cluster_id"] = f"c{i:03d}"
    # đưa cluster_id lên đầu mỗi dict cho dễ đọc
    clusters = [{"cluster_id": c.pop("cluster_id"), **c} for c in clusters]

    return {
        "version": "1.0",
        "threshold": threshold,
        "model": "offline/hash-test" if offline else "bge-m3",
        "n_phrases": len(phrases),
        "n_clusters": len(clusters),
        "clusters": clusters,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TẦNG 2 Discovery: gom cụm lạ đồng nghĩa (embedding).")
    ap.add_argument("--in", dest="inp", default=RAW_DISCOVERY, help="raw_discovery.jsonl")
    ap.add_argument("--out", default=OUT_JSON, help="clusters.json")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"ngưỡng cosine gom cluster (mặc định {DEFAULT_THRESHOLD})")
    ap.add_argument("--min-freq", type=int, default=DEFAULT_MIN_FREQ,
                    help=f"freq tối thiểu để embed (mặc định {DEFAULT_MIN_FREQ})")
    ap.add_argument("--min-hotels", type=int, default=DEFAULT_MIN_HOTELS,
                    help=f"số hotel tối thiểu (mặc định {DEFAULT_MIN_HOTELS})")
    ap.add_argument("--offline", action="store_true",
                    help="HashEmbeddingModel (vector NGẪU NHIÊN) — CHỈ smoke-test chạy, KHÔNG verify cụm")
    args = ap.parse_args()

    phrases = load_phrases(args.inp, args.min_freq, args.min_hotels)
    print(f"Đọc {args.inp}: {len(phrases)} phrase (sau lọc >= {args.min_freq} lần, "
          f">= {args.min_hotels} hotel).")
    if not phrases:
        print("Không có phrase nào qua ngưỡng — dừng."); raise SystemExit(0)
    if args.offline:
        print("⚠ --offline: vector NGẪU NHIÊN, cụm KHÔNG có nghĩa — chỉ kiểm pipeline chạy.")

    out = cluster(phrases, args.threshold, args.offline)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {out['n_clusters']} cluster (threshold {args.threshold}) -> {args.out}")
    for c in out["clusters"][:20]:
        warn = " ⚠neg" if c["neg_ratio"] >= 0.6 else ""
        print(f"  {c['cluster_id']} | {c['hotel_count']:3d} hotel | {c['freq']:4d}x"
              f" | neg {c['neg_ratio']}{warn} | {c['members'][:5]}")
