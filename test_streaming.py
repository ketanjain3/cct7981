#!/usr/bin/env python3
"""
Simple test to verify streaming bridge functionality.
"""
import asyncio
from streaming_bridge import (
    create_streaming_queue,
    get_streaming_queue,
    clear_streaming_queue,
    get_active_queue_count
)


async def test_basic_queue_operations():
    """Test basic queue creation, retrieval, and cleanup."""
    print("Test 1: Basic Queue Operations")

    # Create queue
    queue_id = create_streaming_queue()
    assert queue_id is not None, "Queue ID should not be None"
    print(f"✓ Created queue: {queue_id[:8]}...")

    # Retrieve queue
    queue = get_streaming_queue(queue_id)
    assert queue is not None, "Queue should be retrievable"
    print(f"✓ Retrieved queue successfully")

    # Check active count
    assert get_active_queue_count() == 1, "Should have 1 active queue"
    print(f"✓ Active queue count: {get_active_queue_count()}")

    # Clear queue
    clear_streaming_queue(queue_id)
    assert get_streaming_queue(queue_id) is None, "Queue should be cleared"
    assert get_active_queue_count() == 0, "Should have 0 active queues"
    print(f"✓ Cleared queue successfully\n")


async def test_queue_isolation():
    """Test that multiple queues are isolated."""
    print("Test 2: Queue Isolation")

    # Create two queues
    queue_id_a = create_streaming_queue()
    queue_id_b = create_streaming_queue()

    queue_a = get_streaming_queue(queue_id_a)
    queue_b = get_streaming_queue(queue_id_b)

    assert queue_a is not queue_b, "Queues should be different objects"
    print(f"✓ Created two isolated queues: {queue_id_a[:8]}... and {queue_id_b[:8]}...")

    # Put different items
    await queue_a.put("Item A")
    await queue_b.put("Item B")

    # Retrieve from correct queues
    item_a = await queue_a.get()
    item_b = await queue_b.get()

    assert item_a == "Item A", "Queue A should return Item A"
    assert item_b == "Item B", "Queue B should return Item B"
    print(f"✓ Queue isolation verified: A='{item_a}', B='{item_b}'")

    # Cleanup
    clear_streaming_queue(queue_id_a)
    clear_streaming_queue(queue_id_b)
    print(f"✓ Cleaned up both queues\n")


async def test_queue_communication():
    """Test producer-consumer pattern through queue."""
    print("Test 3: Producer-Consumer Pattern")

    queue_id = create_streaming_queue()
    queue = get_streaming_queue(queue_id)

    # Producer task
    async def producer():
        for i in range(3):
            await asyncio.sleep(0.1)
            await queue.put(f"Message {i+1}")
            print(f"  Producer: Sent 'Message {i+1}'")
        await queue.put(None)  # Sentinel
        print(f"  Producer: Sent completion signal")

    # Consumer task
    async def consumer():
        messages = []
        while True:
            msg = await queue.get()
            if msg is None:
                print(f"  Consumer: Received completion signal")
                break
            messages.append(msg)
            print(f"  Consumer: Received '{msg}'")
        return messages

    # Run both concurrently
    producer_task = asyncio.create_task(producer())
    consumer_task = asyncio.create_task(consumer())

    await producer_task
    messages = await consumer_task

    assert len(messages) == 3, "Should receive 3 messages"
    assert messages == ["Message 1", "Message 2", "Message 3"], "Messages should match"
    print(f"✓ Producer-consumer pattern works correctly\n")

    clear_streaming_queue(queue_id)


async def main():
    """Run all tests."""
    print("=" * 60)
    print("STREAMING BRIDGE TESTS")
    print("=" * 60 + "\n")

    try:
        await test_basic_queue_operations()
        await test_queue_isolation()
        await test_queue_communication()

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
