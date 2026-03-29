/* ─────────────────────────────────────────────────────────────────────────────
   studio.js — Mermaid rendered inline, dark themed, full size
───────────────────────────────────────────────────────────────────────────── */

/* ── Mermaid init ─────────────────────────────────────────────────────────── */
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    background:                   'transparent',
    mainBkg:                      '#0f1117',
    nodeBorder:                   '#00e5cc',
    clusterBkg:                   '#1a1f2e',
    titleColor:                   '#e2e8f0',
    nodeTextColor:                '#e2e8f0',
    edgeLabelBackground:          '#0d1117',
    labelTextColor:               '#94a3b8',
    tertiaryTextColor:            '#94a3b8',
    lineColor:                    '#00e5cc',
    arrowheadColor:               '#00e5cc',
    actorBkg:                     '#1a1f2e',
    actorBorder:                  '#00e5cc',
    actorTextColor:               '#e2e8f0',
    actorLineColor:               '#334155',
    signalColor:                  '#00e5cc',
    signalTextColor:              '#e2e8f0',
    activationBkgColor:           '#0f172a',
    activationBorderColor:        '#00e5cc',
    labelBoxBkgColor:             '#1a1f2e',
    labelBoxBorderColor:          '#00e5cc',
    loopTextColor:                '#94a3b8',
    noteBkgColor:                 '#1e293b',
    noteBorderColor:              '#00e5cc',
    noteTextColor:                '#e2e8f0',
    attributeBackgroundColorEven: '#0f1117',
    attributeBackgroundColorOdd:  '#1a1f2e',
    classText:                    '#e2e8f0',
    fontFamily:                   "'Inter', 'Segoe UI', sans-serif",
    fontSize:                     '14px',
  },
  flowchart: { curve: 'basis', useMaxWidth: false, htmlLabels: true },
  sequence:  { useMaxWidth: false },
  er:        { useMaxWidth: false },
});

/* ── State ────────────────────────────────────────────────────────────────── */
const state = {
  currentDiagramId:   null,
  currentVersionId:   null,
  currentSvgPath:     null,
  currentMermaidCode: null,
  diagramType:        'flowchart',
};

