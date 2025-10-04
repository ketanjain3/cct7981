from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path to import streaming_bridge
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming_bridge import get_streaming_queue
from loguru import logger


load_dotenv()


async def streaming_tool(tool_context: ToolContext) -> str:
    """
    Streaming tool that sends secret code digits progressively to TTS.
    Uses queue bridge to send interim results to Pipecat.

    Args:
        tool_context: ADK tool context with session state access

    Returns:
        str: Final result message
    """
    # Get queue ID from session state (primitive survives deepcopy!)
    queue_id = tool_context.state.get('streaming_queue_id')

    if not queue_id:
        error_msg = "Error: No streaming queue configured"
        logger.error(error_msg)
        return error_msg

    # Retrieve the queue from global registry
    queue = get_streaming_queue(queue_id)
    if not queue:
        error_msg = f"Error: Streaming queue {queue_id[:8]}... not found"
        logger.error(error_msg)
        return error_msg

    logger.info(f"Tool using queue: {queue_id[:8]}...")

    # Simulate progressive computation
    code = "1234"
    for i, digit in enumerate(code):
        await asyncio.sleep(0.3)  # Simulate processing time

        interim_text = f"Digit {i+1} is {digit}"
        logger.info(f"[Queue {queue_id[:8]}] Sending: {interim_text}")

        # Send to Pipecat TTS queue (non-blocking)
        try:
            await asyncio.wait_for(queue.put(interim_text), timeout=1.0)
        except asyncio.TimeoutError:
            logger.error(f"Queue {queue_id[:8]} put timeout")

    # Send completion sentinel
    try:
        await asyncio.wait_for(queue.put(None), timeout=1.0)
    except asyncio.TimeoutError:
        logger.error(f"Queue {queue_id[:8]} completion signal timeout")

    final_msg = "Secret code retrieval complete!"
    logger.info(f"[Queue {queue_id[:8]}] Complete")
    return final_msg


# Configure agent with streaming tool
root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[streaming_tool],
)
