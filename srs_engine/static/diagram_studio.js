/* ─────────────────────────────────────────────────────────────────────────────
   diagram_studio.js  v3  — Complete rewrite of UI logic

   New features vs v2:
     · 7 diagram types for technical projects (flowchart, sequence, erd,
       class, state, gantt, mindmap) — user picks freely, no restrictions.
     · Detail Level selector (Brief / Standard / Detailed / Comprehensive)
       injected into DOM automatically if not already in the template.
     · Context indicator: shows "SRS context loaded" badge when project has
       a generated SRS to feed the LLM.
     · Versioning fix: diagram_type always synced from API response.
     · Validation Retry: mermaid.parse() client-side, up to MAX_RETRIES.
     · Click-to-Edit nodes inline.
     · Version Diff viewer.
     · Server-side validation runs inside diagram_service; client retries
       independently — double safety net.
───────────────────────────────────────────────────────────────────────────── */

/* ── Mermaid init ─────────────────────────────────────────────────────────── */
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",

  themeVariables: {
    primaryColor: "#0a1023",
    primaryBorderColor: "#4f8eff",
    primaryTextColor: "#e8eeff",
    lineColor: "#64748b",
    secondaryColor: "#0a0f1e",
    tertiaryColor: "#06090f",
    fontFamily: "DM Sans"
  },

  flowchart: {
    nodeSpacing: 60,
    rankSpacing: 80,
    padding: 20,
    curve: "basis"
  }
})

/* ══════════════════════════════════════════════════════════════════════════════
   DIAGRAM TYPE DEFINITIONS
   All 7 types relevant for technical / software projects.
   User picks freely — no "recommended" restriction.
══════════════════════════════════════════════════════════════════════════════ */
const DIAGRAM_TYPES = [
  {
    type: 'flowchart',
    label: 'Flowchart',
    icon: '⬡',
    desc: 'System or process flow',
    hint: 'e.g. "User registration and email verification flow"',
  },
  {
    type: 'sequence',
    label: 'Sequence',
    icon: '↔',
    desc: 'API / service interaction',
    hint: 'e.g. "OAuth2 authentication handshake between client, server, and IdP"',
  },
  {
    type: 'erd',
    label: 'ERD',
    icon: '⊟',
    desc: 'Database schema',
    hint: 'e.g. "E-commerce DB with users, orders, products, and payments"',
  },
  {
    type: 'class',
    label: 'Class',
    icon: '◫',
    desc: 'Object model / architecture',
    hint: 'e.g. "Microservices architecture for a payment gateway with retry and fallback strategies"',
  },
  {
    type: 'state',
    label: 'State',
    icon: '◎',
    desc: 'State machine / lifecycle',
    hint: 'e.g. "Order lifecycle: placed → confirmed → shipped → delivered"',
  },
  {
    type: 'gantt',
    label: 'Gantt',
    icon: '▤',
    desc: 'Project / sprint timeline',
    hint: 'e.g. "Q1 sprint plan with backend, frontend, and testing phases"',
  },
  {
    type: 'mindmap',
    label: 'Mind Map',
    icon: '✦',
    desc: 'Feature / requirement map',
    hint: 'e.g. "Feature breakdown of the user management module"',
  },
];

/* ── Detail Levels ────────────────────────────────────────────────────────── */
const DETAIL_LEVELS = [
  { value: 'brief',         label: 'Brief',         desc: '5–10 nodes, top-level only' },
  { value: 'standard',      label: 'Standard',      desc: '10–20 nodes, key flows' },
  { value: 'detailed',      label: 'Detailed',      desc: '20–40 nodes, sub-components' },
  { value: 'comprehensive', label: 'Comprehensive', desc: '40+ nodes, all edge cases' },
];

/* ── State ────────────────────────────────────────────────────────────────── */
const state = {
  currentDiagramId: null,
  currentVersionId: null,
  currentSvgPath:   null,
  currentMermaidCode: null,
  diagramType:      'flowchart',
  detailLevel:      'standard',
  allVersions:      [],
};

