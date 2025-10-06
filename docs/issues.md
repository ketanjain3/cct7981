
  1. Memory Leak from Stale Task Registrations
   * Problem: If a tool execution fails to reach the finally block where unregister_task is called,
     the task object remains in the global _tasks dictionary. This can happen if the process crashes,
     a task hangs indefinitely, or an unhandled exception bypasses the cleanup logic.
   * Production Impact: In a high-traffic environment with many users, even a small rate of failures
     will cause the _tasks dictionary to grow unbounded. This guarantees a memory leak, which will
     eventually consume all available RAM, leading to server slowdowns, crashes, and downtime for all 
     users. It is the most critical stability risk.


  2. Race Conditions in the Global Task Registry
   * Problem: The _tasks dictionary is a shared, global object that is not protected by a lock. With
     many users and tools operating concurrently, there is a high probability of simultaneous
     read/write operations (e.g., one user's tool starting while another's is ending).
   * Production Impact: This can lead to a state of Heisenbugs—intermittent and unpredictable errors
     that are notoriously difficult to reproduce and debug in a live environment. Potential outcomes
     include data corruption within the registry, KeyError exceptions from trying to unregister a
     task that was just overwritten, or one user's tool inadvertently getting the task object of
     another user. This undermines the reliability of the entire system.


  3. Unhandled Tool Timeouts and Hanging Processes
   * Problem: A single streaming tool that hangs—due to a slow external API call, an infinite loop,
     or a deadlock—will hold its associated Pipecat pipeline and resources indefinitely. There is
     currently no timeout mechanism to preemptively kill a misbehaving tool.
   * Production Impact: A hanging tool will not only result in a very poor experience for the
     affected user but can also tie up server resources (CPU, memory, open connections). In a
     resource-constrained environment, a few misbehaving tools could degrade the performance for all
     other users, a phenomenon known as a "noisy neighbor" problem.


  4. Cascading Failures from Inadequate Error Isolation
   * Problem: The current error handling is basic. A tool might fail in a way that isn't a standard
     Exception or might return a malformed result that the calling function (google_adk) doesn't know
     how to handle, causing the parent task itself to crash.
   * Production Impact: With multiple tools, some of which may have dependencies on others, one tool's
      crash can trigger a cascading failure that brings down a user's entire session pipeline. If this
      happens frequently, the system will appear unstable and unreliable to users, even if the root
     cause is isolated to a single, poorly written tool.


  5. Lack of Monitoring and Debugging for a "Black Box"
   * Problem: When a tool fails to stream, there is very little visibility into why. Was the task not
     found? Did the tool silently fail? Is it just running slowly? The logging is helpful but isn't
     aggregated or structured for easy production monitoring.
   * Production Impact: When users report issues, the support and engineering teams will have a very
     difficult time diagnosing the root cause. This leads to longer incident response times and an
     inability to proactively detect when a specific tool is causing a high error rate. Without
     metrics on task registration, cleanup, and failures, you are flying blind.


