/**
 * document_navigator.js  v2
 * ─────────────────────────
 * Agentic Document Navigator — Page Index powered chat with RAG fallback.
 *
 * BUGS FIXED vs original:
 *  BUG-1  loadDocument() called /api/chat/documents (list) instead of
 *         /api/chat/documents/{docId}/index.                    [FIXED ✓]
 *  BUG-2  Content / state were not reset on document switch.   [FIXED ✓]
 *  BUG-3  State (history, sections) accumulated across docs.   [FIXED ✓]
 *  BUG-4  sendBtn never re-enabled after a network error —
 *         missing finally block.                                [FIXED ✓]
 *  BUG-6  Section lookup used O(n) recursive findSectionInTree
 *         on an already-flat array. Replaced with O(1) Map.    [FIXED ✓]
 *  BUG-7  Bot text rendered with esc() → markdown shown as
 *         literal asterisks/hashes. Added lightweight md→HTML. [FIXED ✓]
 *  BUG-8  chatInput height stayed 'auto' after clear → glitch. [FIXED ✓]
 *  BUG-9  No visible loading indicator while index fetches.    [FIXED ✓]
 *  BUG-10 querySelector(".toc-item[data-section-id="1.2"]")
 *         fails for IDs with dots. Fixed with CSS.escape().    [FIXED ✓]
 */

/* ── State ───────────────────────────────────────────────────────────────── */
const state = {
    docId:       null,
    history:     [],
    /** O(1) section lookup: section_id → {section_id, heading, content} */
    sectionMap:  new Map(),
    /** Original nested tree (for renderToc) */
    tree:        [],
};

/* ── DOM refs ────────────────────────────────────────────────────────────── */
const docSelect      = document.getElementById('docSelect');
const tocWrap        = document.getElementById('tocWrap');
const chatMessages   = document.getElementById('chatMessages');
const chatInput      = document.getElementById('chatInput');
const sendBtn        = document.getElementById('sendBtn');
const sectionPreview = document.getElementById('sectionPreview');
const quotaBanner    = document.getElementById('quotaBanner');
const quotaText      = document.getElementById('quotaText');

/* ── Utilities ───────────────────────────────────────────────────────────── */