/* ── DOM helpers ──────────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

const projectSelect   = $('projectSelect');
const promptInput     = $('promptInput');
const generateBtn     = $('generateBtn');
const regenBtn        = $('regenBtn');
const previewSvgWrap  = $('previewSvgWrap');
const previewEmpty    = $('previewEmpty');
const previewLoading  = $('previewLoading');
const previewMeta     = $('previewMeta');
const codeEditor      = $('codeEditor');
const applyEditBtn    = $('applyEditBtn');
const downloadBtn     = $('downloadBtn');
const versionsListEl  = $('versionsList');
const previewBadge    = $('previewBadge');
const previewVersion  = $('previewVersion');

/* ══════════════════════════════════════════════════════════════════════════════
   INJECT DIAGRAM TYPE CHIPS + DETAIL LEVEL SELECTOR
   Creates or rebuilds the control row dynamically so the HTML template
   doesn't need manual updates when new types are added.
══════════════════════════════════════════════════════════════════════════════ */

function enableDiagramZoom() {
  const svg = document.querySelector("#previewSvgWrap svg")
  if (!svg) return

  panzoom(svg, {
    maxZoom: 4,
    minZoom: 0.5,
    bounds: true,
    boundsPadding: 0.1
  })
}

function _buildTypeChips() {
  const container = document.querySelector('.type-chips') || _createChipsContainer();
  if (!container) return;

  // Clear existing chips (avoid duplicates on hot-reload)
  container.innerHTML = '';

  DIAGRAM_TYPES.forEach(({ type, label, icon, desc }) => {
    const chip = document.createElement('button');
    chip.className = `type-chip${type === state.diagramType ? ' active' : ''}`;
    chip.dataset.type = type;
    chip.title = desc;
    chip.innerHTML = `<span class="chip-icon">${icon}</span><span class="chip-label">${label}</span>`;
    chip.addEventListener('click', () => {
      document.querySelectorAll('.type-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.diagramType = type;
      _updatePromptHint(type);
    });
    container.appendChild(chip);
  });
}

function _createChipsContainer() {
  // If the template has no .type-chips, inject one before the prompt area
  const promptArea = promptInput?.closest('.form-group') || promptInput?.parentElement;
  if (!promptArea) return null;
  const wrapper = document.createElement('div');
  wrapper.className = 'type-chips';
  wrapper.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;';
  promptArea.parentElement.insertBefore(wrapper, promptArea);
  return wrapper;
}

function _buildDetailSelector() {
  // Look for an existing select; if missing, inject one
  let sel = $('detailLevelSelect');
  if (!sel) {
    sel = document.createElement('select');
    sel.id = 'detailLevelSelect';
    sel.style.cssText = (
      'background:#1a1f2e;color:#e2e8f0;border:1px solid #334155;border-radius:6px;'
      + 'padding:6px 10px;font-size:0.82rem;cursor:pointer;margin-bottom:10px;width:100%;'
    );

    const label = document.createElement('label');
    label.htmlFor = 'detailLevelSelect';
    label.textContent = 'Detail Level';
    label.style.cssText = 'display:block;font-size:0.75rem;color:#94a3b8;margin-bottom:4px;';

    const wrapper = document.createElement('div');
    wrapper.appendChild(label);
    wrapper.appendChild(sel);

    // Insert before the generate button
    const btnParent = generateBtn?.parentElement;
    if (btnParent) {
      btnParent.insertBefore(wrapper, generateBtn);
    }
  }

  // Populate options
  sel.innerHTML = '';
  DETAIL_LEVELS.forEach(({ value, label, desc }) => {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = `${label} — ${desc}`;
    opt.selected = value === state.detailLevel;
    sel.appendChild(opt);
  });

  sel.addEventListener('change', () => {
    state.detailLevel = sel.value;
  });

  return sel;
}

/* ── Context indicator ────────────────────────────────────────────────────── */
function _showContextBadge(hasContext) {
  let badge = $('contextBadge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'contextBadge';
    badge.style.cssText = (
      'font-size:0.72rem;padding:3px 8px;border-radius:12px;display:inline-block;'
      + 'margin-bottom:8px;transition:all .3s;'
    );
    const anchor = promptInput?.parentElement;
    if (anchor) anchor.insertBefore(badge, anchor.firstChild);
  }
  if (hasContext) {
    badge.textContent = '✓ SRS context loaded — LLM has project knowledge';
    badge.style.cssText += 'background:rgba(0,229,204,0.12);color:#00e5cc;border:1px solid rgba(0,229,204,0.3);';
  } else {
    badge.textContent = '⚠ No SRS found — generate one first for richer diagrams';
    badge.style.cssText += 'background:rgba(251,191,36,0.1);color:#fbbf24;border:1px solid rgba(251,191,36,0.25);';
  }
}

async function _checkContextAvailability(projectName) {
  if (!projectName) { _showContextBadge(false); return; }
  try {
    // A quick probe: list parsed docs; if endpoint succeeds the project exists in SRS
    const res = await fetch(`/api/diagrams/project/${encodeURIComponent(projectName)}`);
    // We check if there's a _sections.json by seeing if project has diagrams or just probe
    // Actually we can check via /api/chat/documents
    const chatRes = await fetch('/api/chat/documents');
    if (chatRes.ok) {
      const docs = await chatRes.json();
      const hasSRS = Array.isArray(docs) && docs.some(d => d.project_name === projectName);
      _showContextBadge(hasSRS);
    } else {
      _showContextBadge(false);
    }
  } catch (_) {
    _showContextBadge(false);
  }
}

/* ── Quota Check ──────────────────────────────────────────────────────────── */
async function updateDiagramQuota(projectName) {
  try {
    const res = await fetch('/api/my-quota');
    const q = await res.json();
    const isAdmin = q.is_admin || false;
    const limit = q.diag_limit || 2;
    const projData = q.projects?.[projectName] || {};
    const used = projData.diagram_count || 0;
    const remaining = limit - used;
    const el = document.getElementById('diagram-quota');
    if (!el) return;
    el.style.display = 'block';

    if (isAdmin) {
      el.innerHTML = `✨ Administrative access: Unlimited diagrams available for "${projectName}"`;
      el.className = 'quota-banner quota-admin';
      document.getElementById('generateBtn')?.removeAttribute('disabled');
      return;
    }

    if (remaining <= 0) {
      el.innerHTML = `🔒 You have used all ${limit} diagram slots for this project.`;
      el.className = 'quota-banner quota-exhausted';
      document.getElementById('generateBtn')?.setAttribute('disabled', 'true');
    } else {
      el.innerHTML = `🎨 ${remaining} of ${limit} diagrams remaining for "${projectName}"`;
      el.className = 'quota-banner';
      document.getElementById('generateBtn')?.removeAttribute('disabled');
    }
  } catch(e) {}
}

/* ── Prompt hints ─────────────────────────────────────────────────────────── */
function _updatePromptHint(type) {
  const hintEl = $('promptHint');
  if (!hintEl) return;
  const entry = DIAGRAM_TYPES.find(d => d.type === type);
  hintEl.textContent = entry?.hint || '';
}

/* ── Toast ────────────────────────────────────────────────────────────────── */
function showToast(msg, type = 'success') {
  const toast = $('studioToast');
  if (!toast) { console.log(`[toast] ${type}: ${msg}`); return; }
  toast.textContent = msg;
  toast.className = `studio-toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 3500);
}

/* ── Loading state ────────────────────────────────────────────────────────── */
function setGenerating(loading, label = null) {
  if (!generateBtn) return;
  if (loading) {
    generateBtn.classList.add('loading');
    generateBtn.disabled = true;
    const lbl = generateBtn.querySelector('.btn-label span:last-child');
    if (lbl && label) lbl.textContent = label;
    previewLoading?.classList.add('active');
  } else {
    generateBtn.classList.remove('loading');
    generateBtn.disabled = false;
    const lbl = generateBtn.querySelector('.btn-label span:last-child');
    if (lbl) lbl.textContent = 'Generate Diagram';
    previewLoading?.classList.remove('active');
  }
}

/* ── SVG white-background patch ──────────────────────────────────────────── */
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

/* ══════════════════════════════════════════════════════════════════════════════
   CLICK-TO-EDIT NODES
══════════════════════════════════════════════════════════════════════════════ */
function attachClickToEdit(svgEl) {
  if (!svgEl) return;
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
      const escaped = rawText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(?<=[\\[\\(\\{>"']|^\\s*)${escaped}(?=[\\]\\)\\}"'<]|\\s*$)`, 'gm');
      let newCode = state.currentMermaidCode.replace(regex, newLabel);
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

/* ══════════════════════════════════════════════════════════════════════════════
   VERSION DIFF VIEWER
══════════════════════════════════════════════════════════════════════════════ */
const diffToggleBtn = $('diffToggleBtn');
const diffPanel     = $('diffPanel');
const diffContent   = $('diffContent');

function computeLineDiff(oldCode, newCode) {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');
  const maxLen   = Math.max(oldLines.length, newLines.length);
  const result   = [];
  for (let i = 0; i < maxLen; i++) {
    const o = oldLines[i] ?? null;
    const n = newLines[i] ?? null;
    if      (o === null) { result.push({ type: 'add', line: n }); }
    else if (n === null) { result.push({ type: 'del', line: o }); }
    else if (o !== n)    { result.push({ type: 'del', line: o }); result.push({ type: 'add', line: n }); }
    else                 { result.push({ type: 'same', line: n }); }
  }
  return result;
}

function renderDiff() {
  if (!diffContent) return;
  const cur  = state.allVersions.find(v => v.version_id === state.currentVersionId);
  if (!cur) { diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;">No version selected.</p>'; return; }
  const prev = state.allVersions.find(v => v.version_number === cur.version_number - 1);
  if (!prev) { diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;font-size:.82rem;">First version — nothing to compare.</p>'; return; }
  const diff = computeLineDiff(prev.mermaid_code || '', cur.mermaid_code || '');
  if (!diff.length) { diffContent.innerHTML = '<p style="color:#94a3b8;padding:12px;">No differences found.</p>'; return; }
  diffContent.innerHTML = diff.map(d => {
    const prefix = d.type === 'add' ? '+ ' : d.type === 'del' ? '- ' : '  ';
    const color  = d.type === 'add' ? '#86efac' : d.type === 'del' ? '#fca5a5' : '#94a3b8';
    const bg     = d.type === 'add' ? 'rgba(134,239,172,.08)' : d.type === 'del' ? 'rgba(252,165,165,.08)' : 'transparent';
    return `<div style="color:${color};background:${bg};padding:0 8px;font-family:monospace;font-size:.75rem;white-space:pre;">${escHtml(prefix + d.line)}</div>`;
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

/* ══════════════════════════════════════════════════════════════════════════════
   CLIENT-SIDE MERMAID VALIDATION + RETRY
   Acts as a second safety net after server-side validation in diagram_service.
══════════════════════════════════════════════════════════════════════════════ */
const MAX_RETRIES = 2;

async function validateMermaid(code) {
  // Strip %%{init:...}%% before parsing (mermaid.parse rejects it)
  const stripped = code.replace(/^%%\{init.*?\}%%\s*/s, '').trimStart();
  try {
    await mermaid.parse(stripped);
    return null;
  } catch (err) {
    return err?.message || String(err);
  }
}

async function generateWithRetry(payload) {
  let lastError = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) setGenerating(true, `Retrying… (${attempt}/${MAX_RETRIES})`);
    const res = await fetch('/api/diagrams/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, error_feedback: lastError || '' }),
    });
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({ detail: 'Unknown error' }))).detail;
      throw new Error(detail);
    }
    const data = await res.json();
    const code = data.current_version?.mermaid_code || '';
    const parseError = await validateMermaid(code);
    if (!parseError) {
      if (attempt > 0) showToast(`Fixed after ${attempt} retry attempt(s).`);
      return data;
    }
    lastError = parseError;
    console.warn(`[diagram_studio] Client parse error attempt ${attempt + 1}:`, parseError);
  }
  // Exhausted — return whatever we have (server stored it)
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

async function regenerateWithRetry(diagramId, payload) {
  let lastError = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) setGenerating(true, `Retrying… (${attempt}/${MAX_RETRIES})`);
    const res = await fetch(`/api/diagrams/${diagramId}/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, error_feedback: lastError || '' }),
    });
    if (!res.ok) {
      const detail = (await res.json().catch(() => ({ detail: 'Regeneration failed' }))).detail;
      throw new Error(detail);
    }
    const data = await res.json();
    const code = data.current_version?.mermaid_code || '';
    const parseError = await validateMermaid(code);
    if (!parseError) {
      if (attempt > 0) showToast(`Fixed after ${attempt} retry attempt(s).`);
      return data;
    }
    lastError = parseError;
    console.warn(`[diagram_studio] Client parse error on regen attempt ${attempt + 1}:`, parseError);
  }
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

/* ── Core: render Mermaid in browser ─────────────────────────────────────── */
async function renderPreview(mermaidCode, diagramType, versionNumber, svgPath) {
  if (!mermaidCode || !previewSvgWrap) return;
  state.currentSvgPath = svgPath;
  state.currentMermaidCode = mermaidCode;

  if (previewEmpty) previewEmpty.style.display = 'none';
  previewSvgWrap.style.display = 'block';
  previewSvgWrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;opacity:.35;font-size:.85rem;color:#94a3b8;">Rendering…</div>`;

  try {
    const uid = `mmd-${Date.now()}`;
    const { svg } = await mermaid.render(uid, mermaidCode);
    previewSvgWrap.innerHTML = svg;
    const svgEl = previewSvgWrap.querySelector('svg');
    patchSvgColors(svgEl);
    attachClickToEdit(svgEl);

    enableDiagramZoom();
  } catch (err) {
    console.error('[mermaid render]', err);
    previewSvgWrap.innerHTML = `
      <div style="color:#f87171;padding:2rem;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;font-family:monospace;">
        <div style="font-size:1.4rem;margin-bottom:.5rem">⚠️</div>
        <div style="opacity:.8;margin-bottom:.75rem">Mermaid parse error — edit the code and click Apply Edit.</div>
        <pre style="background:#1e1e2e;border-radius:6px;padding:1rem;overflow:auto;font-size:.7rem;max-height:160px;white-space:pre-wrap;color:#fca5a5;max-width:100%">
${escHtml(err.message || String(err))}</pre>
      </div>`;
  }

  if (previewMeta) previewMeta.style.display = 'flex';
  if (previewBadge) {
    const entry = DIAGRAM_TYPES.find(d => d.type === diagramType);
    previewBadge.textContent = entry ? entry.label : diagramType;
  }
  if (previewVersion) previewVersion.textContent = `v${versionNumber}`;
}

/* ── Version list ─────────────────────────────────────────────────────────── */
function renderVersions(versions, activeVersionId) {
  if (!versionsListEl) return;
  state.allVersions = (versions || []).map(v => ({ ...v }));
  versionsListEl.innerHTML = '';
  if (!versions?.length) {
    versionsListEl.innerHTML = '<p class="version-empty">No versions yet.</p>';
    return;
  }
  [...versions].reverse().forEach(v => {
    const item = document.createElement('div');
    item.className = `version-item${v.version_id === activeVersionId ? ' active' : ''}`;
    item.dataset.versionId = v.version_id;
    const date = new Date(v.created_at).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
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
  state.currentVersionId    = v.version_id;
  state.currentMermaidCode  = v.mermaid_code;
  if (codeEditor) codeEditor.value = v.mermaid_code;
  renderPreview(v.mermaid_code, state.diagramType || 'flowchart', v.version_number, v.svg_path);
  document.querySelectorAll('.version-item').forEach(el =>
    el.classList.toggle('active', el.dataset.versionId === v.version_id)
  );
  if (diffPanel && diffPanel.style.display !== 'none') renderDiff();
}

/* ── Apply full diagram API response ─────────────────────────────────────── */
function applyDiagramResponse(data) {
  state.currentDiagramId = data.diagram_id;

  // ── VERSIONING FIX: always sync diagram_type from the API ────────────────
  if (data.diagram_type) {
    state.diagramType = data.diagram_type;
    // Sync type chip UI
    document.querySelectorAll('.type-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.type === data.diagram_type);
    });
  }

  if (data.current_version) {
    state.currentVersionId    = data.current_version.version_id;
    state.currentMermaidCode  = data.current_version.mermaid_code;
    if (codeEditor) codeEditor.value = data.current_version.mermaid_code;
    renderPreview(
      data.current_version.mermaid_code,
      data.diagram_type,
      data.current_version.version_number,
      data.current_version.svg_path,
    );
  }

  renderVersions(data.versions, state.currentVersionId);
  if (regenBtn)    regenBtn.disabled    = false;
  if (applyEditBtn) applyEditBtn.disabled = false;
  if (downloadBtn)  downloadBtn.disabled  = false;

  // Live quota refresh
  if (window.refreshQuotas) {
    window.currentProject = data.project_name || state.projectName;
    window.refreshQuotas();
  }
  if (state.projectName) {
    updateDiagramQuota(state.projectName);
  }
}

/* ── Get selected context doc IDs ─────────────────────────────────────────── */
function getSelectedDocIds() {
  const list = document.querySelectorAll('.context-doc-checkbox:checked');
  return Array.from(list).map(el => el.value);
}

/* ── API event handlers ───────────────────────────────────────────────────── */
if (generateBtn) {
  generateBtn.addEventListener('click', async () => {
    const project = projectSelect?.value || '';
    const prompt  = promptInput?.value.trim() || '';
    if (!project) { showToast('Please select a project first.', 'error'); return; }
    if (!prompt)  { showToast('Please enter a description.', 'error'); return; }
    setGenerating(true, 'Generating…');
    try {
      const data = await generateWithRetry({
        project_name:          project,
        prompt,
        diagram_type:          state.diagramType,
        detail_level:          state.detailLevel,
        selected_document_ids: getSelectedDocIds(),
      });
      applyDiagramResponse(data);
      showToast('Diagram generated!');
    } catch (e) {
      showToast(e.message || 'Generation failed.', 'error');
    } finally {
      setGenerating(false);
      if (window.refreshQuotas) window.refreshQuotas();
    }
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
        diagram_type:          state.diagramType,
        detail_level:          state.detailLevel,
        selected_document_ids: getSelectedDocIds(),
      });
      applyDiagramResponse(data);
      showToast('New version generated!');
    } catch (e) {
      showToast(e.message || 'Regeneration failed.', 'error');
    } finally {
      setGenerating(false);
      if (window.refreshQuotas) window.refreshQuotas();
    }
  });
}

