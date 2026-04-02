/**
 * document_navigator.js
 * ─────────────────────
 * Agentic Document Navigator — Page Index powered chat.
 *
 * BUGS FIXED:
 *  1. loadDocument() was fetching /api/chat/documents (the document LIST)
 *     to build the page index. Fixed to call /api/chat/documents/{docId}/index.
 *  2. previewSection() was writing into #sectionPreview which is the inner
 *     content div — was correct, but content wasn't cleared between loads.
 *  3. State was never reset on document switch (history, sections accumulated).
 *  4. send button was never re-enabled after a network error (missing finally).
 */

const state = {
    docId:    null,
    history:  [],
    sections: []   /* flat cache of entire section tree for fast lookup */
};

/* ── DOM ─────────────────────────────────────────────────────────────────── */
const docSelect      = document.getElementById('docSelect');
const tocWrap        = document.getElementById('tocWrap');
const chatMessages   = document.getElementById('chatMessages');
const chatInput      = document.getElementById('chatInput');
const sendBtn        = document.getElementById('sendBtn');
const sectionPreview = document.getElementById('sectionPreview');

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function esc(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/** Recursively flatten the section tree into a lookup array. */
function flattenSections(sections, acc = []) {
    for (const s of sections) {
        acc.push(s);
        if (s.subsections?.length) flattenSections(s.subsections, acc);
    }
    return acc;
}

function findSectionInTree(sections, sid) {
    for (const s of sections) {
        if (s.section_id === sid) return s;
        const found = findSectionInTree(s.subsections || [], sid);
        if (found) return found;
    }
    return null;
}

/* ── Initialisation: load document list ─────────────────────────────────── */
async function init() {
    try {
        const resp = await fetch('/api/chat/documents');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const docs = await resp.json();

        docSelect.innerHTML = '<option value="">— Select Document —</option>';
        if (!Array.isArray(docs) || docs.length === 0) {
            docSelect.innerHTML = '<option value="">No parsed documents found</option>';
            return;
        }

        docs.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.doc_id;
            opt.textContent = d.filename
                + (d.project_name ? ` (${d.project_name})` : '')
                + (d.section_count ? ` · ${d.section_count} sections` : '');
            docSelect.appendChild(opt);
        });

        /* Auto-select from URL query param ?doc_id=... */
        const urlParams = new URLSearchParams(window.location.search);
        const urlDocId  = urlParams.get('doc_id');
        if (urlDocId) {
            docSelect.value = urlDocId;
            if (docSelect.value) loadDocument(urlDocId);
        }
    } catch (e) {
        console.error('init error:', e);
        docSelect.innerHTML = '<option value="">Failed to load documents</option>';
    }
}

