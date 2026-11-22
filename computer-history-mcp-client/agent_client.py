"""
Agent Client - Handles interaction with the Claude-based computing historian agent.

This module contains the core logic for the agent. It uses the Anthropic SDK
to call the Claude Messages API, running an agent loop that submits prompts
(with conversation history), lets Claude use built-in (server-side) tools,
custom (client-side) tools, and tools from a remote MCP server, and returns
the final response.
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
    "Do not engage in conversations on any topic that is unrelated to computing history. "
    "When the user asks to see an image of a historic computer, hardware component, or person, "
    "use web search to find a relevant image that is in the public domain or released under a "
    "Creative Commons license (Wikimedia Commons is a good source). "
    "Then use the download_image tool to save the image for the user. "
    "Never download an image unless the search results show that its license permits reuse. "
    "After downloading an image, briefly describe what it shows, and credit its author and license."
)

# Define the MCP server that provides Wikipedia tools




TOOLS = [
    # Built-in (server-side) tool: Anthropic runs this for you
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 5},

    # Custom (client-side) tool: your code runs this when Claude asks it to
    {
        "name": "download_image",
        "description": (
            "Downloads an openly licensed image from the web and saves it in the app's downloads "
            "folder, so that it can be displayed to the user. Only use this tool for images that are "
            "in the public domain or released under a Creative Commons license. Images must be JPEG, "
            "PNG, GIF, or WebP files of up to 5 MB. Returns the saved file's details as JSON, or an "
            "error message if the image can't be downloaded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": (
                        "The URL of the image's web page (for example, a Wikimedia Commons file page "
                        "such as https://commons.wikimedia.org/wiki/File:Example.jpg), or the URL of the image file."
                    )
                },
                "title": {
                    "type": "string",
                    "description": "A short title describing the image (for example, 'Altair 8800 computer')."
                },
                "author": {
                    "type": "string",
                    "description": "The author or creator of the image, as stated on its source page."
                },
                "license": {
                    "type": "string",
                    "description": "The image's license (for example, 'CC BY-SA 4.0' or 'Public domain')."
                },
                "source_page_url": {
                    "type": "string",
                    "description": "The URL of the web page where the image and its license are described."
                }
            },
            "required": ["image_url", "title", "author", "license", "source_page_url"]
        }
    },

    # MCP toolset: Anthropic connects to the MCP server and runs its tools for you



]


# Implement the custom tool function
def download_image(image_url: str, title: str, author: str, license: str, source_page_url: str) -> Dict[str, str]:
    """Download an image, save it in the downloads folder, and return its details."""
    data, media_type = fetch_image(image_url)

    # Create a safe, unique file name from the title (never trust a file name from the web)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "image"
    filename = f"{slug}-{uuid.uuid4().hex[:8]}{IMAGE_TYPES[media_type]}"

    DOWNLOADS_FOLDER.mkdir(exist_ok=True)
    (DOWNLOADS_FOLDER / filename).write_bytes(data)
    logger.info("Downloaded %s to %s", image_url, filename)

    return {
        "filename": filename,
        "title": title,
        "author": author,
        "license": license,
        "source_page_url": source_page_url,
    }


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
        self.max_turns = 10

        # Track the images downloaded while responding to the latest message
        self.downloaded_images: List[Dict[str, str]] = []

    # Run a custom tool that Claude requested
    def run_tool(self, tool_use) -> Dict[str, Any]:
        """Run a custom tool that Claude requested, and return a tool_result content block."""
        try:
            if tool_use.name == "download_image":
                image = download_image(**tool_use.input)
                self.downloaded_images.append(image)
                result = json.dumps(image)
            else:
                raise ValueError(f"Unknown tool: {tool_use.name}")

            return {"type": "tool_result", "tool_use_id": tool_use.id, "content": result}

        except Exception as e:
            # Tell Claude the tool failed, so it can try something else (such as a different image)
            logger.warning("Tool %s failed: %s", tool_use.name, e)
            return {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": f"Error: {e}",
                "is_error": True,
            }

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
        self.downloaded_images = []

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
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    tool_results = [
                        self.run_tool(block) for block in response.content if block.type == "tool_use"
                    ]
                    messages.append({"role": "user", "content": tool_results})
                    continue

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
