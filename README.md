# In-Memory Rate Limiter

An in-memory rate limiter for an LLM API gateway, implemented in Python. The project explores how to control request frequency, isolate usage across clients and resources, and support different rate-limiting strategies.

## 1. Problem Statement

Imagine an API gateway that provides access to Large Language Model (LLM) services. Multiple clients may send requests to the gateway at the same time.

For example:

* Client A sends requests to an LLM API.
* Client B sends requests to the same LLM API.
* Client A also sends requests to an Embedding API.

Without rate limiting, a single client could consume excessive API capacity, affecting other clients and increasing infrastructure costs.

The goal is to build a rate limiter that decides whether each incoming request should be accepted or rejected based on a configurable limit.

The implementation supports two rate-limiting strategies:

1. **Sliding Window**
2. **Token Bucket**

Each client and resource combination maintains independent state.

## 2. Project Objectives

The main objectives are to:

* Limit the number of requests a client can make.
* Support multiple rate-limiting strategies.
* Maintain separate state for each client and resource.
* Remove expired request timestamps automatically.
* Replenish tokens continuously over time.
* Return whether a request is allowed.
* Report the remaining request capacity.
* Estimate how long a rejected request must wait before retrying.

## 3. Project Structure

```text
rate-limiter/
├── README.md
└── rate_limit.py
```

* `rate_limit.py`: Contains the rate limiter implementation and manual test examples.
* `README.md`: Documents the problem, design decisions, algorithms, and usage.

## 4. Technologies Used

* **Python 3** — implementation language.
* **`collections.deque`** — stores request timestamps for the Sliding Window strategy.
* **`time`** — obtains timestamps and measures elapsed time for expiration and token replenishment.
* **Dictionaries** — store configuration and state for each client/resource combination.

The current implementation uses only Python's standard library.

## 5. Design Overview

The main component is the `RateLimiter` class.

```python
class RateLimiter:
    def __init__(self, strategy, limit, window_size):
        self.strategy = strategy
        self.limit = limit
        self.window_size = window_size
        self.states = {}
```

The constructor accepts three configuration values:

| Parameter     | Description                                 |
| ------------- | ------------------------------------------- |
| `strategy`    | Selects `sliding_window` or `token_bucket`. |
| `limit`       | Maximum request capacity.                   |
| `window_size` | Time window, in seconds.                    |

For Sliding Window, `limit` represents the maximum accepted requests during the configured window.

For Token Bucket, `limit` represents the bucket's maximum token capacity. The current refill rate is calculated as `limit / window_size` tokens per second.

### Independent state

The rate limiter uses a tuple containing the client ID and resource name as the dictionary key.

```python
key = (client_id, resource)
```

For example:

```text
("client-A", "llm")       → independent state
("client-A", "embedding") → independent state
("client-B", "llm")       → independent state
```

This prevents one client's requests to one resource from consuming the capacity allocated to another client/resource combination.

### The `get_state()` method

The `get_state()` method retrieves existing state or creates it when a client/resource combination is encountered for the first time.

For Sliding Window, the state is a deque of timestamps.

For Token Bucket, the state is a dictionary containing:

* `tokens`: the current available token count.
* `last_updated`: the timestamp of the last token-refill calculation.

Reusing existing state is essential because creating a new state for every request would lose the history needed to enforce the limit.

## 6. Rate-Limiting Algorithms

### A. Sliding Window

The Sliding Window strategy tracks the timestamps of accepted requests within a moving time window.

For example, assume:

```text
limit = 3
window_size = 10 seconds
```

A client sends requests at the following times:

```text
Time:        100    103    106
Requests:     R1     R2     R3
```

All three requests are accepted. An additional request at time 107 is rejected because three requests are already within the window.

#### How it works

1. Retrieve the timestamp deque for the client and resource.

2. Obtain the current time.

3. Calculate the expiration boundary:

   ```python
   expiry_time = current_time - self.window_size
   ```

4. Remove timestamps that are at or before the expiration boundary.

5. Count the timestamps that remain.

6. If the count is below the limit, accept the request and append its timestamp.

7. Otherwise, reject the request and calculate its estimated recovery time.

Expired timestamps are removed using:

```python
while timestamps and timestamps[0] <= expiry_time:
    timestamps.popleft()
```

A deque is useful because it supports efficient removal from the front, where the oldest timestamp is stored.

#### Remaining capacity

After accepting a request:

```python
remaining = self.limit - len(timestamps)
```

For a limit of three, if two requests are already in the window, accepting another request leaves zero remaining capacity.