/** HTML-escape raw text (for user messages and labels). */
function esc(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/**
 * BUG-7 FIX: Lightweight Markdown → safe HTML converter.
 * Handles: **bold**, *italic*, `code`, ### headings, - bullet lists,
 *           numbered lists, blank-line paragraphs, and line breaks.
 * Does NOT use innerHTML directly on user input — only on LLM responses.
 */
function mdToHtml(text) {
    if (!text) return '';

    // Escape HTML first to prevent XSS
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Headings  (### h3, ## h2, # h1)
    html = html.replace(/^#{3}\s+(.+)$/gm, '<h4 class="md-h4">$1</h4>');
    html = html.replace(/^#{2}\s+(.+)$/gm, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^#{1}\s+(.+)$/gm, '<h3 class="md-h3">$1</h3>');

    // Bold / italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g,      '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g,           '<em>$1</em>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');

    // Bullet lists
    html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>(\n|$))+/g, (m) => `<ul class="md-ul">${m}</ul>`);

    // Numbered lists
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

    // Horizontal rules
    html = html.replace(/^---+$/gm, '<hr class="md-hr">');

    // Paragraphs (blank-line separated blocks)
    html = html
        .split(/\n{2,}/)
        .map(block => {
            block = block.trim();
            if (!block) return '';
            if (/^<(h[1-6]|ul|ol|hr|li)/.test(block)) return block;
            return `<p class="md-p">${block.replace(/\n/g, '<br>')}</p>`;
        })
        .join('\n');

    return html;
}

/**
 * BUG-6 FIX: Build an O(1) section Map from the nested tree.
 * flattenSections() was returning a flat array and findSectionInTree()
 * still did O(n) recursive search — now we use a Map for instant lookup.
 */
function buildSectionMap(sections, map = new Map()) {
    for (const s of sections) {
        map.set(s.section_id, s);
        if (s.subsections?.length) buildSectionMap(s.subsections, map);
    }
    return map;
}

/**
 * BUG-10 FIX: querySelector with data attributes that contain dots (e.g. "1.2")
 * was throwing SyntaxError. CSS.escape() handles it correctly.
 */
function tocItemEl(sectionId) {
    try {
        return document.querySelector(`.toc-item[data-section-id="${CSS.escape(sectionId)}"]`);
    } catch {
        // CSS.escape not available (very old browsers) — fall back to find-all
        return [...document.querySelectorAll('.toc-item')]
            .find(el => el.dataset.sectionId === sectionId) || null;
    }
}

/* ── Init: load document list ────────────────────────────────────────────── */
async function init() {
    try {
        const resp = await fetch('/api/chat/documents');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const docs = await resp.json();

        docSelect.innerHTML = '<option value="">— Select Document —</option>';
        if (!Array.isArray(docs) || docs.length === 0) {
            docSelect.innerHTML = '<option value="">No SRS documents found — generate one first.</option>';
            return;
        }

        docs.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.doc_id;
            opt.textContent = d.filename
                + (d.domain && d.domain !== 'technical' ? ` [${d.domain}]` : '')
                + (d.section_count ? ` · ${d.section_count} sections` : '');
            docSelect.appendChild(opt);
        });

        // Auto-select from ?doc_id= query param
        const urlDocId = new URLSearchParams(window.location.search).get('doc_id');
        if (urlDocId) {
            docSelect.value = urlDocId;
            if (docSelect.value) loadDocument(urlDocId);
        }
    } catch (e) {
        console.error('init error:', e);
        docSelect.innerHTML = '<option value="">Failed to load documents</option>';
    }
    
    // Check quota on boot
    checkChatQuota();
}

/** Fetch current chat quota and update banner/UI */
async function checkChatQuota() {
    try {
        const res = await fetch('/api/my-quota');
        if (!res.ok) return;
        const q = await res.json();

        const count = q.chat_query_count || 0;
        const limit = q.chat_query_limit || 15;
        const remaining = Math.max(0, limit - count);

        if (quotaBanner) {
            quotaBanner.style.display = 'flex';
            quotaText.innerHTML = `<strong>Beta Quota:</strong> ${remaining} messages remaining (${count}/${limit} used)`;
            
            if (remaining <= 0) {
                quotaBanner.style.background = 'rgba(252, 129, 129, 0.1)';
                quotaBanner.style.borderColor = 'rgba(252, 129, 129, 0.2)';
                quotaBanner.style.color = '#fc8181';
                quotaText.innerHTML = `<strong>Quota Reached:</strong> 0 messages remaining. Upgrade to continue!`;
                
                // Lock the UI
                chatInput.disabled = true;
                chatInput.placeholder = "Quota reached — please upgrade your plan.";
                sendBtn.disabled = true;
            }
        }
    } catch (err) {
        console.warn('Failed to fetch quota:', err);
    }
}

