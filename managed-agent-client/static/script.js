// DOM elements
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const resetBtn = document.getElementById('resetBtn');
const attachBtn = document.getElementById('attachBtn');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const imagePreviewImg = document.getElementById('imagePreviewImg');
const removeImageBtn = document.getElementById('removeImageBtn');
const imageError = document.getElementById('imageError');

// Image attachment limits (must match the server)
const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg'];
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

// The currently selected image, or null: { mediaType, dataUrl, base64 }
let selectedImage = null;

// Event listeners
sendBtn.addEventListener('click', sendMessage);
attachBtn.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', handleImageSelected);
removeImageBtn.addEventListener('click', () => {
    clearSelectedImage();
    attachBtn.focus();
});
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
resetBtn.addEventListener('click', resetConversation);

// Keyboard accessibility: Allow Space key to activate buttons
sendBtn.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        resetConversation();
    }
});

// Functions
function sendMessage() {
    const message = messageInput.value.trim();

    // A prompt must contain text; an image is optional
    if (!message) {
        return;
    }

    // Keep a reference to the image being sent so it can be restored if the request fails
    const image = selectedImage;

    // Clear welcome message if present
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    // Add user message to chat (with the image, if one is attached)
    addMessage(message, 'user', { imageUrl: image ? image.dataUrl : null });

    // Clear input
    messageInput.value = '';

    // Disable input while processing
    setInputDisabled(true);

    // Show typing indicator
    const typingIndicator = addTypingIndicator();

    // Send to server
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            image: image ? { media_type: image.mediaType, data: image.base64 } : null
        })
    })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            typingIndicator.remove();

            if (data.error) {
                // Put the prompt and image back so the user can try again
                restoreFailedPrompt(message, image);
                addMessage(`Error: ${data.error}`, 'agent');
            } else {
                // Success: the image has been sent, so clear the selection
                clearSelectedImage();

                // Display the agent's response (and any images it downloaded)
                if (data.response_html) {
                    addMessage(data.response_html, 'agent', { isHtml: true, images: data.images });
                } else {
                    addMessage(data.response, 'agent', { images: data.images });
                }
            }

            // Re-enable input
            setInputDisabled(false);
            messageInput.focus();
        })
        .catch(error => {
            typingIndicator.remove();
            restoreFailedPrompt(message, image);
            addMessage(`Error: ${error.message}`, 'agent');
            setInputDisabled(false);
            messageInput.focus();
        });
}

function restoreFailedPrompt(message, image) {
    messageInput.value = message;
    if (image) {
        selectedImage = image;
        imagePreviewImg.src = image.dataUrl;
        imagePreview.hidden = false;
    }
}

function handleImageSelected() {
    const file = imageInput.files[0];
    if (!file) {
        return;
    }

    // Reject unsupported or oversized files; any previous selection is kept
    const problem = validateImageFile(file);
    imageInput.value = '';
    if (problem) {
        showImageError(problem);
        return;
    }

    const reader = new FileReader();
    reader.onload = () => {
        const dataUrl = reader.result;
        selectedImage = {
            mediaType: file.type,
            dataUrl: dataUrl,
            base64: dataUrl.substring(dataUrl.indexOf(',') + 1)
        };
        imagePreviewImg.src = dataUrl;
        imagePreview.hidden = false;
        hideImageError();
    };
    reader.onerror = () => {
        showImageError('The image could not be read. Please try another file.');
    };
    reader.readAsDataURL(file);
}

function validateImageFile(file) {
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        return 'Unsupported file type. Please choose a PNG or JPEG image.';
    }
    if (file.size > MAX_IMAGE_BYTES) {
        return 'That image is larger than 5 MB. Please choose a smaller image.';
    }
    return null;
}

function clearSelectedImage() {
    selectedImage = null;
    imagePreviewImg.removeAttribute('src');
    imagePreview.hidden = true;
    imageInput.value = '';
    hideImageError();
}

function showImageError(message) {
    imageError.textContent = message;
    imageError.hidden = false;
}

function hideImageError() {
    imageError.textContent = '';
    imageError.hidden = true;
}

