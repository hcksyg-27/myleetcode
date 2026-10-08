# Dual-Strategy Rate Limiter

A high-performance, object-oriented Python implementation of rate limiting featuring **Sliding Window Log** and **Token Bucket** algorithms. This library provides a unified interface to isolate and track traffic constraints per client and per resource.

## 🚀 Features

* **Dual Strategies:** Choose between memory-efficient `token_bucket` or burst-protective `sliding_window`.
* **Resource Isolation:** Granular rate limiting tracked uniquely by `(client_id, resource, strategy)`.
* **High Performance:** Utilizes a double-ended queue (`collections.deque`) for O(1) operations in the sliding window log, and pure math formulas for O(1) constant memory in the token bucket.
* **Actionable Metadata:** Blocked requests return precise `retry_after` countdowns.

---

## 📊 Comparison Matrix

| Strategy | Memory Complexity | CPU Complexity | Handling Burst Traffic |
| :--- | :--- | :--- | :--- |
| **Token Bucket** | **O(1) Constant** | **O(1)** (Arithmetic) | Allows instant bursts up to capacity |
| **Sliding Window** | **O(N) Variable** | **O(N)** (Queue cleanup) | Enforces strict, smoothed pacing |

---

## 🛠️ Usage Examples

### 1. Token Bucket Strategy (Recommended for API endpoints with burst allowances)
Allows clients to instantly consume accumulated tokens, tracking state lazily with timestamps.

```python
import time
from rate_limiter import RateLimiter

# Allow 5 requests every 10 seconds per client/resource
limiter = RateLimiter(strategy="token_bucket", limit=5, window_size=10)

# Simulate requests
for i in range(6):
    result = limiter.allow(client_id="user_42", resource="/api/v1/checkout")
    print(f"Request {i+1}: {result}")
    time.sleep(0.5)
```

**Example Output:**
```json
{"allowed": true, "remaining": 4}
{"allowed": true, "remaining": 3}
{"allowed": true, "remaining": 2}
{"allowed": true, "remaining": 1}
{"allowed": true, "remaining": 0}
{"allowed": false, "remaining": 0, "retry_after": 1.49}
```

### 2. Sliding Window Log Strategy (Recommended for tight security/expensive operations)
Prevents micro-bursting by keeping an exact chronological history of all calls within the moving time frame.

```python
# Allow 2 requests every 5 seconds
strict_limiter = RateLimiter(strategy="sliding_window", limit=2, window_size=5)

print(strict_limiter.allow("user_101", "/api/login"))  # True
print(strict_limiter.allow("user_101", "/api/login"))  # True
print(strict_limiter.allow("user_101", "/api/login"))  # False (retry_after returned)
```

---

## 🔍 Response Schema

The `.allow(client_id, resource)` method returns a structured dictionary:

### On Success (`"allowed": true`)
```json
{
  "allowed": true,
  "remaining": 4
}
```

### On Throttled (`"allowed": false`)
```json
{
  "allowed": false,
  "remaining": 0,
  "retry_after": 2.345
}
```
* `retry_after`: A float value representing the exact seconds the client must wait until a slot opens up or a full token regenerates.

---

## 🧪 Architecture Details

* **`get_state(client_id, resource)`**: Automatically provisions state machines dynamically. Sliding Window initializes a `deque()`, while Token Bucket instantiates a structural dictionary tracking floating-point balances.
* **Lazy Evaluation**: The token bucket does not run background timer threads. It dynamically updates the balance using elapsed time delta variables only when a request strikes the code path.