/* ── Load a document: fetch section tree from correct endpoint ───────────── */
async function loadDocument(docId) {
    // BUG-2 & BUG-3 FIX: reset ALL state on every document switch
    state.docId      = docId;
    state.history    = [];
    state.sectionMap = new Map();
    state.tree       = [];

    chatMessages.innerHTML = '';
    sectionPreview.innerHTML = `
        <div class="preview-empty">
            <div class="preview-empty-icon">📖</div>
            <p>Select a section or ask a question to preview its content here.</p>
        </div>`;

    chatInput.disabled = true;
    sendBtn.disabled   = true;

    // BUG-9 FIX: show a visible spinner while loading
    tocWrap.innerHTML = `
        <div style="padding:20px;text-align:center;">
            <div class="thinking" style="justify-content:center;margin-bottom:8px;">
                <span class="t-dot"></span>
                <span class="t-dot"></span>
                <span class="t-dot"></span>
            </div>
            <p style="font-size:0.78rem;color:var(--muted);">Loading section index…</p>
        </div>`;

    try {
        // BUG-1 FIX: correct endpoint (was calling /api/chat/documents by mistake)
        const res = await fetch(`/api/chat/documents/${encodeURIComponent(docId)}/index`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const tree = await res.json();

        if (tree.error) throw new Error(tree.error);
        if (!Array.isArray(tree) || !tree.length) throw new Error('No sections found.');

        // BUG-6 FIX: build O(1) Map instead of relying on tree search later
        state.tree       = tree;
        state.sectionMap = buildSectionMap(tree);

        tocWrap.innerHTML = '';
        renderToc(tree, tocWrap, 0);

        chatInput.disabled = false;
        sendBtn.disabled   = false;

        appendBotMessage(
            `📄 **${docId}** loaded — ${state.sectionMap.size} sections indexed.\n\n` +
            `Ask me anything. I'll read the exact section to answer you.`
        );

    } catch (e) {
        console.error('loadDocument error:', e);
        tocWrap.innerHTML =
            `<p style="padding:16px;font-size:0.8rem;color:#fc8181;">⚠ ${esc(e.message)}</p>`;
        appendBotMessage(`⚠ Could not load the document index: ${e.message}`);
    }
}

docSelect.addEventListener('change', () => {
    if (docSelect.value) loadDocument(docSelect.value);
});

/* ── Render TOC ──────────────────────────────────────────────────────────── */
function renderToc(sections, container, depth) {
    if (!sections?.length) return;

    const ul = document.createElement('ul');
    ul.className = depth === 0 ? 'toc-tree' : 'toc-tree toc-sub';

    sections.forEach(s => {
        const li   = document.createElement('li');
        const item = document.createElement('div');
        item.className = 'toc-item';
        item.dataset.sectionId = s.section_id;
        item.innerHTML = `
            <span class="toc-id">${esc(s.section_id)}</span>
            <span class="toc-label">${esc(s.heading)}</span>`;

        item.addEventListener('click', () => {
            setActiveTocItem(item);
            previewSection(s.section_id, s.heading, s.content);
            chatInput.value = `Tell me about section ${s.section_id}: ${s.heading}`;
            chatInput.style.height = 'auto'; // BUG-8 FIX: reset height before measuring
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
            chatInput.focus();
        });

        li.appendChild(item);
        if (s.subsections?.length) renderToc(s.subsections, li, depth + 1);
        ul.appendChild(li);
    });

    container.appendChild(ul);
}

/* ── Section preview ─────────────────────────────────────────────────────── */
function previewSection(id, heading, content) {
    const bodyText = (content || '').trim();
    sectionPreview.innerHTML = `
        <h2>§${esc(id)} ${esc(heading)}</h2>
        ${bodyText
            ? `<p style="white-space:pre-wrap;">${esc(bodyText)}</p>`
            : `<p style="color:var(--muted);font-style:italic;">
               Parent heading — select a sub-section to read its content.
               </p>`}`;
}

function setActiveTocItem(el) {
    document.querySelectorAll('.toc-item').forEach(e => e.classList.remove('active'));
    if (el) el.classList.add('active');
}

/**
 * BUG-10 FIX: use CSS.escape() via tocItemEl() helper.
 * BUG-6 FIX:  use state.sectionMap instead of tree search.
 */
function highlightTocSection(sid) {
    const el = tocItemEl(sid);
    if (el) {
        setActiveTocItem(el);
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    // Preview the section content using O(1) map lookup
    const sec = state.sectionMap.get(sid);
    if (sec) previewSection(sec.section_id, sec.heading, sec.content);
}

/* ── Chat messages ───────────────────────────────────────────────────────── */
function removeWelcomeState() {
    const empty = chatMessages.querySelector('.preview-empty');
    if (empty) empty.remove();
}

/**
 * BUG-7 FIX: Bot messages use mdToHtml() instead of esc() so markdown
 * from the LLM (**, *, ##, lists) renders as formatted HTML.
 */
function appendBotMessage(text, toolCalls = [], ragUsed = false) {
    removeWelcomeState();
    const div  = document.createElement('div');
    div.className = 'msg bot';

    let toolHtml = '';
    toolCalls.forEach(tc => {
        const isRag  = tc.source === 'rag';
        const icon   = isRag
            ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`
            : `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`;
        const label  = isRag ? 'RAG §' : 'Read §';
        toolHtml += `
            <div class="msg-tool">
                ${icon}
                ${label}${esc(tc.section_id)}
                <span style="color:var(--muted)">(${tc.chars_returned} chars)</span>
            </div>`;
    });

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.innerHTML = `
        <div class="msg-bubble">${mdToHtml(text)}</div>
        ${toolHtml}
        ${ragUsed ? '<div class="msg-tool" style="opacity:0.6">🔍 Semantic RAG search used as fallback</div>' : ''}
        <div class="msg-meta">${time}</div>`;

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendUserMessage(text) {
    removeWelcomeState();
    const div  = document.createElement('div');
    div.className = 'msg user';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.innerHTML = `
        <div class="msg-bubble">${esc(text)}</div>
        <div class="msg-meta">${time}</div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendThinking() {
    removeWelcomeState();
    const div = document.createElement('div');
    div.className = 'msg bot thinking-wrap';
    div.innerHTML = `
        <div class="msg-bubble" style="padding:12px 18px;">
            <div class="thinking">
                <span class="t-dot"></span>
                <span class="t-dot"></span>
                <span class="t-dot"></span>
            </div>
        </div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

/* ── Send message ────────────────────────────────────────────────────────── */
async function sendMessage() {
    const question = chatInput.value.trim();
    if (!question || !state.docId) return;

    appendUserMessage(question);

    // BUG-8 FIX: properly reset input height after clearing
    chatInput.value = '';
    chatInput.style.height = 'auto';

    sendBtn.disabled   = true;
    chatInput.disabled = true;
    const thinking     = appendThinking();

    state.history.push({ role: 'user', content: question });

    try {
        const resp = await fetch('/api/chat/query', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                doc_id:  state.docId,
                question,
                history: state.history.slice(-10),
            }),
        });

        thinking.remove();

        if (!resp.ok) {
            appendBotMessage(`⚠ Server error ${resp.status}: ${resp.statusText}`);
            return;
        }

        const data = await resp.json();

        if (data.error) {
            appendBotMessage(`⚠ ${data.error}`);
            // If the error was quota-related, refresh the UI
            if (data.error.toLowerCase().includes('quota')) checkChatQuota();
        } else {
            appendBotMessage(data.answer, data.tool_calls || [], data.rag_used || false);
            state.history.push({ role: 'assistant', content: data.answer });

            // Highlight the last section read in the TOC + preview panel
            const calls = data.tool_calls || [];
            if (calls.length) {
                // Prefer first non-RAG call for highlighting (more precise)
                const precise = calls.find(c => c.source !== 'rag') || calls[calls.length - 1];
                highlightTocSection(precise.section_id);
            }
            
            // Refresh quota after successful message
            checkChatQuota();
            if (window.refreshQuotas) window.refreshQuotas();
        }

    } catch (e) {
        thinking.remove();
        appendBotMessage('⚠ Network error — please check your connection and try again.');
        console.error('sendMessage error:', e);

    } finally {
        // BUG-4 FIX: always re-enable controls even after error
        sendBtn.disabled   = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}

/* ── Input event listeners ───────────────────────────────────────────────── */
chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
});

sendBtn.addEventListener('click', sendMessage);

/* ── Boot ────────────────────────────────────────────────────────────────── */
init();