#### Recovery time

When the window is full, the earliest time another request can be accepted is determined by when the oldest request expires:

```python
retry_after = (
    timestamps[0] + self.window_size - current_time
)
```

This estimates how many seconds the client must wait before the oldest request leaves the window.

### B. Token Bucket

The Token Bucket strategy models request capacity using a bucket that contains tokens.

Each accepted request consumes one token. Tokens are replenished continuously according to the refill rate, up to the maximum bucket capacity.

For example:

```text
capacity = 3 tokens
window_size = 10 seconds
refill_rate = 3 / 10
            = 0.3 tokens per second
```

Initially, the bucket contains three tokens.

```text
Initial bucket: 3 tokens

Request 1 → 2 tokens
Request 2 → 1 token
Request 3 → 0 tokens
Request 4 → Rejected
```

As time passes, tokens are replenished. The client can make another request when at least one token is available.

#### How it works

**Step 1: Calculate elapsed time**

```python
time_passed = current_time - bucket["last_updated"]
```

This measures the time since the last refill calculation.

**Step 2: Calculate the refill rate**

```python
refill_rate = self.limit / self.window_size
```

This implementation derives the refill rate from the configured capacity and window size.

**Step 3: Replenish tokens**

```python
replenished_tokens = refill_rate * time_passed

bucket["tokens"] = min(
    float(self.limit),
    bucket["tokens"] + replenished_tokens
)
```

The `min()` function ensures that the bucket never exceeds its configured capacity.

**Step 4: Update the timestamp**

```python
bucket["last_updated"] = current_time
```

This records when the bucket was last updated.

**Step 5: Process the request**

If at least one token is available, the request is accepted and one token is consumed.

Otherwise, the request is rejected.

#### Recovery time

If the bucket has less than one token, the time needed to generate the next token is calculated as:

```python
needed_tokens = 1.0 - bucket["tokens"]
retry_after = needed_tokens / refill_rate
```

For example, if the bucket contains `0.4` tokens and replenishes at `0.2` tokens per second:

```text
Needed tokens = 1.0 - 0.4
              = 0.6

Retry after   = 0.6 / 0.2
              = 3 seconds
```

This allows the limiter to report partial recovery rather than waiting for the bucket to become completely full.

## 7. Request Processing Flow

Both strategies are accessed through the same public method:

```python
limiter.allow(client_id, resource)
```

The method retrieves the appropriate state and delegates the request to the selected strategy.

```text
Incoming request
       |
       v
Identify client + resource
       |
       v
Retrieve or create state
       |
       v
Select rate-limiting strategy
       |
       +-----------------------+
       |                       |
       v                       v
  Sliding Window          Token Bucket
       |                       |
       v                       v
 Remove expired            Refill tokens
 timestamps                    |
       |                       v
       v                  Check token count
 Check request count           |
       |                       |
       +-----------+-----------+
                   |
                   v
           Accept or reject
                   |
                   v
       Return result to caller
```

## 8. Response Format

The `allow()` method returns a Python dictionary.

An accepted request may return:

```python
{
    "allowed": True,
    "remaining": 2
}
```

A rejected request may return:

```python
{
    "allowed": False,
    "remaining": 0,
    "retry_after": 4.5
}
```

The fields mean:

| Field         | Meaning                                                                                            |
| ------------- | -------------------------------------------------------------------------------------------------- |
| `allowed`     | Whether the request was accepted.                                                                  |
| `remaining`   | Number of additional whole requests currently available under the strategy.                        |
| `retry_after` | Estimated seconds until another request can be accepted; currently returned for rejected requests. |

`retry_after` is an estimate based on the current state. It is not a guarantee that the next request will succeed if another request consumes capacity first.

## 9. How to Run the Project

### Prerequisites

Install Python 3 and open the repository in Visual Studio Code.

Verify that Python is available:

```bash
python --version
```

On some systems, you may need:

```bash
python3 --version
```

### Run the program

Open the VS Code terminal in the repository directory:

```bash
python rate_limit.py
```

The current script includes manual examples for both strategies.

### Example: Sliding Window

```python
sliding_limiter = RateLimiter(
    strategy="sliding_window",
    limit=3,
    window_size=10
)

print(sliding_limiter.allow("client-A", "llm"))
print(sliding_limiter.allow("client-A", "llm"))
print(sliding_limiter.allow("client-A", "llm"))
print(sliding_limiter.allow("client-A", "llm"))
```

Expected behavior:

```text
Request 1 → Allowed
Request 2 → Allowed
Request 3 → Allowed
Request 4 → Rejected
```