function addMessage(text, sender, options = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.setAttribute('role', 'article');
    messageDiv.setAttribute('aria-label', `${sender === 'user' ? 'User' : 'Agent'} message`);

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = sender === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    if (options.isHtml === true) {
        content.innerHTML = text;
    } else {
        // Security: Escape HTML first, then safely render structured response content.
        const formattedText = renderMessageContent(text);
        content.innerHTML = formattedText;
    }

    // Show an attached image above the message text
    if (options.imageUrl) {
        const image = document.createElement('img');
        image.className = 'message-image';
        image.src = options.imageUrl;
        image.alt = 'Image attached to this message';
        content.prepend(image);
    }

    // Show any images the agent downloaded below the message text
    if (options.images) {
        appendDownloadedImages(content, options.images);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    // Scroll again after a short delay to ensure content is fully rendered
    setTimeout(scrollToBottom, 100);
}

// Display images downloaded by the agent, each with a caption that credits its author and license.
// (The agent only returns images when it has a tool that downloads them.)
function appendDownloadedImages(content, images) {
    for (const image of images) {
        const figure = document.createElement('figure');
        figure.className = 'message-figure';

        const img = document.createElement('img');
        img.className = 'downloaded-image';
        img.src = image.url;
        img.alt = image.title;
        // Scroll once the image has loaded and its height is known
        img.addEventListener('load', scrollToBottom);

        // Credit the image's author and license, with a link to its source page
        const caption = document.createElement('figcaption');
        caption.textContent = `${image.title} by ${image.author} (${image.license}) `;
        if (/^https?:\/\//.test(image.source_page_url)) {
            const link = document.createElement('a');
            link.href = image.source_page_url;
            link.textContent = 'Source';
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            caption.appendChild(link);
        }

        figure.appendChild(img);
        figure.appendChild(caption);
        content.appendChild(figure);
    }
}

function renderMessageContent(text) {
    const normalizedText = String(text || '').replace(/\r\n/g, '\n');
    const markedLib = resolveMarkedLibrary();
    const purifyLib = resolvePurifyLibrary();

    // Fallback rendering if markdown libraries fail to load.
    if (!markedLib || !purifyLib) {
        return renderFallbackMarkdown(normalizedText);
    }

    const renderer = new markedLib.Renderer();
    renderer.link = (hrefOrToken, title, textValue) => {
        let href = hrefOrToken;
        let linkTitle = title;
        let textContent = textValue;

        // Marked v12+ uses an object argument; older versions pass (href, title, text).
        if (hrefOrToken && typeof hrefOrToken === 'object') {
            href = hrefOrToken.href;
            linkTitle = hrefOrToken.title;
            textContent = markedLib.Parser && hrefOrToken.tokens
                ? markedLib.Parser.parseInline(hrefOrToken.tokens)
                : hrefOrToken.text;
        }

        const safeHref = href || '#';
        const safeTitle = linkTitle ? ` title="${escapeHtml(linkTitle)}"` : '';
        return `<a href="${safeHref}"${safeTitle} target="_blank" rel="noopener noreferrer">${textContent}</a>`;
    };

    markedLib.setOptions({
        gfm: true,
        breaks: true,
        renderer
    });

    const rawHtml = markedLib.parse(normalizedText);
    return purifyLib.sanitize(rawHtml, {
        USE_PROFILES: { html: true },
        ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'class']
    });
}

function resolveMarkedLibrary() {
    if (typeof marked === 'undefined' && typeof window === 'undefined') {
        return null;
    }

    const candidate = typeof marked !== 'undefined' ? marked : window.marked;
    if (!candidate) {
        return null;
    }

    if (typeof candidate.parse === 'function') {
        return candidate;
    }

    if (typeof candidate.marked === 'function') {
        return {
            parse: candidate.marked,
            setOptions: candidate.setOptions ? candidate.setOptions.bind(candidate) : () => { },
            Renderer: candidate.Renderer,
            Parser: candidate.Parser
        };
    }

    if (typeof candidate === 'function') {
        return {
            parse: candidate,
            setOptions: candidate.setOptions ? candidate.setOptions.bind(candidate) : () => { },
            Renderer: candidate.Renderer,
            Parser: candidate.Parser
        };
    }

    return null;
}

function resolvePurifyLibrary() {
    if (typeof DOMPurify !== 'undefined') {
        return DOMPurify;
    }

    if (typeof window !== 'undefined') {
        if (window.DOMPurify) {
            return window.DOMPurify;
        }
        if (window.dompurify && typeof window.dompurify.sanitize === 'function') {
            return window.dompurify;
        }
    }

    return null;
}

function renderFallbackMarkdown(text) {
    let html = escapeHtml(text);

    // Fenced code blocks.
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, _language, code) => {
        return `<pre><code>${code.trimEnd()}</code></pre>`;
    });

    // Inline code, strong, emphasis.
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Links.
    html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');

    // Basic line breaks.
    return html.replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function addTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message agent';
    messageDiv.id = 'typing-indicator';
    messageDiv.setAttribute('role', 'status');
    messageDiv.setAttribute('aria-label', 'Agent is typing');
    messageDiv.setAttribute('aria-live', 'polite');

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.setAttribute('aria-hidden', 'true');
    indicator.innerHTML = '<span></span><span></span><span></span>';

    content.appendChild(indicator);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

function setInputDisabled(disabled) {
    messageInput.disabled = disabled;
    sendBtn.disabled = disabled;
    attachBtn.disabled = disabled;
    removeImageBtn.disabled = disabled;

    // Update ARIA attributes for better screen reader support
    if (disabled) {
        sendBtn.setAttribute('aria-busy', 'true');
        messageInput.setAttribute('aria-busy', 'true');
    } else {
        sendBtn.removeAttribute('aria-busy');
        messageInput.removeAttribute('aria-busy');
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function resetConversation() {
    // Announce to screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = 'Conversation reset';
    document.body.appendChild(announcement);

    // Call backend to reset conversation history
    fetch('/reset', {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            // Clear chat messages and any selected image
            chatMessages.innerHTML = '<div class="welcome-message" role="status">Let\'s chat about computing history...</div>';
            clearSelectedImage();
            messageInput.focus();

            // Remove announcement after a short delay
            setTimeout(() => announcement.remove(), 1000);
        })
        .catch(error => {
            console.error('Error resetting conversation:', error);
            announcement.textContent = 'Error resetting conversation';
            setTimeout(() => announcement.remove(), 1000);
        });
}

// Focus input on load
messageInput.focus();