/* ── DOM refs ─────────────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const projectSelect  = $('projectSelect');
const promptInput    = $('promptInput');
const generateBtn    = $('generateBtn');
const regenBtn       = $('regenBtn');
const previewSvgWrap = $('previewSvgWrap');
const previewEmpty   = $('previewEmpty');
const previewLoading = $('previewLoading');
const previewMeta    = $('previewMeta');
const codeEditor     = $('codeEditor');
const applyEditBtn   = $('applyEditBtn');
const downloadBtn    = $('downloadBtn');
const versionsListEl = $('versionsList');
const previewBadge   = $('previewBadge');
const previewVersion = $('previewVersion');

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
    sequence:  'e.g. "API authentication handshake between client and server"',
    erd:       'e.g. "E-commerce database with users, orders, and products"',
    class:     'e.g. "Animal class hierarchy with Dog and Cat subclasses"',
    custom:    'e.g. "State machine for a traffic light system"',
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
function setGenerating(loading) {
  if (loading) {
    generateBtn.classList.add('loading');
    generateBtn.disabled = true;
    previewLoading.classList.add('active');
  } else {
    generateBtn.classList.remove('loading');
    generateBtn.disabled = false;
    previewLoading.classList.remove('active');
  }
}

/* ── Strip white backgrounds Mermaid injects into the SVG ────────────────── */
function patchSvgColors(svgEl) {
  if (!svgEl) return;

  const WHITE = new Set(['white', '#ffffff', '#fff', 'rgb(255,255,255)', 'rgb(255, 255, 255)']);

  /* 1. Root SVG background */
  svgEl.style.background = 'transparent';
  if (WHITE.has((svgEl.getAttribute('style') || '').match(/background[^;]*/)?.[0]?.split(':')[1]?.trim() || ''))
    svgEl.style.background = 'transparent';

  /* 2. Walk every element and fix fill / background */
  svgEl.querySelectorAll('*').forEach(el => {
    const fill = el.getAttribute('fill');
    if (fill && WHITE.has(fill.toLowerCase().replace(/\s/g, ''))) {
      el.setAttribute('fill', 'transparent');
    }
    if (el.style.fill && WHITE.has(el.style.fill.toLowerCase().replace(/\s/g, ''))) {
      el.style.fill = 'transparent';
    }
    if (el.style.background && WHITE.has(el.style.background.toLowerCase().replace(/\s/g, ''))) {
      el.style.background = 'transparent';
    }
    if (el.style.backgroundColor && WHITE.has(el.style.backgroundColor.toLowerCase().replace(/\s/g, ''))) {
      el.style.backgroundColor = 'transparent';
    }
  });

  /* 3. Patch inline <style> blocks inside the SVG */
  svgEl.querySelectorAll('style').forEach(styleEl => {
    styleEl.textContent = styleEl.textContent
      .replace(/background(-color)?:\s*(white|#fff(fff)?)\s*;?/gi, 'background:transparent;')
      .replace(/fill:\s*(white|#fff(fff)?)\s*;?/gi, 'fill:transparent;');
  });

  /* 4. Size — fill the container */
  svgEl.removeAttribute('width');
  svgEl.removeAttribute('height');
  svgEl.style.cssText += `
    width:100% !important;
    height:100% !important;
    max-width:100% !important;
    display:block;
    background:transparent !important;
  `;
  svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');
}

/* ── CORE: render mermaid code in the browser ────────────────────────────── */
async function renderPreview(mermaidCode, diagramType, versionNumber, svgPath) {
  if (!mermaidCode) return;

  state.currentSvgPath     = svgPath;
  state.currentMermaidCode = mermaidCode;

  previewEmpty.style.display   = 'none';
  previewSvgWrap.style.display = 'block';
  previewSvgWrap.innerHTML     = `
    <div style="display:flex;align-items:center;justify-content:center;
                height:100%;opacity:.35;font-size:.85rem;color:#94a3b8;">
      Rendering…
    </div>`;

  try {
    const uid      = `mmd-${Date.now()}`;
    const { svg }  = await mermaid.render(uid, mermaidCode);

    previewSvgWrap.innerHTML = svg;
    patchSvgColors(previewSvgWrap.querySelector('svg'));

  } catch (err) {
    console.error('[mermaid]', err);
    previewSvgWrap.innerHTML = `
      <div style="color:#f87171;padding:2rem;text-align:center;
                  display:flex;flex-direction:column;align-items:center;
                  justify-content:center;height:100%;font-family:monospace;">
        <div style="font-size:1.4rem;margin-bottom:.5rem">⚠️</div>
        <div style="opacity:.8;margin-bottom:.75rem">Mermaid parse error — edit the code and click Apply Edit.</div>
        <pre style="background:#1e1e2e;border-radius:6px;padding:1rem;
                    overflow:auto;font-size:.7rem;max-height:160px;
                    white-space:pre-wrap;color:#fca5a5;max-width:100%">
${escHtml(err.message || String(err))}</pre>
      </div>`;
  }

  if (previewMeta)    previewMeta.style.display  = 'flex';
  if (previewBadge)   previewBadge.textContent   = diagramType;
  if (previewVersion) previewVersion.textContent = `v${versionNumber}`;
}

/* ── Version list ─────────────────────────────────────────────────────────── */
function renderVersions(versions, activeVersionId) {
  if (!versionsListEl) return;
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
      day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit',
    });
    item.innerHTML = `
      <div class="version-badge">v${v.version_number}</div>
      <div class="version-info">
        <div class="version-prompt">${escHtml(v.prompt)}</div>
        <div class="version-date">${date}</div>
      </div>`;
    item.addEventListener('click', () => loadVersion(v));
    versionsListEl.appendChild(item);
  });
}

function loadVersion(v) {
  state.currentVersionId = v.version_id;
  if (codeEditor) codeEditor.value = v.mermaid_code;
  renderPreview(v.mermaid_code, state.diagramType || 'flowchart', v.version_number, v.svg_path);
  document.querySelectorAll('.version-item').forEach(el =>
    el.classList.toggle('active', el.dataset.versionId === v.version_id)
  );
}

function applyDiagramResponse(data) {
  state.currentDiagramId = data.diagram_id;
  if (data.current_version) {
    state.currentVersionId = data.current_version.version_id;
    if (codeEditor) codeEditor.value = data.current_version.mermaid_code;
    renderPreview(data.current_version.mermaid_code, data.diagram_type,
                  data.current_version.version_number, data.current_version.svg_path);
  }
  renderVersions(data.versions, state.currentVersionId);
  if (regenBtn)     regenBtn.disabled     = false;
  if (applyEditBtn) applyEditBtn.disabled = false;
  if (downloadBtn)  downloadBtn.disabled  = false;
}

/* ── API calls ────────────────────────────────────────────────────────────── */
if (generateBtn) {
  generateBtn.addEventListener('click', async () => {
    const project = projectSelect?.value || '';
    const prompt  = promptInput?.value.trim() || '';
    if (!project) { showToast('Please select a project first.', 'error'); return; }
    if (!prompt)  { showToast('Please enter a description.', 'error'); return; }
    setGenerating(true);
    try {
      const res = await fetch('/api/diagrams/generate', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({project_name:project, prompt, diagram_type:state.diagramType}),
      });
      if (!res.ok) throw new Error((await res.json().catch(()=>({detail:'Unknown error'}))).detail);
      applyDiagramResponse(await res.json());
      showToast('Diagram generated!');
    } catch(e) { showToast(e.message||'Generation failed.','error'); }
    finally    { setGenerating(false); }
  });
}