if (applyEditBtn) {
  applyEditBtn.addEventListener('click', async () => {
    if (!state.currentDiagramId) { showToast('No diagram loaded.', 'error'); return; }
    const code = codeEditor?.value.trim() || '';
    if (!code) { showToast('Code editor is empty.', 'error'); return; }

    // Client-side validation before sending to server
    const parseErr = await validateMermaid(code);
    if (parseErr) {
      showToast(`Syntax error: ${parseErr.slice(0, 120)}`, 'error');
      return;
    }

    applyEditBtn.disabled = true;
    applyEditBtn.textContent = 'Applying…';
    previewLoading?.classList.add('active');
    try {
      const res = await fetch(`/api/diagrams/${state.currentDiagramId}/edit`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mermaid_code: code }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Edit failed' }));
        throw new Error(err.detail);
      }
      applyDiagramResponse(await res.json());
      showToast('Edit saved as new version!');
    } catch (e) {
      showToast(e.message || 'Could not apply edit.', 'error');
    } finally {
      applyEditBtn.disabled = false;
      applyEditBtn.textContent = '✏️ Apply Edit';
      previewLoading?.classList.remove('active');
      if (window.refreshQuotas) window.refreshQuotas();
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
          const url  = URL.createObjectURL(blob);
          Object.assign(document.createElement('a'), {
            href: url, download: `diagram_v${state.currentVersionId || 'latest'}.svg`,
          }).click();
          URL.revokeObjectURL(url);
          showToast('SVG downloading…'); return;
        }
      } catch (_) { }
    }
    const svgEl = previewSvgWrap?.querySelector('svg');
    if (!svgEl) { showToast('Nothing to download yet.', 'error'); return; }
    const blob = new Blob([new XMLSerializer().serializeToString(svgEl)], { type: 'image/svg+xml' });
    const url  = URL.createObjectURL(blob);
    Object.assign(document.createElement('a'), {
      href: url, download: `diagram_v${state.currentVersionId || 'latest'}.svg`,
    }).click();
    URL.revokeObjectURL(url);
    showToast('SVG downloading…');
  });
}

