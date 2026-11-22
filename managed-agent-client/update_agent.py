"""
Update Agent - Updates the managed agent's configuration.

Run this script to create a new version of your managed agent, with updated
instructions (system prompt), tools, and MCP servers. Sessions that start after
the update use the new version - the client app doesn't need to change.

Usage: python update_agent.py
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load the API key and agent ID from the .env file
load_dotenv()

# The agent's instructions
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
    "After downloading an image, briefly describe what it shows, and credit its author and license. "
    "When the user asks for a Wikipedia article, use the Wikipedia tools to find the most relevant "
    "English Wikipedia article, and get its introduction (section_index 0). "
    "Respond with the article's title as a heading, followed by the introduction text exactly as "
    "returned (leaving out any infobox data lines and notes such as 'For other uses, see...'), "
    "followed by a markdown link to the full article labeled 'Read the full article on Wikipedia', "
    "and finally the note 'Text from Wikipedia, available under the CC BY-SA 4.0 license.'"
)

# Define the MCP server that provides Wikipedia tools
# (Wikipedia MCP server by cyanheads: https://github.com/cyanheads/wikipedia-mcp-server)
MCP_SERVERS = [
    {"type": "url", "name": "wikipedia", "url": "https://wikipedia.caseyjhand.com/mcp"}
]

# Define the agent's tools
TOOLS = [
    # Built-in agent tools: enable only web search and web fetch, and allow them to run without approval
    {
        "type": "agent_toolset_20260401",
        "default_config": {"enabled": False},
        "configs": [
            {"name": "web_search", "enabled": True, "permission_policy": {"type": "always_allow"}},
            {"name": "web_fetch", "enabled": True, "permission_policy": {"type": "always_allow"}}
        ]
    },

    # Custom tool: the client app runs this when the agent asks it to
    {
        "type": "custom",
        "name": "download_image",
        "description": (
            "Downloads an openly licensed image from the web and saves it in the client app's downloads "
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

    # MCP toolset: Anthropic connects to the MCP server and runs its tools for the agent
    {
        "type": "mcp_toolset",
        "mcp_server_name": "wikipedia",
        # Only enable the tools that the agent needs, and allow them to run without approval
        "default_config": {"enabled": False},
        "configs": [
            {"name": "wikipedia_search_articles", "enabled": True, "permission_policy": {"type": "always_allow"}},
            {"name": "wikipedia_get_article", "enabled": True, "permission_policy": {"type": "always_allow"}}
        ]
    }
]


def main():
    # Create the Anthropic client
    client = Anthropic()

    # Update the agent, creating a new version
    agent = client.beta.agents.update(
        os.environ["AGENT_ID"],
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        mcp_servers=MCP_SERVERS,
    )
    print(f"Updated agent '{agent.name}' ({agent.id}) - it's now at version {agent.version}.")


if __name__ == "__main__":
    main()
