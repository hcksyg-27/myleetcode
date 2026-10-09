from collections import deque
import time

class RateLimiter:
    def __init__(self, strategy, limit, window_size):
        self.strategy = strategy
        self.limit = limit
        self.window_size = window_size
        self.states = {}


    # we want First request--> create state --> second request --> use same state --> Third request --> use same state 
    # Otherwise we'd lose the previous request timestamps
    def get_state(self, client_id, resource):
        key = (client_id, resource)

        # "Have we already created state for client-A using the LLM resource?", initially.. self.states={}
        if key not in self.states:
            if self.strategy == "token_bucket":
                self.states[key] = {
                    "tokens": float(self.limit),
                    "last_updated": time.time(),
                }
            else:
                # self.states
                # │
                # └── ("client-A", "llm") → deque([])
                self.states[key] = deque()

        # Return that deque
        return self.states[key]

    def _allow_sliding_window(self, timestamps ):
        # Step 1: Get the isolated state(list of timestamps)
        
        # timestamps = self.get_state(client_id, resource)
        # Step 2: Get the current time
        current_time = time.time()
        # Step 3: Remove timestamps that are outside the sliding window
        expiry_time = current_time - self.window_size

        # Any timestamps less that expiry_time is outside our current window
        while timestamps and timestamps[0] <= expiry_time:
            timestamps.popleft()

        # Step 4: check how many timestamps remain
        # Step 5: if below limit --> accept and add current timestamps
        if len(timestamps) < self.limit:
            timestamps.append(current_time)
            remaining = self.limit - len(timestamps)
            return {
                "allowed": True,
                "remaining": remaining,
            }
        # We only reach here when the limit is full
        retry_after = timestamps[0] + self.window_size - current_time
        # Otherwise --> reject
        return {
            "allowed": False,
            "remaining": 0,
            "retry_after": max(0.0, retry_after)
        }

    def _allow_token_bucket(self, bucket):
        current_time = time.time()

        # 1. Calculate continous linear dynakic token replenishment
        time_passed = current_time - bucket["last_updated"]
        refill_rate = self.limit / self.window_size # fractional tokens
        replenished_tokens = refill_rate * time_passed

        # 2. Add tokens up to the target capacity and record update mark
        bucket["tokens"] = min(float(self.limit), bucket["tokens"] + replenished_tokens)
        bucket["last_updated"] = current_time

        # 3. Process access permit check
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return {
                "allowed": True,
                "remaining": int(bucket["tokens"]),
            }
        # Time remaining until at least 1 whole structural token is refilled
        needed_tokens = 1.0 - bucket["tokens"]
        retry_after = needed_tokens / refill_rate
        return {
            "allowed": False,
            "remaining": 0,
            "retry_after": max(0.0, retry_after)
        }

    def allow(self, client_id, resource):
        state_bucket = self.get_state(client_id, resource)

        if self.strategy == "sliding_window":
            return self._allow_sliding_window(state_bucket)
        elif self.strategy == "token_bucket":
            return self._allow_token_bucket(state_bucket)
        else:
            raise ValueError(f"Unsupported strategy Logic: {self.strategy}")


    
# Tiny experiment
if __name__ == "__main__":
    # limiter = RateLimiter(
    #     strategy="sliding_window",
    #     limit=3,
    #     window_size=10
    # )
    # Test 1
  
    # print(limiter.strategy)
    # print(limiter.limit)
    # print(limiter.window_size)


    # Test 2
    # limiter.states[("client-A", "llm")] = deque()
    # limiter.states[("client-B", "llm")] = deque()

    # limiter.states[("client-A", "llm")].append(10)
    # limiter.states[("client-A", "llm")].append(14)

    # print(limiter.states)



    # Test 3
    # The output will be same only, because it refer to the same deque
    # state1 = limiter.get_state("client-A", "llm")

    # state1.append(10)
    # state1.append(15)

    # state2 = limiter.get_state("client-A", "llm")

    # print(state1)
    # print(state2)




    # Test 4 --> Test Isolation
    # The  output will be different since they are different deques or different client_id and resource
    # Now it met the independent state requirement from the problem statement
    # state1 = limiter.get_state("client-A", "llm")
    # state1.append(10)
    # state1.append(15)

    # state2 = limiter.get_state("client-B", "llm")
    # state2.append(20)

    # state3 = limiter.get_state("client-A", "embedding")
    # state3.append(30)

    # print(limiter.states)




    # Test 5
    # Test limit
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))

    # Test expiration
    # print("Request 1:", limiter.allow("client-A", "llm"))
    # print("Request 2:", limiter.allow("client-A", "llm"))
    # print("Request 3:", limiter.allow("client-A", "llm"))
    # print("Request 4:", limiter.allow("client-A", "llm"))

    # print("Waiting 10 seconds...")
    # time.sleep(10)
    # print("Request 5:", limiter.allow("client-A", "llm"))

    # Test Client are isolated
    # print("Client A:")
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))

    # print("\nClient B:")
    # print(limiter.allow("client-B", "llm"))
    # print(limiter.allow("client-B", "llm"))
    # print(limiter.allow("client-B", "llm"))
    # print(limiter.allow("client-B", "llm"))

    # Test that resources are isolated
    # print("Client A - LLM:")
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print(limiter.allow("client-A", "llm"))
    # print("Waiting 10 seconds...")
    # time.sleep(10)
    # print(limiter.allow("client-A", "llm"))

    # print("\nClient A - Embedding:")
    # print(limiter.allow("client-A", "embedding"))

    # print("State:",limiter.states)

    # Test 6 --> after adding bucket tokens
    sliding_limiter = RateLimiter(
        strategy="sliding_window",
        limit=3,
        window_size=10
    )
    bucket_limiter = RateLimiter(
        strategy="token_bucket",
        limit=3,
        window_size=10
    )

    
    print("--- Sliding Window Execution ---")
    print(sliding_limiter.allow("client-A", "llm"))  # Allowed (remaining: 1)
    print(sliding_limiter.allow("client-A", "llm"))  # Allowed (remaining: 0)
    print(sliding_limiter.allow("client-A", "llm"))  # Rejected (returns retry_after)
    
    # 2. Initialize Token Bucket Instance (Limit: 2 per 5 seconds)
    bucket_limiter = RateLimiter(strategy="token_bucket", limit=2, window_size=5)
    
    print("\n--- Token Bucket Execution ---")
    print(bucket_limiter.allow("client-A", "llm"))   # Allowed (remaining: 1)
    print(bucket_limiter.allow("client-A", "llm"))   # Allowed (remaining: 0)
    print(bucket_limiter.allow("client-A", "llm"))   # Rejected (returns retry_after until next partial token generation)
