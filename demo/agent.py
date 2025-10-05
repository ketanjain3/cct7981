from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path to import streaming_bridge
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streaming_bridge import get_task
from pipecat.frames.frames import TTSSpeakFrame
from loguru import logger


load_dotenv()


async def streaming_tool(tool_context: ToolContext) -> str:
    """
    Streaming tool that speaks digits progressively via TTS.
    Calls Pipecat task directly - no queue complexity!

    Args:
        tool_context: ADK tool context with session state access

    Returns:
        str: Final result message
    """
    # Get task ID from session state (primitive survives deepcopy!)
    task_id = tool_context.state.get('task_id')

    if not task_id:
        error_msg = "Error: No task ID configured"
        logger.error(error_msg)
        return error_msg

    # Retrieve task from global registry
    task = get_task(task_id)
    if not task:
        error_msg = f"Error: Task {task_id[:8]}... not found"
        logger.error(error_msg)
        return error_msg

    logger.info(f"Tool using task: {task_id[:8]}...")

    # Progressive computation with direct TTS calls
    code = "1234"
    for i, digit in enumerate(code):
        await asyncio.sleep(0.3)  # Simulate processing time

        text = f"Digit {i+1} is {digit}"
        logger.info(f"[Task {task_id[:8]}] Speaking: {text}")

        # DIRECT CALL - No queue, no monitor, no sentinel!
        await task.queue_frames([TTSSpeakFrame(text=text)])

    final_msg = "Secret code retrieval complete!"
    logger.info(f"[Task {task_id[:8]}] Complete")
    return final_msg


# Configure agent with streaming tool
root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[streaming_tool],
)
