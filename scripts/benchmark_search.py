"""Benchmark BM25 search endpoint.

Generates load and collects latency percentiles (p50, p95, p99).
"""

import argparse
import asyncio
import time
import statistics
import httpx
from datetime import datetime


async def send_request(client, url, query):
    """Send a single search request and return latency in ms."""
    start = time.time()
    try:
        async with client.stream("GET", url, params={"q": query}) as response:
            await response.aread()
        latency_ms = (time.time() - start) * 1000
        return latency_ms, None
    except Exception as e:
        return None, str(e)


async def benchmark(
    target_url: str,
    query_file: str,
    qps: int,
    duration_sec: int,
    concurrency: int = 10,
):
    """
    Run benchmark.

    Args:
        target_url: API base URL (e.g., http://localhost:8000)
        query_file: Path to file with queries (one per line)
        qps: Target queries per second
        duration_sec: Benchmark duration in seconds
        concurrency: Number of concurrent requests
    """

    # Load queries
    try:
        with open(query_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        # Use default test queries if file not found
        queries = [
            "khách sạn 5 sao hạ long",
            "resort bãi biển việt nam",
            "khách sạn có spa",
            "nơi lưu trú gần sân bay",
            "resort với bể bơi",
        ]

    if not queries:
        print("No queries found. Exiting.")
        return

    latencies = []
    errors = 0
    request_count = 0
    completed_count = 0

    print(f"Target: {target_url}/search")
    print(f"Duration: {duration_sec}s")
    print(f"Target QPS: {qps}")
    print(f"Concurrency: {concurrency}")
    print(f"Query file: {query_file}")
    print(f"Loaded {len(queries)} queries")
    print()
    print("Warming up...")

    # Warm up
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(5):
            query = queries[request_count % len(queries)]
            await send_request(client, f"{target_url}/search", query)

    print("Starting benchmark...")
    print()

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_request(client, url, query):
        async with semaphore:
            return await send_request(client, url, query)

    async def record_request(client, url, query):
        nonlocal errors, completed_count, interval_completed
        latency_ms, error = await bounded_request(client, url, query)
        completed_count += 1
        if latency_ms is not None:
            latencies.append(latency_ms)
            interval_completed += 1
        else:
            errors += 1

    # Run benchmark
    async with httpx.AsyncClient(timeout=30) as client:
        start_time = time.time()
        interval_start = start_time
        interval_completed = 0
        next_request_at = start_time
        tasks = []

        while time.time() - start_time < duration_sec:
            now = time.time()
            if now >= next_request_at:
                query = queries[request_count % len(queries)]
                task = asyncio.create_task(
                    record_request(client, f"{target_url}/search", query)
                )
                tasks.append(task)
                request_count += 1
                next_request_at += 1.0 / qps
            else:
                await asyncio.sleep(min(0.001, next_request_at - now))

            elapsed = time.time() - interval_start
            if elapsed >= 1.0:
                actual_qps = interval_completed / elapsed
                print(f"[{time.time() - start_time:.1f}s] "
                      f"Throughput: {actual_qps:.1f} req/s, "
                      f"Errors: {errors}")
                interval_start = time.time()
                interval_completed = 0

        if tasks:
            await asyncio.gather(*tasks)

    # Print results
    elapsed_total = time.time() - start_time

    if not latencies:
        print("No successful requests. Exiting.")
        return

    latencies_sorted = sorted(latencies)
    p50 = statistics.quantiles(latencies_sorted, n=100)[49]  # 50th percentile
    p95 = statistics.quantiles(latencies_sorted, n=100)[94]  # 95th percentile
    p99 = statistics.quantiles(latencies_sorted, n=100)[98]  # 99th percentile

    print()
    print("=" * 60)
    print(f"Benchmark Results ({datetime.now().isoformat()})")
    print("=" * 60)
    print(f"Total requests: {request_count}")
    print(f"Successful: {len(latencies)}")
    print(f"Errors: {errors}")
    print(f"Error rate: {100.0 * errors / request_count:.2f}%")
    print(f"Actual duration: {elapsed_total:.2f}s")
    print(f"Actual QPS: {request_count / elapsed_total:.2f}")
    print()
    print("Latency (ms):")
    print(f"  Min: {min(latencies_sorted):.2f}")
    print(f"  Max: {max(latencies_sorted):.2f}")
    print(f"  Mean: {statistics.mean(latencies_sorted):.2f}")
    print(f"  Median: {statistics.median(latencies_sorted):.2f}")
    print(f"  P50: {p50:.2f}")
    print(f"  P95: {p95:.2f}")
    print(f"  P99: {p99:.2f}")
    print(f"  StdDev: {statistics.stdev(latencies_sorted):.2f}")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Benchmark BM25 search endpoint')
    parser.add_argument('--target', default='http://localhost:8000',
                        help='API base URL (default: http://localhost:8000)')
    parser.add_argument('--query-file', default='tests/test_queries/queries.txt',
                        help='Query file (one per line)')
    parser.add_argument('--qps', type=int, default=50,
                        help='Target QPS (default: 50)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Benchmark duration in seconds (default: 60)')
    parser.add_argument('--concurrency', type=int, default=10,
                        help='Concurrent requests (default: 10)')

    args = parser.parse_args()

    asyncio.run(benchmark(
        target_url=args.target,
        query_file=args.query_file,
        qps=args.qps,
        duration_sec=args.duration,
        concurrency=args.concurrency,
    ))
