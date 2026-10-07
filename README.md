Rate Limiter

Background
Build an in-memory rate limiter for an LLM API gateway where multiple clients share API resources. The limiter must prevent a single client from consuming excessive capacity while safely handling concurrent requests and shared state.

Task
Implement a rate limiter with two configurable strategies: Sliding Window and Token Bucket. The limiter should maintain independent state for each client and resource, correctly determine whether each request should be accepted, and return the remaining capacity and estimated recovery time. The implementation must also maintain accurate statistics and remain correct under concurrent access.

What This Problem Tests
Implementing Sliding Window and Token Bucket rate-limiting algorithms
Handling time-based expiration and continuous token refills
Managing shared state and thread safety in a concurrent environment
Applying basic locking and synchronization mechanisms
Maintaining isolated state across clients and resources
Handling edge cases such as rejected requests, exhausted capacity, and partial recovery
Translating detailed algorithmic requirements into a reliable engineering implementation

<!-- Allow step by step execution -->

Request 1: Happens at t = 2 seconds

1. timestamps = get_state("client-A", "llm")
	• Fetches the current list: []
2. current_time = 2
3. expiry_time = 2 - 10 \(\rightarrow \) -8
4. while timestamps and timestamps[0] <= expiry_time:
	• The list is empty, so this loop is skipped. No timestamps are removed.
5. if len(timestamps) < limit:
	• Is 0 < 3? Yes (True).
6. timestamps.append(2)
	• The list becomes [2].
7. Result: Returns True (Request Allowed).

Request 2: Happens at t = 5 seconds

1. timestamps = get_state("client-A", "llm")
	• Fetches the list: [2]
2. current_time = 5
3. expiry_time = 5 - 10 \(\rightarrow \) -5
4. while timestamps and timestamps[0] <= expiry_time:
	• Is 2 <= -5? No. The loop terminates. No timestamps are removed.
5. if len(timestamps) < limit:
	• Is 1 < 3? Yes (True).
6. timestamps.append(5)
	• The list becomes [2, 5].
7. Result: Returns True (Request Allowed).

Request 3: Happens at t = 8 seconds

1. timestamps = get_state("client-A", "llm")
	• Fetches the list: [2, 5]
2. current_time = 8
3. expiry_time = 8 - 10 \(\rightarrow \) -2
4. while timestamps and timestamps[0] <= expiry_time:
	• Is 2 <= -2? No. The loop terminates.
5. if len(timestamps) < limit:
	• Is 2 < 3? Yes (True).
6. timestamps.append(8)
	• The list becomes [2, 5, 8].
7. Result: Returns True (Request Allowed).

Request 4: Happens at t = 11 seconds (The Limit Test)

Notice that the very first request (t = 2) is still inside the 10-second window because 11 - 2 = 9 seconds (less than 10).
1. timestamps = get_state("client-A", "llm")
	• Fetches the list: [2, 5, 8]
2. current_time = 11
3. expiry_time = 11 - 10 \(\rightarrow \) 1
4. while timestamps and timestamps[0] <= expiry_time:
	• Is 2 <= 1? No. The loop terminates. Nothing is expired yet.
5. if len(timestamps) < limit:
	• Is 3 < 3? No (False).
6. Execution jumps to return False.
7. Result: Returns False (Request Rejected / Rate Limited).

Request 5: Happens at t = 13 seconds (The Sliding Window Clean)

Now, let's see how the window slides and cleans up old data.
1. timestamps = get_state("client-A", "llm")
	• Fetches the list: [2, 5, 8]
2. current_time = 13
3. expiry_time = 13 - 10 \(\rightarrow \) 3
4. while timestamps and timestamps[0] <= expiry_time:
	• Iteration 1: timestamps[0] is 2. Is 2 <= 3? Yes.
		• timestamps.pop(0) removes 2. The list is now [5, 8].
	• Iteration 2: timestamps[0] is now 5. Is 5 <= 3? No. The loop stops.
5. if len(timestamps) < limit:
	• Is 2 < 3? Yes (True).
6. timestamps.append(13)
	• The list becomes [5, 8, 13].
7. Result: Returns True (Request Allowed again because t=2 dropped off!).
