import os
import string
import sys
import datetime
import asyncio
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.openai.llm import OpenAILLMService
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.adapters.services.gemini_adapter import GeminiLLMAdapter
from pipecat.services.deepgram.tts import DeepgramTTSService
from demo.agent import root_agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.adk.agents.llm_agent import Agent
from pipecat_whisker import WhiskerObserver
from streaming_bridge import create_streaming_queue, get_streaming_queue, clear_streaming_queue


class AgentRunner:
    @staticmethod
    async def run_streaming(
        query: str,
        root_agent: Agent,
        queue_id: str
    ) -> str:
        """
        Run ADK agent with streaming queue configured in session state.

        Args:
            query: User's question
            root_agent: ADK agent to run
            queue_id: Unique queue ID for this invocation

        Returns:
            Final accumulated result text
        """
        runner = InMemoryRunner(agent=root_agent, app_name="my_app")

        # Create session with queue_id in state
        session = await runner.session_service.create_session(
            app_name="my_app",
            user_id="test_user",
            state={'streaming_queue_id': queue_id}  # KEY: Pass queue ID
        )

        logger.info(f"Session {session.id[:8]} using queue {queue_id[:8]}")

        result_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role='user', parts=[types.Part(text=query)])
        ):
            if event.content and event.content.parts:
                text = "".join(p.text for p in event.content.parts if p.text)
                if text:
                    logger.debug(f"[{event.author}]: {text}")
                    result_text += text

        return result_text



load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")
# Define a function using the standard schema
weather_function = FunctionSchema(
    name="get_current_weather",
    description="Get the current weather in a location",
    properties={
        "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
        },
        "format": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use.",
        },
    },
    required=["location", "format"]
)




SYSTEM_INSTRUCTION = f"""
"You are Gemini Chatbot, a friendly, helpful robot.

Your output will be converted to audio so don't include special characters in your answers.

Your job is to take the user's query and use the google_adk function to respond to the user.

"""


async def google_adk(params: FunctionCallParams, query: str, task: PipelineTask):
    '''
    Use this tool to get the secret code with real-time TTS streaming.
    Supports concurrent invocations with isolated queues.

    Args:
        params: Pipecat function call parameters
        query: The user's query
        task: Pipecat pipeline task for frame queueing
    '''
    logger.info(f"google_adk called with query: '{query}'")

    # Step 1: Create unique queue for THIS invocation
    queue_id = create_streaming_queue()
    queue = get_streaming_queue(queue_id)
    logger.info(f"Created queue {queue_id[:8]} for invocation")

    # Step 2: Start TTS monitor task (consumes from THIS queue only)
    async def tts_monitor():
        """Consume queue and speak via TTS with timeout protection."""
        item_count = 0
        while True:
            try:
                # Wait for next item with timeout
                text = await asyncio.wait_for(queue.get(), timeout=30.0)

                if text is None:  # Completion sentinel
                    logger.info(f"Queue {queue_id[:8]} received completion signal after {item_count} items")
                    break

                # Queue TTS frame
                logger.info(f"[Queue {queue_id[:8]}] Speaking: {text}")
                await task.queue_frames([TTSSpeakFrame(text=text)])
                item_count += 1

            except asyncio.TimeoutError:
                logger.warning(f"Queue {queue_id[:8]} timeout after {item_count} items")
                break
            except Exception as e:
                logger.error(f"Queue {queue_id[:8]} error: {e}")
                break

    monitor_task = asyncio.create_task(tts_monitor())

    # Step 3: Run ADK agent (tool will populate queue)
    try:
        result = await AgentRunner.run_streaming(query, root_agent, queue_id)
        logger.info(f"ADK returned: {result[:50]}...")

        # Wait for TTS monitor to finish speaking all queued items
        await asyncio.wait_for(monitor_task, timeout=60.0)

        # Return final result to LLM context
        await params.result_callback(result)

    except asyncio.TimeoutError:
        logger.error(f"Queue {queue_id[:8]} monitor timeout")
        await params.result_callback("Error: Streaming timeout")
    except Exception as e:
        logger.error(f"Queue {queue_id[:8]} error: {e}")
        await params.result_callback(f"Error: {str(e)}")
    finally:
        # Cleanup: Always remove queue from registry
        clear_streaming_queue(queue_id)
        logger.info(f"Cleaned up queue {queue_id[:8]}")


async def get_current_weather(params: FunctionCallParams, location: str, format: str):
    '''
    Use this tool to get the current weather for a location.
    location: The city and state, e.g. San Francisco, CA
    format: One of "celsius" or "fahrenheit"
    '''
    logger.info(f"Get Current Weather called with location={location}, format={format}")
    # Dummy implementation; replace with real weather lookup as needed
    if format.lower() == "celsius":
        result = f"In {location}, it's 22°C and clear."
    else:
        result = f"In {location}, it's 72°F and clear."
    await params.result_callback(result)


# Define google_adk schema
google_adk_schema = FunctionSchema(
    name="google_adk",
    description="Get the secret code by querying the ADK agent. This tool streams results progressively.",
    properties={
        "query": {
            "type": "string",
            "description": "The user's question or query to send to the agent",
        },
    },
    required=["query"]
)

tools = ToolsSchema(standard_tools=[weather_function, google_adk_schema])

async def run_bot(websocket_client):
  


    ws_transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=ProtobufFrameSerializer(),
        ),
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o-mini", system_instruction=SYSTEM_INSTRUCTION)

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-2-helena-en",
    )

    context = OpenAILLMContext(
        [
            {
                "role": "system",
                "content": " you are gemma who does only 1 job:- use the google_adk function to tell the time and use the get_current_weather function to get the weather.",
            },
            {
                "role": "user",
                "content": "can you tell the secret code ?",
            }

        ],
        tools=tools,
    )
    context_aggregator = llm.create_context_aggregator(context)

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            ws_transport.input(),
            stt,
            context_aggregator.user(),
            rtvi,
            llm,
            tts,
            ws_transport.output(),
            context_aggregator.assistant(),
        ]
    )
    whisker = WhiskerObserver(pipeline)
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi),whisker],
    )

    # Define handler with access to task (closure)
    async def handle_tool_function(params: FunctionCallParams):
        """Dispatch function calls with task access."""
        function_name = params.function_name
        args = params.arguments or {}

        if function_name == "google_adk":
            # Pass task to google_adk
            await google_adk(params=params, query=args.get("query", ""), task=task)
            return

        if function_name == "get_current_weather":
            await get_current_weather(
                params=params,
                location=args.get("location", ""),
                format=args.get("format", "celsius"),
            )
            return

        await params.result_callback(f"Unknown function: {function_name}")

    # Register handlers
    llm.register_function("google_adk", handle_tool_function)
    llm.register_function("get_current_weather", handle_tool_function)

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        # Kick off the conversation.
        await task.queue_frames([LLMRunFrame()])

    @ws_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Pipecat Client connected")

    @ws_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)