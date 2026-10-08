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
            # self.states
            # │
            # └── ("client-A", "llm") → deque([])
            self.states[key] = deque()

        # Return that deque
        return self.states[key]

    def allow(self, client_id, resource):
        # Step 1: Get the isolated state(list of timestamps)
        timestamps = self.get_state(client_id, resource)
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
            "retry_after": retry_after
        }


    
# Tiny experiment
if __name__ == "__main__":
    limiter = RateLimiter(
        strategy="sliding_window",
        limit=3,
        window_size=10
    )
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
    print("Client A - LLM:")
    print(limiter.allow("client-A", "llm"))
    print(limiter.allow("client-A", "llm"))
    print(limiter.allow("client-A", "llm"))
    print(limiter.allow("client-A", "llm"))
    print("Waiting 10 seconds...")
    time.sleep(10)
    print(limiter.allow("client-A", "llm"))

    print("\nClient A - Embedding:")
    print(limiter.allow("client-A", "embedding"))

    print("State:",limiter.states)