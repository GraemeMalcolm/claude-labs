/*
 * Ask Claude: a floating chat assistant for the lab pages.
 *
 * The learner supplies their own Claude API key. The key is kept in sessionStorage
 * (cleared when the tab closes) and requests go directly from the browser to the
 * Claude Messages API, so usage is billed to the learner's own Console account.
 *
 * The assistant is given the lab title and the section the learner is currently
 * reading, so its answers relate to the lab.
 */
(function () {
    'use strict';

    const CONFIG = {
        model: 'claude-haiku-5-5',
        maxTokens: 1024,
        maxSectionChars: 6000,
        maxHistoryMessages: 10,
        storageKey: 'labAssistantApiKey',
        apiUrl: 'https://api.anthropic.com/v1/messages',
        apiVersion: '2023-06-01'
    };

    const script = document.currentScript;
    const labTitle = (script && script.dataset.labTitle) || document.title;
    const labDescription = (script && script.dataset.labDescription) || '';

    let history = [];
    let busy = false;

    // ----- Build the UI -----

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    const toggleBtn = el('button', 'la-toggle', 'Ask Claude');
    toggleBtn.type = 'button';
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.setAttribute('aria-controls', 'la-panel');

    const panel = el('div', 'la-panel');
    panel.id = 'la-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-labelledby', 'la-panel-title');
    panel.hidden = true;

    // Header
    const header = el('div', 'la-header');
    const titleBlock = el('div', 'la-title-block');
    const title = el('h2', 'la-title', 'Ask Claude');
    title.id = 'la-panel-title';
    titleBlock.appendChild(title);
    titleBlock.appendChild(el('p', 'la-subtitle', labTitle));
    const headerButtons = el('div', 'la-header-buttons');
    const keyBtn = el('button', 'la-icon-btn', 'Key');
    keyBtn.type = 'button';
    keyBtn.title = 'Change or remove your API key';
    keyBtn.setAttribute('aria-label', 'Change or remove your API key');
    const closeBtn = el('button', 'la-icon-btn', '×');
    closeBtn.type = 'button';
    closeBtn.title = 'Close';
    closeBtn.setAttribute('aria-label', 'Close Ask Claude');
    headerButtons.appendChild(keyBtn);
    headerButtons.appendChild(closeBtn);
    header.appendChild(titleBlock);
    header.appendChild(headerButtons);

    // API key setup
    const keyPanel = el('div', 'la-key-panel');
    keyPanel.hidden = true;
    const keyNote = el('p', 'la-key-note',
        'Ask Claude uses your own Claude API key. The key is stored only in this browser tab ' +
        'and is cleared when you close the tab. Requests go directly from your browser to Anthropic ' +
        'and are billed to your Claude Console account. Don\'t use this on a shared computer.');
    const keyLabel = el('label', 'la-key-label', 'Your API key');
    keyLabel.htmlFor = 'la-key-input';
    const keyInput = el('input', 'la-key-input');
    keyInput.id = 'la-key-input';
    keyInput.type = 'password';
    keyInput.autocomplete = 'off';
    keyInput.spellcheck = false;
    keyInput.placeholder = 'sk-ant-...';
    const keyActions = el('div', 'la-key-actions');
    const saveKeyBtn = el('button', 'la-primary-btn', 'Save key');
    saveKeyBtn.type = 'button';
    const forgetKeyBtn = el('button', 'la-secondary-btn', 'Remove key');
    forgetKeyBtn.type = 'button';
    keyActions.appendChild(saveKeyBtn);
    keyActions.appendChild(forgetKeyBtn);
    const keyError = el('p', 'la-error');
    keyError.hidden = true;
    keyPanel.appendChild(keyNote);
    keyPanel.appendChild(keyLabel);
    keyPanel.appendChild(keyInput);
    keyPanel.appendChild(keyActions);
    keyPanel.appendChild(keyError);

    // Conversation
    const log = el('div', 'la-log');
    log.setAttribute('role', 'log');
    log.setAttribute('aria-live', 'polite');
    log.setAttribute('aria-label', 'Conversation with Claude');

    // Composer
    const composer = el('div', 'la-composer');
    const prompt = el('textarea', 'la-prompt');
    prompt.rows = 2;
    prompt.placeholder = 'Ask a question about this lab...';
    prompt.setAttribute('aria-label', 'Your question for Claude');
    const sendBtn = el('button', 'la-primary-btn', 'Send');
    sendBtn.type = 'button';
    composer.appendChild(prompt);
    composer.appendChild(sendBtn);

    panel.appendChild(header);
    panel.appendChild(keyPanel);
    panel.appendChild(log);
    panel.appendChild(composer);

    document.body.appendChild(panel);
    document.body.appendChild(toggleBtn);

    // ----- API key handling -----

    function getKey() {
        return sessionStorage.getItem(CONFIG.storageKey) || '';
    }

    function showKeyPanel(show) {
        keyPanel.hidden = !show;
        log.hidden = show;
        composer.hidden = show;
        if (show) {
            keyInput.focus();
        } else {
            prompt.focus();
        }
    }

    saveKeyBtn.addEventListener('click', () => {
        const value = keyInput.value.trim();
        if (!value.startsWith('sk-ant-')) {
            keyError.textContent = 'That doesn\'t look like a Claude API key. Keys start with "sk-ant-".';
            keyError.hidden = false;
            return;
        }
        sessionStorage.setItem(CONFIG.storageKey, value);
        keyInput.value = '';
        keyError.hidden = true;
        showKeyPanel(false);
    });

    forgetKeyBtn.addEventListener('click', () => {
        sessionStorage.removeItem(CONFIG.storageKey);
        keyInput.value = '';
        history = [];
        renderLog();
        showKeyPanel(true);
    });

    keyBtn.addEventListener('click', () => showKeyPanel(keyPanel.hidden));

    // ----- Lab context -----

    // Returns the heading the learner is currently reading, plus the text of its section.
    function currentSection() {
        const main = document.querySelector('main') || document.body;
        const children = Array.from(main.children);
        const headings = children.filter(node => /^H[1-4]$/.test(node.tagName));

        let current = null;
        for (const h of headings) {
            if (h.getBoundingClientRect().top <= 200) {
                current = h;
            }
        }
        if (!current) {
            current = headings[0] || null;
        }
        if (!current) {
            return { heading: '', text: '' };
        }

        // Collect the heading's section: following siblings up to the next heading of the same or higher level
        const level = Number(current.tagName.substring(1));
        const parts = [];
        let node = current;
        while (node) {
            if (node !== current && /^H[1-4]$/.test(node.tagName) && Number(node.tagName.substring(1)) <= level) {
                break;
            }
            parts.push(node.textContent.replace(/\s+/g, ' ').trim());
            node = node.nextElementSibling;
        }
        const text = parts.filter(Boolean).join('\n').slice(0, CONFIG.maxSectionChars);
        return { heading: current.textContent.trim(), text };
    }

    function buildSystemPrompt() {
        const section = currentSection();
        const lines = [
            'You are a helpful assistant for a learner working through a hands-on lab titled "' + labTitle + '".',
            labDescription ? 'Lab description: ' + labDescription : '',
            'The learner is currently reading the section "' + section.heading + '". Here is that section of the lab:',
            '<lab_section>',
            section.text,
            '</lab_section>',
            'Help the learner understand the lab and complete its steps. Explain concepts, help them debug errors, and suggest next steps.',
            'Use the lab section as the source of truth for lab-specific steps. Keep answers concise and practical.',
            'If the question is not about this lab, answer it helpfully anyway.'
        ];
        return lines.filter(Boolean).join('\n');
    }

    // ----- Chat -----

    function renderLog() {
        log.textContent = '';
        if (history.length === 0) {
            log.appendChild(el('p', 'la-empty', 'Ask a question about the part of the lab you\'re reading.'));
            return;
        }
        for (const turn of history) {
            const bubble = el('div', 'la-msg la-msg-' + turn.role);
            bubble.textContent = turn.content;
            log.appendChild(bubble);
        }
        log.scrollTop = log.scrollHeight;
    }

    function addPending() {
        const pending = el('div', 'la-msg la-msg-assistant la-pending', 'Thinking…');
        log.appendChild(pending);
        log.scrollTop = log.scrollHeight;
        return pending;
    }

    async function sendPrompt() {
        const text = prompt.value.trim();
        const key = getKey();
        if (!text || busy) {
            return;
        }
        if (!key) {
            showKeyPanel(true);
            return;
        }

        busy = true;
        sendBtn.disabled = true;
        prompt.value = '';
        history.push({ role: 'user', content: text });
        renderLog();
        const pending = addPending();

        const messages = history.slice(-CONFIG.maxHistoryMessages).map(m => ({ role: m.role, content: m.content }));

        try {
            const response = await fetch(CONFIG.apiUrl, {
                method: 'POST',
                headers: {
                    'content-type': 'application/json',
                    'x-api-key': key,
                    'anthropic-version': CONFIG.apiVersion,
                    'anthropic-dangerous-direct-browser-access': 'true'
                },
                body: JSON.stringify({
                    model: CONFIG.model,
                    max_tokens: CONFIG.maxTokens,
                    system: buildSystemPrompt(),
                    messages: messages
                })
            });
            const data = await response.json();

            if (!response.ok) {
                const message = response.status === 401
                    ? 'Your API key wasn\'t accepted. Use the Key button to check it.'
                    : 'Claude couldn\'t answer: ' + ((data.error && data.error.message) || response.statusText);
                throw new Error(message);
            }

            const reply = (data.content || [])
                .filter(block => block.type === 'text')
                .map(block => block.text)
                .join('')
                .trim();
            history.push({ role: 'assistant', content: reply || 'The response was empty.' });
        } catch (error) {
            history.push({ role: 'assistant', content: error.message || 'Something went wrong. Please try again.' });
        } finally {
            busy = false;
            sendBtn.disabled = false;
            renderLog();
            prompt.focus();
        }
    }

    sendBtn.addEventListener('click', sendPrompt);
    prompt.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendPrompt();
        }
    });

    // ----- Open / close -----

    function openPanel() {
        panel.hidden = false;
        toggleBtn.setAttribute('aria-expanded', 'true');
        renderLog();
        if (getKey()) {
            showKeyPanel(false);
        } else {
            showKeyPanel(true);
        }
    }

    function closePanel() {
        panel.hidden = true;
        toggleBtn.setAttribute('aria-expanded', 'false');
        toggleBtn.focus();
    }

    toggleBtn.addEventListener('click', () => {
        if (panel.hidden) {
            openPanel();
        } else {
            closePanel();
        }
    });
    closeBtn.addEventListener('click', closePanel);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !panel.hidden) {
            closePanel();
        }
    });

    renderLog();
})();
