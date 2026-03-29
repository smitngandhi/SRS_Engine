// project_buckets.js

document.addEventListener('DOMContentLoaded', () => {
  const elements = {
    list:          document.getElementById('project-list'),
    details:       document.getElementById('project-details'),
    emptyState:    document.getElementById('project-empty-state'),
    title:         document.getElementById('detail-title'),
    summary:       document.getElementById('detail-summary'),
    srsList:       document.getElementById('detail-srs-list'),
    srsEmpty:      document.getElementById('detail-srs-empty'),
    diagramsGrid:  document.getElementById('detail-diagrams-grid'),
    diagramsEmpty: document.getElementById('detail-diagrams-empty'),
    form:          document.getElementById('generate-diagram-form'),
    diagramType:   document.getElementById('diagram-type'),
    diagramPrompt: document.getElementById('diagram-prompt'),
    btnGenerate:   document.getElementById('btn-generate-diagram'),
    statusText:    document.getElementById('generate-diagram-status'),
  };

  let allProjects  = [];
  let allDocuments = [];
  let currentProject = null;

  /* ── Mermaid thumbnail config ─────────────────────────────────────────── */
  function initMermaidForThumbs() {
    if (typeof mermaid === 'undefined') return;
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        background:          'transparent',
        mainBkg:             '#0f1117',
        nodeBorder:          '#00e5cc',
        nodeTextColor:       '#e2e8f0',
        edgeLabelBackground: '#0d1117',
        lineColor:           '#00e5cc',
        fontFamily:          "'Inter','Segoe UI',sans-serif",
        fontSize:            '11px',
      },
      flowchart: { curve: 'basis', useMaxWidth: true, htmlLabels: false },
      sequence:  { useMaxWidth: true },
      er:        { useMaxWidth: true },
    });
  }

  /* Render one mermaid thumbnail into a container element */
  async function renderThumb(container, mermaidCode) {
    if (!mermaidCode || typeof mermaid === 'undefined') return;
    try {
      initMermaidForThumbs();
      const uid     = `thumb-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const { svg } = await mermaid.render(uid, mermaidCode);
      container.innerHTML = svg;

      const svgEl = container.querySelector('svg');
      if (!svgEl) return;

      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      svgEl.style.cssText = 'width:100%!important;height:100%!important;background:transparent!important;display:block;';

      // Strip white fills
      svgEl.querySelectorAll('[fill="white"],[fill="#ffffff"],[fill="#fff"]').forEach(el =>
        el.setAttribute('fill', 'transparent')
      );
      svgEl.querySelectorAll('style').forEach(s => {
        s.textContent = s.textContent
          .replace(/background(-color)?:\s*(white|#fff(fff)?)\s*;?/gi, 'background:transparent;')
          .replace(/fill:\s*(white|#fff(fff)?)\s*;?/gi, 'fill:transparent;');
      });
      const firstRect = svgEl.querySelector('rect:first-child');
      if (firstRect) firstRect.setAttribute('fill', 'transparent');
    } catch (_) {
      // Keep icon fallback already in DOM
    }
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */
  async function init() {
    try {
      const [projRes, docsRes] = await Promise.all([
        fetch('/api/projects'),
        fetch('/api/my-documents'),
      ]);
      if (!projRes.ok || !docsRes.ok) throw new Error('Failed to fetch data');
      allProjects  = await projRes.json();
      allDocuments = await docsRes.json();
      renderProjectList();
    } catch (err) {
      elements.list.innerHTML = `<div class="docs-error">Failed to load projects.</div>`;
    }
  }

  /* ── Project list sidebar ─────────────────────────────────────────────── */
  function renderProjectList() {
    if (!allProjects.length) {
      elements.list.innerHTML = `<div class="muted" style="padding:16px;">No projects found yet.</div>`;
      return;
    }

    elements.list.innerHTML = '';
    const sorted = [...allProjects].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));

    sorted.forEach(proj => {
      const div     = document.createElement('div');
      const isActive = currentProject?.project_name === proj.project_name;
      div.className = `project-item${isActive ? ' active' : ''}`;

      const hasDocs  = allDocuments.some(d => d.project_name === proj.project_name);
      const metaText = proj.summary ? 'Has SRS summary' : (hasDocs ? 'Has documents' : 'Diagrams only');

      div.innerHTML = `
        <div class="project-item-name">${escHtml(proj.project_name || 'Untitled')}</div>
        <div class="project-item-meta">${metaText}</div>`;

      div.addEventListener('click', () => selectProject(proj));
      elements.list.appendChild(div);
    });
  }

  /* ── Select project ───────────────────────────────────────────────────── */
  async function selectProject(proj) {
    currentProject = proj;
    renderProjectList();

    elements.emptyState.style.display = 'none';
    elements.details.style.display    = 'block';
    elements.title.textContent        = proj.project_name || 'Untitled Project';

    // Summary
    if (proj.summary?.problem_statement || proj.summary?.features?.length) {
      let html = '';
      if (proj.summary.problem_statement)
        html += `<div style="margin-bottom:16px;"><strong>Problem:</strong> ${escHtml(proj.summary.problem_statement)}</div>`;
      if (proj.summary.features?.length) {
        html += `<div>${proj.summary.features.map(f =>
          `<span class="summary-feature">${escHtml(f.title || 'Feature')}</span>`
        ).join('')}</div>`;
      }
      elements.summary.innerHTML = html;
    } else {
      elements.summary.innerHTML = '<span class="muted">No summary context found for this project.</span>';
    }

    // SRS documents
    const docs = allDocuments.filter(d => d.project_name === proj.project_name);
    elements.srsList.innerHTML = '';
    elements.srsEmpty.style.display = docs.length ? 'none' : 'block';
    docs.forEach(doc => {
      const dateStr = new Date(doc.created_at * 1000).toLocaleDateString();
      const card    = document.createElement('div');
      card.className = 'doc-card';
      card.innerHTML = `
        <div class="doc-icon">📄</div>
        <div class="doc-info">
          <div class="doc-name">${escHtml(doc.filename)}</div>
          <div class="doc-meta">${dateStr} · ${doc.size_kb} KB</div>
        </div>
        <div class="doc-actions">
          <a class="btn btn-link" href="/api/download-srs/${doc.id}" download>Download</a>
        </div>`;
      elements.srsList.appendChild(card);
    });

    // Diagrams
    loadDiagrams(proj.project_name);
  }

  /* ── Load & render diagrams ───────────────────────────────────────────── */
  const DIAGRAM_TYPE_ICONS = {
    flowchart: '🔀', sequence: '🔁', erd: '🗄️', class: '🏛️', custom: '✨',
  };

  async function loadDiagrams(projectName) {
    elements.diagramsGrid.innerHTML    = '<div class="muted" style="padding:8px;">Loading diagrams…</div>';
    elements.diagramsEmpty.style.display = 'none';

    try {
      const res = await fetch(`/api/diagrams/project/${encodeURIComponent(projectName)}`);
      if (!res.ok) throw new Error('Fetch failed');
      const diagrams = await res.json();

      elements.diagramsGrid.innerHTML = '';

      if (!diagrams.length) {
        elements.diagramsEmpty.style.display = 'block';
        return;
      }

      diagrams.forEach((d, i) => {
        const v    = d.versions[d.versions.length - 1]; // latest version
        const icon = DIAGRAM_TYPE_ICONS[d.diagram_type] || '🗺️';
        const thumbId = `bucket-thumb-${d.diagram_id}`;

        const card = document.createElement('a');
        card.className = 'diagram-card';
        card.href      = `javascript:void(0)`;
        card.onclick   = (e) => {
          e.preventDefault();
          if (v && v.svg_path) openDiagramModal(d.project_name, v.svg_path);
        };
        card.style.textDecoration = 'none';

        card.innerHTML = `
          <div class="diagram-preview-thumb" id="${thumbId}">
            <span class="diagram-thumb-icon">${icon}</span>
          </div>
          <div class="diagram-name">${escHtml(d.project_name)}</div>
          <div class="diagram-meta">
            <span class="diagram-type-badge">${escHtml(d.diagram_type)}</span>
            <span class="diagram-versions-count">${d.versions.length} version${d.versions.length !== 1 ? 's' : ''}</span>
            <span class="doc-date">${relativeTime(v.created_at)}</span>
          </div>`;

        elements.diagramsGrid.appendChild(card);

        // Render mermaid thumbnail with stagger so cards paint first
        if (v?.mermaid_code) {
          const thumbEl = document.getElementById(thumbId);
          if (thumbEl) {
            setTimeout(() => renderThumb(thumbEl, v.mermaid_code), i * 80);
          }
        }
      });

    } catch (e) {
      elements.diagramsGrid.innerHTML = '<div class="docs-error">Error loading diagrams.</div>';
    }
  }

  /* ── Generate diagram form ────────────────────────────────────────────── */
  elements.form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentProject) return;

    const payload = {
      project_name: currentProject.project_name,
      prompt:       elements.diagramPrompt.value.trim(),
      diagram_type: elements.diagramType.value,
    };
    if (!payload.prompt) return;

    elements.btnGenerate.disabled    = true;
    elements.btnGenerate.textContent = 'Navigating…';

    const params = new URLSearchParams({
      project: payload.project_name,
      type: payload.diagram_type,
      prompt: payload.prompt
    });
    
    window.location.href = `/diagrams?${params.toString()}`;
  });

  /* ── Diagram Viewer Modal ─────────────────────────────────────────────── */
  const diagramModal = document.getElementById('diagram-modal');
  const modalTitle   = document.getElementById('modal-diagram-title');
  const modalContent = document.getElementById('modal-diagram-content');
  const modalClose   = document.getElementById('modal-diagram-close');
  const modalDownload= document.getElementById('modal-diagram-download');

  if (modalClose && diagramModal) {
    modalClose.onclick = () => diagramModal.style.display = 'none';
    diagramModal.onclick = (e) => {
      if (e.target === diagramModal) diagramModal.style.display = 'none';
    };
  }

  function openDiagramModal(title, svgPath) {
    if (!diagramModal) return;
    modalTitle.textContent = title + ' Diagram';
    modalContent.innerHTML = `<img src="${svgPath}?t=${Date.now()}" style="max-width:100%; max-height:100%; object-fit:contain; display:block;" alt="Diagram" />`;
    modalDownload.href     = svgPath;
    diagramModal.style.display = 'flex';
  }

  /* ── Helpers ──────────────────────────────────────────────────────────── */
  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g, c =>
      ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[c])
    );
  }

  function relativeTime(isoString) {
    if (!isoString) return 'unknown';
    const date     = new Date(isoString + 'Z');
    const diffDays = Math.round((date - new Date()) / 86400000);
    if (diffDays === 0) return 'today';
    return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(diffDays, 'day');
  }

  init();
});