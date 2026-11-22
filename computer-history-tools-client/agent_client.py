"""
Agent Client - Handles interaction with the Claude-based computing historian agent.

This module contains the core logic for the agent. It uses the Anthropic SDK
to call the Claude Messages API, running an agent loop that submits prompts
(with conversation history), lets Claude use built-in (server-side) tools and
custom (client-side) tools, and returns the final response.
"""

import os
import re
import html
import json
import uuid
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Import the Anthropic client library
from anthropic import Anthropic


# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Downloaded images are saved in the /downloads folder of this app
DOWNLOADS_FOLDER = Path(__file__).parent / "downloads"

# Image downloads: supported types (and the file extension to save them with), and the maximum size
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Many image sites (including Wikimedia Commons) reject requests that don't identify the client
# with a name and a contact URL
USER_AGENT = "ComputingHistoryAgent/1.0 (https://github.com/GraemeMalcolm/claude-labs)"


def fetch_image(url: str) -> Tuple[bytes, str]:
    """
    Helper function: download an image from a URL, and return its bytes and media type.

    If the URL is a web page rather than an image file, the page's main image
    (declared in its og:image metadata) is downloaded instead.
    """
    for _ in range(2):
        if urllib.parse.urlparse(url).scheme not in ("http", "https"):
            raise ValueError("Only http and https URLs can be downloaded.")

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            media_type = response.headers.get_content_type()
            data = response.read(MAX_IMAGE_BYTES + 1)

        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("The image is larger than 5 MB.")

        if media_type in IMAGE_TYPES:
            return data, media_type

        # Not an image - if it's a web page, look for its main image and try again
        if media_type == "text/html":
            match = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                data.decode("utf-8", errors="ignore"),
            )
            if match:
                url = urllib.parse.urljoin(url, html.unescape(match.group(1)))
                continue

        break

    raise ValueError(f"The URL returned '{media_type}' content, not a supported image file.")


# Define the agent's instructions (system prompt) and tools
SYSTEM_PROMPT = (
    "You are an expert in the history of computing and AI. "
    "You only answer questions about significant people and events in the development "
    "of computing, and about notable vintage computers. "
    "Do not engage in conversations on any topic that is unrelated to computing history."
)

TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
]


# Implement the custom tool function




class AgentClient:
    """Client for interacting with the computing historian agent."""

    def __init__(self):
        """Initialize the agent client with authentication and model."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")

        # Create the Anthropic client
        self.client = Anthropic()

        # Maintain conversation history (last 3 exchanges)
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history = 3

        # Safety limit on the number of model calls in a single agent loop
        self.max_turns = 5

        # Track the images downloaded while responding to the latest message




    # Run a custom tool that Claude requested




    def send_message(self, user_message: str, image: Optional[Dict[str, str]] = None) -> str:
        """
        Send a message to the agent and return the response.

        Args:
            user_message: The text message from the user
            image: Optional image to send with the message, as a dict with
                   "media_type" (e.g. "image/png") and "data" (base64-encoded bytes)

        Returns:
            The agent's response text. Details of any images the agent downloaded
            are available in the downloaded_images attribute.
        """
        # Build the user's content: plain text, or an image block followed by the text block
        if image:
            content: Any = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image["media_type"],
                        "data": image["data"],
                    },
                },
                {"type": "text", "text": user_message},
            ]
        else:
            content = user_message

        # Add current user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": content
        })

        # Clear the list of images downloaded for the previous message



        try:
            # Initialize assistant message variable
            assistant_message = ""

            # Run the agent loop
            messages = list(self.conversation_history)
            for _ in range(self.max_turns):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=16000,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages
                )

                # If Claude paused while using a server-side tool, send its progress back so it can continue
                if response.stop_reason == "pause_turn":
                    messages.append({"role": "assistant", "content": response.content})
                    continue

                # If Claude wants to use a custom tool, run it and send the results back




                # Otherwise, Claude has finished
                break

            # The response contains multiple content blocks (for example, web searches and results);
            # the text blocks make up the answer
            assistant_message = "".join(
                block.text for block in response.content if block.type == "text"
            )

            if response.stop_reason == "refusal":
                assistant_message = "I'm unable to help with that request."
            elif not assistant_message:
                assistant_message = "Sorry, I wasn't able to complete that request. Please try again."

            # Add assistant response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Count user messages in history to enforce max_history limit
            user_message_count = sum(1 for msg in self.conversation_history
                                    if isinstance(msg, dict) and msg.get("role") == "user")

            # Remove oldest exchanges if we have more than max_history
            while user_message_count > self.max_history:
                # Find and remove the first user message and its assistant response
                for i, msg in enumerate(self.conversation_history):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        self.conversation_history.pop(i)
                        if i < len(self.conversation_history) and self.conversation_history[i].get("role") == "assistant":
                            self.conversation_history.pop(i)
                        user_message_count -= 1
                        break

            return assistant_message

        except Exception as e:
            logger.exception("Error communicating with agent")
            return "An internal error occurred while communicating with the agent."

    def reset_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []
