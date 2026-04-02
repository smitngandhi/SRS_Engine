/* ─────────────────────────────────────────────────────────────────────────────
   diagram_studio.js  — Mermaid rendered inline, dark themed, full size
   Features:
     · Generate / Regenerate / Apply Edit  (original functionality)
     · Theme Switcher   – live swap of Mermaid colour presets + %%{init}%% injection
     · Version Diff     – highlight line-level additions / deletions between versions
     · Click-to-Edit    – click any SVG node label to rename it inline
     · Context Selector – choose which uploaded documents feed the LLM
     · Validation Retry – auto-retry with parse-error feedback (up to 2 retries)
───────────────────────────────────────────────────────────────────────────── */

/* ── Mermaid init ─────────────────────────────────── */
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    background: 'transparent', mainBkg: '#0f1117', nodeBorder: '#00e5cc',
    clusterBkg: '#1a1f2e', titleColor: '#e2e8f0', nodeTextColor: '#e2e8f0',
    edgeLabelBackground: '#0d1117', labelTextColor: '#94a3b8',
    tertiaryTextColor: '#94a3b8', lineColor: '#00e5cc', arrowheadColor: '#00e5cc',
    actorBkg: '#1a1f2e', actorBorder: '#00e5cc', actorTextColor: '#e2e8f0',
    actorLineColor: '#334155', signalColor: '#00e5cc', signalTextColor: '#e2e8f0',
    activationBkgColor: '#0f172a', activationBorderColor: '#00e5cc',
    labelBoxBkgColor: '#1a1f2e', labelBoxBorderColor: '#00e5cc',
    loopTextColor: '#94a3b8', noteBkgColor: '#1e293b', noteBorderColor: '#00e5cc',
    noteTextColor: '#e2e8f0', attributeBackgroundColorEven: '#0f1117',
    attributeBackgroundColorOdd: '#1a1f2e', classText: '#e2e8f0',
    fontFamily: "'Inter', 'Segoe UI', sans-serif", fontSize: '14px',
  },
  flowchart: { curve: 'basis', useMaxWidth: false, htmlLabels: true },
  sequence: { useMaxWidth: false },
  er: { useMaxWidth: false },
});

/* ── State ────────────────────────────────────────────────────────────────── */
const state = {
  currentDiagramId: null,
  currentVersionId: null,
  currentSvgPath: null,
  currentMermaidCode: null,
  diagramType: 'flowchart',
  allVersions: [],          // Cache for diff comparison — full version objects
};

/* ── DOM refs ─────────────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const projectSelect = $('projectSelect');
const promptInput = $('promptInput');
const generateBtn = $('generateBtn');
const regenBtn = $('regenBtn');
const previewSvgWrap = $('previewSvgWrap');
const previewEmpty = $('previewEmpty');
const previewLoading = $('previewLoading');
const previewMeta = $('previewMeta');
const codeEditor = $('codeEditor');
const applyEditBtn = $('applyEditBtn');
const downloadBtn = $('downloadBtn');
const versionsListEl = $('versionsList');
const previewBadge = $('previewBadge');
const previewVersion = $('previewVersion');

/* ── Resizer ───────────────────────────────────────────── */
const horizontalResizer = $('horizontalResizer');
const codeEditorWrap = $('codeEditorWrap');

if (horizontalResizer && codeEditorWrap) {
  let isDragging = false;
  let startY = 0;
  let startHeight = 0;

  horizontalResizer.addEventListener('mousedown', (e) => {
    isDragging = true;
    startY = e.clientY;
    startHeight = codeEditorWrap.getBoundingClientRect().height;
    horizontalResizer.classList.add('dragging');
    document.body.style.cursor = 'row-resize';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dy = e.clientY - startY;
    const newHeight = Math.max(100, startHeight + dy);
    // Max height should not exceed viewport significantly
    const maxH = window.innerHeight - 200;
    codeEditorWrap.style.height = Math.min(newHeight, maxH) + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      horizontalResizer.classList.remove('dragging');
      document.body.style.cursor = '';
    }
  });
}

/* ── Diagram type chips ───────────────────────────────────────────────────── */
document.querySelectorAll('.type-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.type-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    state.diagramType = chip.dataset.type;
    updatePromptHint(state.diagramType);
  });
});

function updatePromptHint(type) {
  const hints = {
    flowchart: 'e.g. "User registration and email verification flow"',
    sequence: 'e.g. "API authentication handshake between client and server"',
    erd: 'e.g. "E-commerce database with users, orders, and products"',
    class: 'e.g. "Animal class hierarchy with Dog and Cat subclasses"',
    custom: 'e.g. "State machine for a traffic light system"',
  };
  const hintEl = $('promptHint');
  if (hintEl) hintEl.textContent = hints[type] || '';
}

/* ── Toast ────────────────────────────────────────────────────────────────── */
function showToast(msg, type = 'success') {
  const toast = $('studioToast');
  toast.textContent = msg;
  toast.className = `studio-toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 3500);
}

/* ── Loading state ────────────────────────────────────────────────────────── */
function setGenerating(loading, label = null) {
  const btn = generateBtn;
  if (loading) {
    btn.classList.add('loading');
    btn.disabled = true;
    if (label) {
      const lbl = btn.querySelector('.btn-label span:last-child');
      if (lbl) lbl.textContent = label;
    }
    previewLoading.classList.add('active');
  } else {
    btn.classList.remove('loading');
    btn.disabled = false;
    // Reset label
    const lbl = btn.querySelector('.btn-label span:last-child');
    if (lbl) lbl.textContent = 'Generate Diagram';
    previewLoading.classList.remove('active');
  }
}

/* ── Strip white backgrounds Mermaid injects into the SVG ────────────────── */
function patchSvgColors(svgEl) {
  if (!svgEl) return;
  const WHITE = new Set(['white', '#ffffff', '#fff', 'rgb(255,255,255)', 'rgb(255, 255, 255)']);
  svgEl.style.background = 'transparent';
  svgEl.querySelectorAll('*').forEach(el => {
    const fill = el.getAttribute('fill');
    if (fill && WHITE.has(fill.toLowerCase().replace(/\s/g, ''))) el.setAttribute('fill', 'transparent');
    if (el.style.fill && WHITE.has(el.style.fill.toLowerCase().replace(/\s/g, ''))) el.style.fill = 'transparent';
    if (el.style.background && WHITE.has(el.style.background.toLowerCase().replace(/\s/g, ''))) el.style.background = 'transparent';
    if (el.style.backgroundColor && WHITE.has(el.style.backgroundColor.toLowerCase().replace(/\s/g, ''))) el.style.backgroundColor = 'transparent';
  });
  svgEl.querySelectorAll('style').forEach(styleEl => {
    styleEl.textContent = styleEl.textContent
      .replace(/background(-color)?:\s*(white|#fff(fff)?)\s*;?/gi, 'background:transparent;')
      .replace(/fill:\s*(white|#fff(fff)?)\s*;?/gi, 'fill:transparent;');
  });
  svgEl.removeAttribute('width');
  svgEl.removeAttribute('height');
  svgEl.style.cssText += `width:100% !important;height:100% !important;max-width:100% !important;display:block;background:transparent !important;`;
  svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');
}

/* ── Removed Theme Switcher Event Listener ── */
/* ══════════════════════════════════════════════════════
   FEATURE: CLICK-TO-EDIT NODES
   When the user clicks on a node label in the SVG preview,
   a prompt box opens to rename it, then the Mermaid code
   is patched and re-rendered — no backend call needed.
══════════════════════════════════════════════════════ */
function attachClickToEdit(svgEl) {
  if (!svgEl) return;
  // Mermaid's node label text lives in <span> inside a <foreignObject> or in <text> tags
  const labelEls = svgEl.querySelectorAll('.label, text, .nodeLabel, foreignObject span');

  labelEls.forEach(el => {
    const rawText = el.textContent?.trim();
    if (!rawText || rawText.length < 2) return;

    el.style.cursor = 'pointer';
    el.title = `Click to rename: "${rawText}"`;

    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const newLabel = prompt(`Rename node:\n"${rawText}"`, rawText);
      if (!newLabel || newLabel === rawText) return;

      // Patch the Mermaid code: replace the exact label text
      const escaped = rawText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(?<=[\\[\\(\\{>"']|^\\s*)${escaped}(?=[\\]\\)\\}"'<]|\\s*$)`, 'gm');
      let newCode = state.currentMermaidCode.replace(regex, newLabel);

      // Simple fallback if regex doesn't match: plain string replace
      if (newCode === state.currentMermaidCode) {
        newCode = state.currentMermaidCode.replaceAll(rawText, newLabel);
      }

      if (codeEditor) codeEditor.value = newCode;
      state.currentMermaidCode = newCode;
      const versionNum = state.allVersions.find(v => v.version_id === state.currentVersionId)?.version_number || 1;
      renderPreview(newCode, state.diagramType, versionNum, state.currentSvgPath);
      showToast(`Node renamed to "${newLabel}" — click Apply Edit to save.`);
    });
  });
}

/* ══════════════════════════════════════════════════════
   FEATURE: VERSION DIFF VIEWER
   Computes a simple line-level diff between the current
   version and the previous one and renders it in the
   diff panel.
══════════════════════════════════════════════════════ */
const diffToggleBtn = $('diffToggleBtn');
const diffPanel = $('diffPanel');
const diffContent = $('diffContent');

function computeLineDiff(oldCode, newCode) {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');
  const maxLen = Math.max(oldLines.length, newLines.length);
  const result = [];

  for (let i = 0; i < maxLen; i++) {
    const o = oldLines[i] ?? null;
    const n = newLines[i] ?? null;
    if (o === null) { result.push({ type: 'add', line: n }); }
    else if (n === null) { result.push({ type: 'del', line: o }); }
    else if (o !== n) {
      result.push({ type: 'del', line: o });
      result.push({ type: 'add', line: n });
    } else {
      result.push({ type: 'same', line: n });
    }
  }
  return result;
}

function renderDiff() {
  if (!diffContent) return;
  const currentVersion = state.allVersions.find(v => v.version_id === state.currentVersionId);
  if (!currentVersion) {
    diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;">No version selected.</p>';
    return;
  }

  const prevVersion = state.allVersions.find(v => v.version_number === currentVersion.version_number - 1);
  if (!prevVersion) {
    diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;font-size:0.82rem;">This is the first version — no previous version to compare.</p>';
    return;
  }

  const diff = computeLineDiff(prevVersion.mermaid_code || '', currentVersion.mermaid_code || '');

  if (!diff.length) {
    diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;font-size:0.82rem;">No differences found.</p>';
    return;
  }

  diffContent.innerHTML = diff.map(d => {
    const prefix = d.type === 'add' ? '+ ' : d.type === 'del' ? '- ' : '  ';
    const color = d.type === 'add' ? '#86efac' : d.type === 'del' ? '#fca5a5' : '#94a3b8';
    const bg = d.type === 'add' ? 'rgba(134,239,172,0.08)' : d.type === 'del' ? 'rgba(252,165,165,0.08)' : 'transparent';
    return `<div style="color:${color};background:${bg};padding:0 8px;font-family:monospace;font-size:0.75rem;white-space:pre;">${escHtml(prefix + d.line)}</div>`;
  }).join('');
}

if (diffToggleBtn) {
  diffToggleBtn.addEventListener('click', () => {
    const isOpen = diffPanel?.style.display !== 'none';
    if (diffPanel) diffPanel.style.display = isOpen ? 'none' : 'block';
    diffToggleBtn.textContent = isOpen ? '🔀 Show Diff' : '✕ Hide Diff';
    if (!isOpen) renderDiff();
  });
}

/* ══════════════════════════════════════════════════════
   FEATURE: MERMAID VALIDATION + RETRY
   After getting code from the backend, parse it with
   mermaid.parse(). If it fails, re-call the backend
   with the error as feedback (up to MAX_RETRIES times).
══════════════════════════════════════════════════════ */
const MAX_RETRIES = 2;

/**
 * Validate mermaid code with mermaid.parse().
 * Returns null on success, or an error string on failure.
 */
async function validateMermaid(code) {
  // Strip any %%{init}%% directive before parsing (mermaid.parse may reject it)
  const stripped = code.replace(/^%%\{init:.*?\}%%\s*/s, '').trimStart();
  try {
    await mermaid.parse(stripped);
    return null;  // valid
  } catch (err) {
    return err?.message || String(err);
  }
}

/**
 * Call the generate endpoint with optional error_feedback, validate the result,
 * and retry up to MAX_RETRIES times if mermaid.parse() fails.
 *
 * @param {Object} payload  - JSON body for POST /api/diagrams/generate
 * @returns {Object}        - Diagram response from the backend
 */
async function generateWithRetry(payload) {
  let lastError = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) {
      setGenerating(true, `Retrying… (${attempt}/${MAX_RETRIES})`);
    }
    const body = { ...payload, error_feedback: lastError || '' };
    const res = await fetch('/api/diagrams/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({ detail: 'Unknown error' }))).detail;
      throw new Error(detail);
    }
    const data = await res.json();
    const mermaidCode = data.current_version?.mermaid_code || '';
    const parseError = await validateMermaid(mermaidCode);
    if (!parseError) {
      if (attempt > 0) showToast(`Diagram fixed after ${attempt} retry attempt(s).`, 'success');
      return data;
    }
    lastError = parseError;
    console.warn(`[diagram_studio] Mermaid parse error on attempt ${attempt + 1}:`, parseError);
  }
  // All retries exhausted — return the last result anyway (backend diagram is saved)
  console.error('[diagram_studio] Max retries reached, returning last result');
  // Re-fetch the last saved diagram
  const res = await fetch('/api/diagrams/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, error_feedback: lastError || '' }),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({ detail: 'Unknown error' }))).detail;
    throw new Error(detail);
  }
  return res.json();
}

/**
 * Call the regenerate endpoint with retry logic.
 *
 * @param {string} diagramId
 * @param {Object} payload  - JSON body for POST /api/diagrams/{id}/regenerate
 * @returns {Object}        - Diagram response from the backend
 */
async function regenerateWithRetry(diagramId, payload) {
  let lastError = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) {
      setGenerating(true, `Retrying… (${attempt}/${MAX_RETRIES})`);
    }
    const body = { ...payload, error_feedback: lastError || '' };
    const res = await fetch(`/api/diagrams/${diagramId}/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({ detail: 'Regeneration failed' }))).detail;
      throw new Error(detail);
    }
    const data = await res.json();
    const mermaidCode = data.current_version?.mermaid_code || '';
    const parseError = await validateMermaid(mermaidCode);
    if (!parseError) {
      if (attempt > 0) showToast(`Diagram fixed after ${attempt} retry attempt(s).`, 'success');
      return data;
    }
    lastError = parseError;
    console.warn(`[diagram_studio] Mermaid parse error on regenerate attempt ${attempt + 1}:`, parseError);
  }
  // Return last fetched
  const res = await fetch(`/api/diagrams/${diagramId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, error_feedback: lastError || '' }),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({ detail: 'Regeneration failed' }))).detail;
    throw new Error(detail);
  }
  return res.json();
}

/* ── CORE: render mermaid code in the browser ────────────────────────────── */
async function renderPreview(mermaidCode, diagramType, versionNumber, svgPath) {
  if (!mermaidCode) return;
  state.currentSvgPath = svgPath;
  state.currentMermaidCode = mermaidCode;

  previewEmpty.style.display = 'none';
  previewSvgWrap.style.display = 'block';
  previewSvgWrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;opacity:.35;font-size:.85rem;color:#94a3b8;">Rendering…</div>`;

  try {
    const uid = `mmd-${Date.now()}`;
    const { svg } = await mermaid.render(uid, mermaidCode);
    previewSvgWrap.innerHTML = svg;
    const svgEl = previewSvgWrap.querySelector('svg');
    patchSvgColors(svgEl);

    // ── FEATURE: Click-to-Edit — attach after every render ────────────────
    attachClickToEdit(svgEl);

  } catch (err) {
    console.error('[mermaid]', err);
    previewSvgWrap.innerHTML = `
      <div style="color:#f87171;padding:2rem;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;font-family:monospace;">
        <div style="font-size:1.4rem;margin-bottom:.5rem">⚠️</div>
        <div style="opacity:.8;margin-bottom:.75rem">Mermaid parse error — edit the code and click Apply Edit.</div>
        <pre style="background:#1e1e2e;border-radius:6px;padding:1rem;overflow:auto;font-size:.7rem;max-height:160px;white-space:pre-wrap;color:#fca5a5;max-width:100%">
${escHtml(err.message || String(err))}</pre>
      </div>`;
  }

  if (previewMeta) previewMeta.style.display = 'flex';
  if (previewBadge) previewBadge.textContent = diagramType;
  if (previewVersion) previewVersion.textContent = `v${versionNumber}`;
}