/* ── Load a document: fetch page index from correct endpoint ─────────────── */
async function loadDocument(docId) {
    /* Reset state on every document switch */
    state.docId    = docId;
    state.history  = [];
    state.sections = [];

    chatMessages.innerHTML = '';
    tocWrap.innerHTML      = '<p style="padding:16px;font-size:0.8rem;color:var(--muted);">Loading index…</p>';
    sectionPreview.innerHTML = `
        <div class="preview-empty">
            <div class="preview-empty-icon">📖</div>
            <p>Select a section or ask a question to preview its content here.</p>
        </div>`;

    chatInput.disabled = true;
    sendBtn.disabled   = true;

    try {
        /*
         * BUG FIX #1 — was: fetch('/api/chat/documents')  ← wrong! returns doc list
         *              now: fetch(`/api/chat/documents/${docId}/index`)  ← section tree
         */
        const res      = await fetch(`/api/chat/documents/${docId}/index`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const sections = await res.json();

        if (sections.error) throw new Error(sections.error);

        /* Cache flat list for instant lookup */
        state.sections = flattenSections(sections);

        /* Render the Table of Contents tree */
        tocWrap.innerHTML = '';
        if (!sections.length) {
            tocWrap.innerHTML = '<p style="padding:16px;font-size:0.8rem;color:var(--muted);">No sections detected.</p>';
        } else {
            renderToc(sections, tocWrap, 0);
        }

        chatInput.disabled = false;
        sendBtn.disabled   = false;

        appendMessage('bot',
            `Document loaded. I have the full Page Index — ${state.sections.length} sections indexed.\n\nAsk me anything and I'll read the exact section to answer you.`
        );

    } catch (e) {
        console.error('loadDocument error:', e);
        tocWrap.innerHTML = '<p style="padding:16px;font-size:0.8rem;color:#fc8181;">Failed to load document index.</p>';
        appendMessage('bot', '⚠ Could not load the document index. Please try again.');
    }
}

docSelect.addEventListener('change', () => {
    if (docSelect.value) loadDocument(docSelect.value);
});

/* ── Render TOC tree ─────────────────────────────────────────────────────── */
function renderToc(sections, container, depth) {
    if (!sections?.length) return;

    const ul = document.createElement('ul');
    ul.className = 'toc-tree';
    if (depth > 0) ul.classList.add('toc-sub');

    sections.forEach(s => {
        const li   = document.createElement('li');
        const item = document.createElement('div');
        item.className = 'toc-item';
        item.dataset.sectionId = s.section_id;
        item.innerHTML = `
            <span class="toc-id">${esc(s.section_id)}</span>
            <span class="toc-label">${esc(s.heading)}</span>
        `;

        item.addEventListener('click', () => {
            /* Mark active */
            document.querySelectorAll('.toc-item').forEach(el => el.classList.remove('active'));
            item.classList.add('active');

            /* Show section in preview */
            previewSection(s.section_id, s.heading, s.content);

            /* Auto-fill chat input */
            chatInput.value = `Tell me about section ${s.section_id}: ${s.heading}`;
            chatInput.focus();
        });

        li.appendChild(item);

        /* Recurse into subsections */
        if (s.subsections?.length) {
            renderToc(s.subsections, li, depth + 1);
        }

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
            : `<p style="color:var(--muted);font-style:italic;">This section has no body text (may be a parent heading).</p>`
        }
    `;
}

function highlightTocSection(sid) {
    document.querySelectorAll('.toc-item').forEach(el => el.classList.remove('active'));
    const el = document.querySelector(`.toc-item[data-section-id="${sid}"]`);
    if (el) {
        el.classList.add('active');
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        /* Also update preview */
        const sec = findSectionInTree(state.sections, sid);
        if (sec) previewSection(sec.section_id, sec.heading, sec.content);
    }
}

/* ── Chat messages ───────────────────────────────────────────────────────── */
function appendMessage(role, text, toolCalls = []) {
    /* Remove the static welcome empty-state if present */
    const empty = chatMessages.querySelector('.preview-empty');
    if (empty) empty.remove();

    const div  = document.createElement('div');
    div.className = `msg ${role}`;

    /* Tool call indicators */
    let toolHtml = '';
    toolCalls.forEach(tc => {
        toolHtml += `
            <div class="msg-tool">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                Read §${esc(tc.section_id)} <span style="color:var(--muted)">(${tc.chars_returned} chars)</span>
            </div>`;
    });

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.innerHTML = `
        <div class="msg-bubble">${esc(text)}</div>
        ${toolHtml}
        <div class="msg-meta">${time}</div>
    `;

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendThinking() {
    const empty = chatMessages.querySelector('.preview-empty');
    if (empty) empty.remove();

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

    appendMessage('user', question);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    sendBtn.disabled = true;
    const thinking = appendThinking();

    state.history.push({ role: 'user', content: question });

    try {
        const resp = await fetch('/api/chat/query', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                doc_id:   state.docId,
                question,
                history:  state.history.slice(-10),
            }),
        });

        thinking.remove();

        if (!resp.ok) {
            appendMessage('bot', `⚠ Server error ${resp.status}: ${resp.statusText}`);
            return;
        }

        const data = await resp.json();

        if (data.error) {
            appendMessage('bot', `⚠ ${data.error}`);
        } else {
            appendMessage('bot', data.answer, data.tool_calls || []);
            state.history.push({ role: 'assistant', content: data.answer });

            /* Highlight last read section in the TOC + preview */
            if (data.tool_calls?.length) {
                const lastSid = data.tool_calls[data.tool_calls.length - 1].section_id;
                highlightTocSection(lastSid);
            }
        }

    } catch (e) {
        thinking.remove();
        appendMessage('bot', '⚠ Network error — please check your connection and try again.');
        console.error('sendMessage error:', e);

    } finally {
        /* BUG FIX #4 — send button was never re-enabled after a network error */
        sendBtn.disabled = false;
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