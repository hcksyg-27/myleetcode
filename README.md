# Concurrent In-Memory Rate Limiter for LLM API Gateways

A robust, thread-safe, in-memory rate-limiting engine designed for high-concurrency LLM API gateways. This system enforces isolated rate limits per **client** and **resource**, preventing unfair resource consumption while safely handling high-volume parallel requests.

## 🚀 Features

*   **Dual-Strategy Engine**: Implements both **Sliding Window Log** and **Token Bucket** algorithms.
*   **Granular Isolation**: Maintains completely independent state tables for every `(client_id, resource_id)` pair.
*   **Thread Safety**: Thread-safe state synchronization under multi-threaded request processing.
*   **Metadata Responses**: Returns real-time metadata including execution status (`Allowed/Rejected`), remaining capacity, and estimated time-to-recovery.

---

## 🛠️ Core Algorithms

### 1. Sliding Window Log
Tracks individual request timestamps in a discrete time series. It slides continuously, ensuring that a user never exceeds the specified maximum capacity over any trailing time window.

*   **Window Size (\(W\))**: Time duration of the sliding window (e.g., 10 seconds).
*   **Limit (\(L\))**: Maximum requests allowed within \(W\).
*   **Eviction Engine**: On every request, entries older than \(t - W\) are purged before calculating the capacity check.

### 2. Token Bucket
Models continuous capacity recovery. Perfect for handling bursty traffic while enforcing a strict sustained ceiling.

*   **Capacity (\(C\))**: Maximum size of the bucket.
*   **Refill Rate (\(R\))**: Amount of tokens added per unit time (e.g., 0.5 tokens/sec).
*   **Continuous Refill Formula**: \(\text{Tokens}_{\text{new}} = \min(C, \text{Tokens}_{\text{old}} + (t_{\text{current}} - t_{\text{last}}) \times R)\)

---

## 🔍 Detailed Walkthrough: Sliding Window Log

The following operational tracing outlines how the sliding window mechanism evaluates state over time.

**Configuration Setup:**
*   **Window Size**: 10 seconds
*   **Capacity Limit**: 3 requests

### Request History Evaluation Trace

| Sequence | Time (\(t\)) | Window Range (\(t-10\)) | Evicted Timestamps | Active Logs State | Action | Remaining Capacity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Req 1** | \(t = 2\text{s}\) | \(\le -8\text{s}\) | None | `[2]` | **Allowed** ✅ | 2 |
| **Req 2** | \(t = 5\text{s}\) | \(\le -5\text{s}\) | None | `[2, 5]` | **Allowed** ✅ | 1 |
| **Req 3** | \(t = 8\text{s}\) | \(\le -2\text{s}\) | None | `[2, 5, 8]` | **Allowed** ✅ | 0 |
| **Req 4** | \(t = 11\text{s}\)| \(\le 1\text{s}\) | None *(t=2 still active)* | `[2, 5, 8]` | **Rejected** ❌ | 0 (Exhausted) |
| **Req 5** | \(t = 13\text{s}\)| \(\le 3\text{s}\) | `[2]` removed | `[5, 8, 13]` | **Allowed** ✅ | 0 |

---

## 🏗️ Architecture & Interface

The core service exposes a single unified gateway evaluation method:

```python
class RateLimiter: -> RateLimitResult:
    """
    Evaluates whether a target request passes or fails the rate limit policy.
    
    Returns a result object containing:
    - allowed (bool): Status of the request execution.
    - remaining_capacity (int/float): Available slots/tokens remaining.
    - retry_after (float): Seconds remaining until capacity returns to >= 1.
    """
```

### Concurrent Protection Blueprint
To guarantee memory and execution correctness across high-volume worker threads, state transitions use fine-grained synchronization keys:

