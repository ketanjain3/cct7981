#!/usr/bin/env python3
"""
Simple test to verify simplified streaming bridge functionality.
"""
import asyncio
from streaming_bridge import (
    register_task,
    get_task,
    unregister_task,
    get_active_task_count
)


class MockTask:
    """Mock PipelineTask for testing."""
    def __init__(self, name):
        self.name = name
        self.frames_queued = []

    async def queue_frames(self, frames):
        """Mock queue_frames method."""
        self.frames_queued.extend(frames)
        print(f"  Task '{self.name}' queued {len(frames)} frame(s)")


async def test_basic_task_operations():
    """Test basic task registration, retrieval, and cleanup."""
    print("Test 1: Basic Task Operations")

    # Create mock task
    mock_task = MockTask("test_task")

    # Register task
    task_id = register_task(mock_task)
    assert task_id is not None, "Task ID should not be None"
    print(f"✓ Registered task: {task_id[:8]}...")

    # Retrieve task
    retrieved_task = get_task(task_id)
    assert retrieved_task is mock_task, "Should retrieve same task instance"
    print(f"✓ Retrieved task successfully")

    # Check active count
    assert get_active_task_count() == 1, "Should have 1 active task"
    print(f"✓ Active task count: {get_active_task_count()}")

    # Unregister task
    unregister_task(task_id)
    assert get_task(task_id) is None, "Task should be unregistered"
    assert get_active_task_count() == 0, "Should have 0 active tasks"
    print(f"✓ Unregistered task successfully\n")


async def test_task_isolation():
    """Test that multiple tasks are isolated."""
    print("Test 2: Task Isolation")

    # Register two tasks
    task_a = MockTask("Task A")
    task_b = MockTask("Task B")

    task_id_a = register_task(task_a)
    task_id_b = register_task(task_b)

    retrieved_a = get_task(task_id_a)
    retrieved_b = get_task(task_id_b)

    assert retrieved_a is task_a, "Should retrieve Task A"
    assert retrieved_b is task_b, "Should retrieve Task B"
    assert retrieved_a is not retrieved_b, "Tasks should be different"
    print(f"✓ Registered two isolated tasks: {task_id_a[:8]}... and {task_id_b[:8]}...")

    # Simulate different operations on each
    await task_a.queue_frames(["Frame A1", "Frame A2"])
    await task_b.queue_frames(["Frame B1"])

    assert len(task_a.frames_queued) == 2, "Task A should have 2 frames"
    assert len(task_b.frames_queued) == 1, "Task B should have 1 frame"
    print(f"✓ Task isolation verified: A has {len(task_a.frames_queued)} frames, B has {len(task_b.frames_queued)} frames")

    # Cleanup
    unregister_task(task_id_a)
    unregister_task(task_id_b)
    print(f"✓ Cleaned up both tasks\n")


async def test_concurrent_task_usage():
    """Test concurrent tool execution with isolated tasks."""
    print("Test 3: Concurrent Tool Execution Pattern")

    # Simulate what happens when tool executes
    async def simulate_tool_execution(task_id, tool_name):
        """Simulate streaming tool execution."""
        task = get_task(task_id)
        if not task:
            print(f"  {tool_name}: Error - task not found!")
            return

        print(f"  {tool_name}: Starting execution")
        for i in range(3):
            await asyncio.sleep(0.05)  # Simulate work
            frame_text = f"{tool_name} - Item {i+1}"
            await task.queue_frames([frame_text])
        print(f"  {tool_name}: Complete")

    # Register tasks for two concurrent "users"
    task_user_a = MockTask("User A")
    task_user_b = MockTask("User B")

    id_a = register_task(task_user_a)
    id_b = register_task(task_user_b)

    print(f"  Registered tasks for User A ({id_a[:8]}) and User B ({id_b[:8]})")

    # Run tools concurrently
    await asyncio.gather(
        simulate_tool_execution(id_a, "Tool A"),
        simulate_tool_execution(id_b, "Tool B")
    )

    # Verify isolation
    assert len(task_user_a.frames_queued) == 3, "User A should have 3 frames"
    assert len(task_user_b.frames_queued) == 3, "User B should have 3 frames"

    # Verify no cross-contamination
    a_frames = [f for f in task_user_a.frames_queued if "Tool A" in f]
    b_frames = [f for f in task_user_b.frames_queued if "Tool B" in f]

    assert len(a_frames) == 3, "User A should only have Tool A frames"
    assert len(b_frames) == 3, "User B should only have Tool B frames"
    print(f"✓ Concurrent execution verified: No cross-contamination")

    # Cleanup
    unregister_task(id_a)
    unregister_task(id_b)
    print(f"✓ Cleaned up both tasks\n")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("SIMPLIFIED STREAMING BRIDGE TESTS")
    print("=" * 60 + "\n")

    try:
        await test_basic_task_operations()
        await test_task_isolation()
        await test_concurrent_task_usage()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