/* ── Resizer ──────────────────────────────────────────────────────────────── */
const horizontalResizer = $('horizontalResizer');
const codeEditorWrap    = $('codeEditorWrap');

if (horizontalResizer && codeEditorWrap) {
  let isDragging = false, startY = 0, startHeight = 0;
  horizontalResizer.addEventListener('mousedown', (e) => {
    isDragging = true; startY = e.clientY;
    startHeight = codeEditorWrap.getBoundingClientRect().height;
    horizontalResizer.classList.add('dragging');
    document.body.style.cursor = 'row-resize'; e.preventDefault();
  });
  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const newH = Math.max(100, Math.min(startHeight + (e.clientY - startY), window.innerHeight - 200));
    codeEditorWrap.style.height = newH + 'px';
  });
  document.addEventListener('mouseup', () => {
    if (isDragging) { isDragging = false; horizontalResizer.classList.remove('dragging'); document.body.style.cursor = ''; }
  });
}

/* ── Projects ─────────────────────────────────────────────────────────────── */
async function loadProjects() {
  if (!projectSelect) return;
  try {
    const [srsRes, diagRes] = await Promise.allSettled([
      fetch('/api/my-documents'),
      fetch('/api/diagrams/projects'),
    ]);
    const names = new Set();
    if (srsRes.status === 'fulfilled' && srsRes.value.ok)
      (await srsRes.value.json()).forEach(d => names.add(d.project_name));
    if (diagRes.status === 'fulfilled' && diagRes.value.ok)
      (await diagRes.value.json()).forEach(n => names.add(n));
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
    // Check context availability whenever project changes
    state.projectName = projectSelect.value;
    window.currentProject = projectSelect.value;
    await _checkContextAvailability(projectSelect.value);
    await updateDiagramQuota(projectSelect.value);
    if (window.refreshQuotas) window.refreshQuotas();
  });
}