if (regenBtn) {
  regenBtn.addEventListener('click', async () => {
    if (!state.currentDiagramId) { showToast('No diagram loaded.','error'); return; }
    const prompt = promptInput?.value.trim()||'';
    if (!prompt) { showToast('Please enter a description.','error'); return; }
    setGenerating(true);
    try {
      const res = await fetch(`/api/diagrams/${state.currentDiagramId}/regenerate`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({prompt, diagram_type:state.diagramType}),
      });
      if (!res.ok) throw new Error((await res.json().catch(()=>({detail:'Regeneration failed'}))).detail);
      applyDiagramResponse(await res.json());
      showToast('New version generated!');
    } catch(e) { showToast(e.message||'Regeneration failed.','error'); }
    finally    { setGenerating(false); }
  });
}

if (applyEditBtn) {
  applyEditBtn.addEventListener('click', async () => {
    if (!state.currentDiagramId) { showToast('No diagram loaded.','error'); return; }
    const code = codeEditor?.value.trim()||'';
    if (!code) { showToast('Code editor is empty.','error'); return; }
    applyEditBtn.disabled = true; applyEditBtn.textContent = 'Applying…';
    previewLoading.classList.add('active');
    try {
      const res = await fetch(`/api/diagrams/${state.currentDiagramId}/edit`, {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({mermaid_code:code}),
      });
      if (!res.ok) throw new Error((await res.json().catch(()=>({detail:'Edit failed'}))).detail);
      applyDiagramResponse(await res.json());
      showToast('Edit saved as new version!');
    } catch(e) { showToast(e.message||'Could not apply edit.','error'); }
    finally {
      applyEditBtn.disabled = false; applyEditBtn.textContent = '✏️ Apply Edit';
      previewLoading.classList.remove('active');
    }
  });
}

if (downloadBtn) {
  downloadBtn.addEventListener('click', async () => {
    // Strategy 1: server SVG file
    if (state.currentSvgPath) {
      try {
        const res = await fetch(state.currentSvgPath);
        if (res.ok) {
          const blob = await res.blob();
          const url  = URL.createObjectURL(blob);
          Object.assign(document.createElement('a'), {href:url, download:`diagram_v${state.currentVersionId||'latest'}.svg`}).click();
          URL.revokeObjectURL(url);
          showToast('SVG downloading…'); return;
        }
      } catch(_) {}
    }
    // Strategy 2: serialize browser SVG
    const svgEl = previewSvgWrap?.querySelector('svg');
    if (!svgEl) { showToast('Nothing to download yet.','error'); return; }
    const blob = new Blob([new XMLSerializer().serializeToString(svgEl)], {type:'image/svg+xml'});
    const url  = URL.createObjectURL(blob);
    Object.assign(document.createElement('a'), {href:url, download:`diagram_v${state.currentVersionId||'latest'}.svg`}).click();
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
    if (srsRes.status==='fulfilled'&&srsRes.value.ok)  (await srsRes.value.json()).forEach(d=>names.add(d.project_name));
    if (diagRes.status==='fulfilled'&&diagRes.value.ok) (await diagRes.value.json()).forEach(n=>names.add(n));
    projectSelect.innerHTML = '<option value="">— Select project —</option>';
    [...names].sort().forEach(n => {
      const o = document.createElement('option'); o.value=n; o.textContent=n;
      projectSelect.appendChild(o);
    });
    const c = document.createElement('option'); c.value='__custom__'; c.textContent='+ New project name…';
    projectSelect.appendChild(c);
  } catch(e) { console.warn('Could not load projects', e); }
}

if (projectSelect) {
  projectSelect.addEventListener('change', () => {
    if (projectSelect.value==='__custom__') {
      const name = prompt('Enter a new project name:')?.trim();
      if (name) {
        const opt = new Option(name, name, true, true);
        projectSelect.insertBefore(opt, projectSelect.lastElementChild);
        projectSelect.value = name;
      } else { projectSelect.value=''; }
    }
  });
}

/* ── Utility ──────────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  await loadProjects();
  
  const params = new URLSearchParams(window.location.search);
  
  if (params.has('project')) {
    const p = params.get('project');
    let exists = Array.from(projectSelect.options).some(o => o.value === p);
    if (!exists && projectSelect) {
      const opt = new Option(p, p, true, true);
      projectSelect.insertBefore(opt, projectSelect.lastElementChild);
    }
    if (projectSelect) projectSelect.value = p;
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
  if (regenBtn)     regenBtn.disabled     = true;
  if (applyEditBtn) applyEditBtn.disabled = true;
  if (downloadBtn)  downloadBtn.disabled  = true;
});