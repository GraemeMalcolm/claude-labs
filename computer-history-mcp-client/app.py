"""
Flask Application for Computing History Agent Client.

This is the main Flask application that provides a web interface
for interacting with the Computing History agent.
"""

import base64
import binascii

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import markdown
import bleach
from agent_client import AgentClient, DOWNLOADS_FOLDER

app = Flask(__name__)

# Image attachments: PNG and JPEG only, up to 5 MB decoded
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/png', 'image/jpeg'}
# Leave room for base64 overhead (about 4/3 of the file size) plus the text prompt
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

# First bytes of each supported format, to check the file really is what it claims to be
IMAGE_SIGNATURES = {
    'image/png': b'\x89PNG\r\n\x1a\n',
    'image/jpeg': b'\xff\xd8\xff',
}


def _validate_image(image: dict):
    """
    Validate an uploaded image sent as {'media_type': ..., 'data': <base64>}.

    Returns (cleaned_image, None) if valid, or (None, error_message) if not.
    """
    media_type = image.get('media_type', '')
    if media_type not in ALLOWED_IMAGE_TYPES:
        return None, 'Unsupported image type. Please attach a PNG or JPEG image.'

    try:
        raw_bytes = base64.b64decode(image.get('data', ''), validate=True)
    except (binascii.Error, ValueError, TypeError):
        return None, 'The image data could not be read. Please attach the image again.'

    if len(raw_bytes) > MAX_IMAGE_BYTES:
        return None, 'The image is larger than 5 MB. Please attach a smaller image.'

    if not raw_bytes.startswith(IMAGE_SIGNATURES[media_type]):
        return None, 'The file does not appear to be a valid PNG or JPEG image.'

    return {'media_type': media_type, 'data': image['data']}, None


def _set_external_link_attributes(attrs, new=False):
    """Force safe external link attributes for rendered markdown links."""
    href_key = (None, 'href')
    href_value = attrs.get(href_key, '')
    if isinstance(href_value, str) and href_value.startswith(('http://', 'https://')):
        attrs[(None, 'target')] = '_blank'
        attrs[(None, 'rel')] = 'noopener noreferrer nofollow'
    return attrs


def render_markdown_to_safe_html(text: str) -> str:
    """Convert markdown to safe HTML for display in chat bubbles."""
    raw_html = markdown.markdown(
        text,
        extensions=['extra', 'sane_lists', 'nl2br']
    )

    allowed_tags = [
        'p', 'br', 'hr', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'strong', 'em', 'code', 'pre',
        'a',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    allowed_attrs = {
        'a': ['href', 'title', 'target', 'rel'],
        'code': ['class']
    }

    safe_html = bleach.clean(
        raw_html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=['http', 'https', 'mailto'],
        strip=True
    )

    # Linkify plain URLs while leaving code blocks untouched.
    safe_html = bleach.linkify(
        safe_html,
        skip_tags=['pre', 'code'],
        callbacks=[_set_external_link_attributes]
    )
    return safe_html

# Initialize the agent client
try:
    agent = AgentClient()
except Exception as e:
    print(f"Warning: Failed to initialize agent client: {e}")
    agent = None

@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from the user."""
    if not agent:
        return jsonify({
            'error': 'Agent client not initialized. Check your .env configuration.'
        }), 500
    
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Validate message length to prevent abuse
    if len(user_message) > 10000:
        return jsonify({'error': 'Message too long'}), 400

    # Optional image attachment
    image = None
    if data.get('image'):
        image, image_error = _validate_image(data['image'])
        if image_error:
            return jsonify({'error': image_error}), 400

    # Note: We do NOT escape HTML here because:
    # 1. The agent needs to receive the raw text to understand it properly
    # 2. HTML escaping is performed on the frontend when displaying messages
    # 3. This follows the principle: escape at the point of use (display), not at input
    response = agent.send_message(user_message, image=image)
    response_html = render_markdown_to_safe_html(response)

    # Add the details of any images the agent downloaded, with the URL to display each one
    images = [
        {**image, 'url': url_for('downloaded_image', filename=image['filename'])}
        for image in agent.downloaded_images
    ]

    return jsonify({
        'response': response,
        'response_html': response_html,
        'images': images
    })

@app.route('/downloads/<path:filename>')
def downloaded_image(filename):
    """Serve an image from the downloads folder."""
    return send_from_directory(DOWNLOADS_FOLDER, filename)

@app.route('/reset', methods=['POST'])
def reset():
    """Reset the conversation history."""
    if agent:
        agent.reset_conversation()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=False, port=5000)