/* ── Version list ─────────────────────────────────────────────────────────── */
function renderVersions(versions, activeVersionId) {
  if (!versionsListEl) return;
  // Store the full version objects (including mermaid_code) for diff
  state.allVersions = (versions || []).map(v => ({ ...v }));
  versionsListEl.innerHTML = '';
  if (!versions?.length) {
    versionsListEl.innerHTML = '<p class="version-empty">No versions yet.</p>';
    return;
  }
  [...versions].reverse().forEach(v => {
    const item = document.createElement('div');
    item.className = 'version-item' + (v.version_id === activeVersionId ? ' active' : '');
    item.dataset.versionId = v.version_id;
    const date = new Date(v.created_at).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
    // Strip [edited] prefix for display
    const displayPrompt = (v.prompt || '').replace(/^\[edited\]\s*/, '');
    item.innerHTML = `
      <div class="version-badge">v${v.version_number}</div>
      <div class="version-info">
        <div class="version-prompt">${escHtml(displayPrompt)}</div>
        <div class="version-date">${date}</div>
      </div>`;
    item.addEventListener('click', () => loadVersion(v));
    versionsListEl.appendChild(item);
  });
}

function loadVersion(v) {
  state.currentVersionId = v.version_id;
  state.currentMermaidCode = v.mermaid_code;
  if (codeEditor) codeEditor.value = v.mermaid_code;
  // Use state.diagramType (set from diagram response), not hardcoded 'flowchart'
  renderPreview(v.mermaid_code, state.diagramType || 'flowchart', v.version_number, v.svg_path);
  document.querySelectorAll('.version-item').forEach(el =>
    el.classList.toggle('active', el.dataset.versionId === v.version_id)
  );
  // Auto-refresh diff if panel is open
  if (diffPanel && diffPanel.style.display !== 'none') renderDiff();
}

function applyDiagramResponse(data) {
  state.currentDiagramId = data.diagram_id;
  // ── VERSION HISTORY FIX: always sync diagram_type from API response ──────
  if (data.diagram_type) {
    state.diagramType = data.diagram_type;
    // Sync the type-chip UI
    document.querySelectorAll('.type-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.type === data.diagram_type);
    });
  }
  if (data.current_version) {
    state.currentVersionId = data.current_version.version_id;
    state.currentMermaidCode = data.current_version.mermaid_code;
    if (codeEditor) codeEditor.value = data.current_version.mermaid_code;
    renderPreview(
      data.current_version.mermaid_code,
      data.diagram_type,
      data.current_version.version_number,
      data.current_version.svg_path,
    );
  }
  // Store full versions list (all fields) so diff and loadVersion can read mermaid_code
  renderVersions(data.versions, state.currentVersionId);
  if (regenBtn) regenBtn.disabled = false;
  if (applyEditBtn) applyEditBtn.disabled = false;
  if (downloadBtn) downloadBtn.disabled = false;
}

/* ── API calls ────────────────────────────────────────────────────────────── */
if (generateBtn) {
  generateBtn.addEventListener('click', async () => {
    const project = projectSelect?.value || '';
    const prompt = promptInput?.value.trim() || '';
    if (!project) { showToast('Please select a project first.', 'error'); return; }
    if (!prompt) { showToast('Please enter a description.', 'error'); return; }
    setGenerating(true, 'Generating…');
    try {
      const data = await generateWithRetry({
        project_name: project,
        prompt,
        diagram_type: state.diagramType,
        selected_document_ids: getSelectedDocIds(),
      });
      applyDiagramResponse(data);
      showToast('Diagram generated!');
    } catch (e) { showToast(e.message || 'Generation failed.', 'error'); }
    finally { setGenerating(false); }
  });
}

if (regenBtn) {
  regenBtn.addEventListener('click', async () => {
    if (!state.currentDiagramId) { showToast('No diagram loaded.', 'error'); return; }
    const prompt = promptInput?.value.trim() || '';
    if (!prompt) { showToast('Please enter a description.', 'error'); return; }
    setGenerating(true, 'Regenerating…');
    try {
      const data = await regenerateWithRetry(state.currentDiagramId, {
        prompt,
        diagram_type: state.diagramType,
        selected_document_ids: getSelectedDocIds(),
      });
      applyDiagramResponse(data);
      showToast('New version generated!');
    } catch (e) { showToast(e.message || 'Regeneration failed.', 'error'); }
    finally { setGenerating(false); }
  });
}