The fourth request is rejected because the first three requests are still within the ten-second window.

### Example: Token Bucket

```python
bucket_limiter = RateLimiter(
    strategy="token_bucket",
    limit=2,
    window_size=5
)

print(bucket_limiter.allow("client-A", "llm"))
print(bucket_limiter.allow("client-A", "llm"))
print(bucket_limiter.allow("client-A", "llm"))
```

Expected immediate behavior:

```text
Request 1 → Allowed
Request 2 → Allowed
Request 3 → Rejected
```

The bucket starts with two tokens, so the first two requests consume its initial capacity. The third request is rejected if insufficient time has passed for another token to be replenished.

## 10. Testing

The project has been manually tested during development for the following behaviors:

* Creating and reusing state.
* Enforcing the Sliding Window request limit.
* Removing expired timestamps.
* Isolating state across different clients.
* Isolating state across different resources.
* Accepting requests again after expiration.
* Enforcing Token Bucket capacity.
* Calculating estimated recovery time for rejected requests.

These are manual tests, not yet a formal automated test suite. Automated tests should be added to make the behavior repeatable and easier to verify after code changes.

## 11. Complexity Analysis

Let \(n\) be the number of request timestamps currently stored for a client/resource pair.

| Operation                                           | Complexity       |
| --------------------------------------------------- | ---------------- |
| Retrieve state from the dictionary                  | Average \(O(1)\) |
| Append a timestamp to the deque                     | \(O(1)\)         |
| Remove one expired timestamp from the deque         | \(O(1)\)         |
| Clean up \(k\) expired timestamps                   | \(O(k)\)         |
| Check the number of stored timestamps using `len()` | \(O(1)\)         |
| Update Token Bucket state                           | \(O(1)\)         |

For Sliding Window, each timestamp is appended once and removed at most once, giving amortized \(O(1)\) timestamp-maintenance work per request, excluding other system overhead.

For Token Bucket, each request requires constant-time state updates, assuming dictionary operations take average \(O(1)\) time.

## 12. Current Limitations and Future Improvements

This project is a learning implementation and does not yet cover every production requirement.

### Thread safety

The current implementation does not use locks. Concurrent requests could read or modify shared state at the same time, potentially allowing more requests than the configured limit.

**Future improvement:** Add appropriate synchronization around state updates and request decisions. Ensure that checking capacity and consuming capacity happen atomically.

### Automated testing

Manual testing is useful during development, but it does not automatically verify behavior after future changes.

**Future improvement:** Add unit tests using Python's `unittest` or `pytest`. Inject or mock the clock so expiration and token-refill tests do not need to wait in real time.

### Configuration validation

The constructor currently does not validate strategy names or configuration values.

**Future improvement:** Validate that the strategy is supported, the limit is positive, and the window size is positive before accepting configuration.

### Strategy-specific configuration

The current Token Bucket refill rate is derived from `limit / window_size`. A production implementation may need independent configuration for token capacity and refill rate.

**Future improvement:** Allow token capacity and refill rate to be configured separately.

### Response consistency

Accepted responses currently omit `retry_after`, while rejected responses include it. Token Bucket also reports remaining capacity as an integer, even when a fractional token amount exists.

**Future improvement:** Define a consistent response contract and document whether `remaining` means whole requests available or the exact token balance.

### State cleanup

The current dictionary retains state for every client/resource combination it encounters. Long-running services could accumulate unused state.

**Future improvement:** Add an appropriate strategy for expiring inactive client/resource entries.

### Production deployment

The state is held in process memory. It will not automatically be shared across multiple application processes or servers, and it will be lost when the process restarts.

**Future improvement:** If shared state across servers is required, evaluate a shared storage solution and a distributed atomic-update mechanism.

## 13. Learning Outcomes

Through this project, the implementation explores:

* Designing a Python class around a clear responsibility.
* Using dictionaries to isolate state by a composite key.
* Using deques to manage timestamp-based request history.
* Implementing time-based expiration.
* Calculating capacity and recovery estimates.
* Implementing continuous token replenishment.
* Comparing two common rate-limiting algorithms.
* Identifying concurrency, testing, and scalability requirements.

## 14. Conclusion

This project implements an in-memory rate limiter with Sliding Window and Token Bucket strategies. It provides a foundation for understanding how API gateways can control request frequency while maintaining separate usage state for individual clients and resources.

The next stage is to strengthen the implementation with automated tests, input validation, thread safety, and a consistent response contract before considering it suitable for concurrent production use.