/* ── Utility ──────────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  // Build the type-chip row + detail selector
  _buildTypeChips();
  _buildDetailSelector();

  await loadProjects();

  const params = new URLSearchParams(window.location.search);

  if (params.has('project')) {
    const p = params.get('project');
    const exists = Array.from(projectSelect?.options || []).some(o => o.value === p);
    if (!exists && projectSelect) {
      const opt = new Option(p, p, true, true);
      projectSelect.insertBefore(opt, projectSelect.lastElementChild);
    }
    if (projectSelect) projectSelect.value = p;
    state.projectName = p;
    window.currentProject = p;
    await _checkContextAvailability(p);
    await updateDiagramQuota(p);
    if (window.refreshQuotas) window.refreshQuotas();
  }

  if (params.has('type')) {
    const t = params.get('type');
    state.diagramType = t || 'flowchart';
    document.querySelectorAll('.type-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.type === t);
    });
  }

  if (params.has('detail')) {
    state.detailLevel = params.get('detail');
    const sel = $('detailLevelSelect');
    if (sel) sel.value = state.detailLevel;
  }

  if (params.has('prompt') && promptInput) {
    promptInput.value = params.get('prompt');
  }

  _updatePromptHint(state.diagramType);

  if (regenBtn)     regenBtn.disabled     = true;
  if (applyEditBtn) applyEditBtn.disabled = true;
  if (downloadBtn)  downloadBtn.disabled  = true;
  if (diffPanel)    diffPanel.style.display = 'none';

  // Auto-generate if navigated with project + prompt in URL
  if (params.has('project') && params.has('prompt') && promptInput?.value.trim()) {
    setTimeout(() => {
      if (generateBtn && !generateBtn.disabled) {
        showToast('Auto-generating diagram from project…');
        generateBtn.click();
      }
    }, 500);
  }
});