if (applyEditBtn) {
  applyEditBtn.addEventListener('click', async () => {
    if (!state.currentDiagramId) { showToast('No diagram loaded.', 'error'); return; }
    const code = codeEditor?.value.trim() || '';
    if (!code) { showToast('Code editor is empty.', 'error'); return; }
    applyEditBtn.disabled = true; applyEditBtn.textContent = 'Applying…';
    previewLoading.classList.add('active');
    try {
      const res = await fetch(`/api/diagrams/${state.currentDiagramId}/edit`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mermaid_code: code }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: 'Edit failed' }))).detail);
      applyDiagramResponse(await res.json());
      showToast('Edit saved as new version!');
    } catch (e) { showToast(e.message || 'Could not apply edit.', 'error'); }
    finally {
      applyEditBtn.disabled = false; applyEditBtn.textContent = '✏️ Apply Edit';
      previewLoading.classList.remove('active');
    }
  });
}

if (downloadBtn) {
  downloadBtn.addEventListener('click', async () => {
    if (state.currentSvgPath) {
      try {
        const res = await fetch(state.currentSvgPath);
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          Object.assign(document.createElement('a'), { href: url, download: `diagram_v${state.currentVersionId || 'latest'}.svg` }).click();
          URL.revokeObjectURL(url);
          showToast('SVG downloading…'); return;
        }
      } catch (_) { }
    }
    const svgEl = previewSvgWrap?.querySelector('svg');
    if (!svgEl) { showToast('Nothing to download yet.', 'error'); return; }
    const blob = new Blob([new XMLSerializer().serializeToString(svgEl)], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    Object.assign(document.createElement('a'), { href: url, download: `diagram_v${state.currentVersionId || 'latest'}.svg` }).click();
    URL.revokeObjectURL(url);
    showToast('SVG downloading…');
  });
}

/* ── Projects ─────────────────────────────────────────────────────────────── */
async function loadProjects() {
  if (!projectSelect) return;
  try {
    const [srsRes, diagRes] = await Promise.allSettled([fetch('/api/my-documents'), fetch('/api/diagrams/projects')]);
    const names = new Set();
    if (srsRes.status === 'fulfilled' && srsRes.value.ok) (await srsRes.value.json()).forEach(d => names.add(d.project_name));
    if (diagRes.status === 'fulfilled' && diagRes.value.ok) (await diagRes.value.json()).forEach(n => names.add(n));
    projectSelect.innerHTML = '<option value="">— Select project —</option>';
    [...names].sort().forEach(n => {
      const o = document.createElement('option'); o.value = n; o.textContent = n;
      projectSelect.appendChild(o);
    });
    const c = document.createElement('option'); c.value = '__custom__'; c.textContent = '+ New project name…';
    projectSelect.appendChild(c);
  } catch (e) { console.warn('Could not load projects', e); }
}

if (projectSelect) {
  projectSelect.addEventListener('change', async () => {
    if (projectSelect.value === '__custom__') {
      const name = prompt('Enter a new project name:')?.trim();
      if (name) {
        const opt = new Option(name, name, true, true);
        projectSelect.insertBefore(opt, projectSelect.lastElementChild);
        projectSelect.value = name;
      } else { projectSelect.value = ''; return; }
    }
  });
}

/* ── Utility ──────────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  await loadProjects();

  const params = new URLSearchParams(window.location.search);

  if (params.has('project')) {
    const p = params.get('project');
    const exists = Array.from(projectSelect.options).some(o => o.value === p);
    if (!exists && projectSelect) {
      const opt = new Option(p, p, true, true);
      projectSelect.insertBefore(opt, projectSelect.lastElementChild);
    }
    if (projectSelect) {
      projectSelect.value = p;
    }
  }

  if (params.has('type')) {
    const t = params.get('type');
    document.querySelectorAll('.type-chip').forEach(c => c.classList.remove('active'));
    const chip = document.querySelector(`.type-chip[data-type="${t}"]`);
    if (chip) chip.classList.add('active');
    state.diagramType = t || 'flowchart';
  }

  if (params.has('prompt') && promptInput) {
    promptInput.value = params.get('prompt');
  }

  updatePromptHint(state.diagramType || 'flowchart');
  if (regenBtn) regenBtn.disabled = true;
  if (applyEditBtn) applyEditBtn.disabled = true;
  if (downloadBtn) downloadBtn.disabled = true;
  if (diffPanel) diffPanel.style.display = 'none';

  // ── AUTO-GENERATE: if navigated from project page with project + prompt params
  // Trigger after a brief delay so the UI is fully painted
  if (params.has('project') && params.has('prompt') && promptInput?.value.trim()) {
    setTimeout(() => {
      if (generateBtn && !generateBtn.disabled) {
        showToast('Auto-generating diagram from project…', 'success');
        generateBtn.click();
      }
    }, 400);
  }
});