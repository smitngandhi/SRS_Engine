// project_buckets.js

document.addEventListener('DOMContentLoaded', () => {
  const elements = {
    list: document.getElementById('project-list'),
    details: document.getElementById('project-details'),
    emptyState: document.getElementById('project-empty-state'),
    title: document.getElementById('detail-title'),
    subtitle: document.getElementById('detail-subtitle'),
    summary: document.getElementById('detail-summary'),
    srsList: document.getElementById('detail-srs-list'),
    srsEmpty: document.getElementById('detail-srs-empty'),
    diagramsGrid: document.getElementById('detail-diagrams-grid'),
    diagramsEmpty: document.getElementById('detail-diagrams-empty'),
    historyList: document.getElementById('detail-history-list'),
    historyEmpty: document.getElementById('detail-history-empty'),
    btnOpenStudio: document.getElementById('btn-open-studio'),
    
    // Stats
    statDocs: document.getElementById('stat-docs-count'),
    statDiagrams: document.getElementById('stat-diagrams-count'),
    statVersions: document.getElementById('stat-versions-count'),
    
    // Tabs
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Modals
    restoreModal: document.getElementById('restore-modal'),
    btnCancelRestore: document.getElementById('btn-cancel-restore'),
    btnConfirmRestore: document.getElementById('btn-confirm-restore'),
  };

  let allProjects = [];
  let allDocuments = [];
  let currentProject = null;
  let pendingRestoreVersion = null;

  /* ── Mobile Sidebar Logic ────────────────────────────────────────── */
  const sidebar = document.querySelector('.buckets-sidebar');
  const openBtn = document.getElementById('mobile-sidebar-open');
  const closeBtn = document.getElementById('mobile-sidebar-close');

  if (openBtn) {
    openBtn.onclick = () => sidebar.classList.add('open');
  }
  if (closeBtn) {
    closeBtn.onclick = () => sidebar.classList.remove('open');
  }

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && e.target !== openBtn) {
        sidebar.classList.remove('open');
      }
    }
  });

  // Close on item click
  elements.list.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && e.target.closest('.project-item')) {
      sidebar.classList.remove('open');
    }
  });


  /* ── Tab Logic ───────────────────────────────────────────────────────── */
  elements.tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      elements.tabButtons.forEach(b => b.classList.remove('active'));
      elements.tabContents.forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(target).classList.add('active');
    });
  });

  /* ── Mermaid thumbnail config ─────────────────────────────────────────── */
  function initMermaidForThumbs() {
    if (typeof mermaid === 'undefined') return;
    mermaid.initialize({
      startOnLoad: false,
      theme: 'neutral',
      themeVariables: {
        fontFamily: "'Inter','Segoe UI',sans-serif",
        fontSize: '11px',
      },
      flowchart: { curve: 'basis', useMaxWidth: true, htmlLabels: false },
      sequence: { useMaxWidth: true },
      er: { useMaxWidth: true },
    });
  }

  async function renderThumb(container, mermaidCode) {
    if (!mermaidCode || typeof mermaid === 'undefined') return;
    try {
      initMermaidForThumbs();
      const uid = `thumb-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const { svg } = await mermaid.render(uid, mermaidCode);
      container.innerHTML = svg;

      const svgEl = container.querySelector('svg');
      if (!svgEl) return;

      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      svgEl.style.cssText = 'width:100%!important;height:100%!important;background:transparent!important;display:block;';
    } catch (_) {}
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */
  async function init() {
    try {
      const [projRes, docsRes] = await Promise.all([
        fetch('/api/projects'),
        fetch('/api/my-documents'),
      ]);
      if (!projRes.ok || !docsRes.ok) throw new Error('Failed to fetch data');
      allProjects = await projRes.json();
      allDocuments = await docsRes.json();
      renderProjectList();
    } catch (err) {
      elements.list.innerHTML = `<div class="docs-error">Failed to load projects.</div>`;
    }
  }

  function renderProjectList() {
    if (!allProjects.length) {
      elements.list.innerHTML = `<div class="muted" style="padding:16px;">No projects found yet.</div>`;
      return;
    }

    elements.list.innerHTML = '';
    const sorted = [...allProjects].sort((a, b) => (new Date(b.updated_at || 0)) - (new Date(a.updated_at || 0)));

    sorted.forEach(proj => {
      const div = document.createElement('div');
      const isActive = currentProject?.project_name === proj.project_name;
      div.className = `project-item${isActive ? ' active' : ''}`;

      const hasDocs = allDocuments.some(d => d.project_name === proj.project_name);
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
    window.currentProject = proj.project_name;
    renderProjectList();
    if (window.refreshQuotas) window.refreshQuotas();

    elements.emptyState.style.display = 'none';
    elements.details.style.display = 'block';
    elements.title.textContent = proj.project_name || 'Untitled Project';
    
    // Set Diagram Studio link
    if (elements.btnOpenStudio) {
      elements.btnOpenStudio.href = `/diagrams?project=${encodeURIComponent(proj.project_name)}`;
    }

    // Set Loading state for stats
    elements.statDiagrams.closest('.stat-card').classList.add('is-loading');
    elements.statVersions.closest('.stat-card').classList.add('is-loading');

    // Summary
    if (proj.summary?.problem_statement || proj.summary?.features?.length) {
      let html = '';
      if (proj.summary.problem_statement)
        html += `<div style="margin-bottom:16px;"><strong>Problem Statement:</strong><p style="margin-top:8px; color:var(--text-secondary);">${escHtml(proj.summary.problem_statement)}</p></div>`;
      if (proj.summary.features?.length) {
        html += `<div style="margin-top:20px;"><strong>Key Features:</strong><div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:8px;">${proj.summary.features.map(f =>
          `<span class="summary-feature">${escHtml(f.title || 'Feature')}</span>`
        ).join('')}</div></div>`;
      }
      elements.summary.innerHTML = html;
    } else {
      elements.summary.innerHTML = '<span class="muted">No summary context found for this project.</span>';
    }

    // SRS documents
    const docs = allDocuments.filter(d => d.project_name === proj.project_name);
    elements.srsList.innerHTML = '';
    elements.srsEmpty.style.display = docs.length ? 'none' : 'block';
    elements.statDocs.textContent = docs.length;
    
    docs.forEach(doc => {
      const dateStr = new Date(doc.created_at * 1000).toLocaleDateString();
      const card = document.createElement('div');
      card.className = 'doc-card';
      card.innerHTML = `
        <div class="doc-icon">📄</div>
        <div class="doc-info">
          <div class="doc-name">${escHtml(doc.filename)}</div>
          <div class="doc-meta">${dateStr} · ${doc.size_kb} KB</div>
        </div>
        <div class="doc-actions">
          <a class="btn btn-link" href="/api/download-srs/${doc.id}" download>Download</a>
          <a class="btn btn-primary" href="/document-navigator?doc_id=${doc.project_name}" style="font-size: 0.75rem; padding: 4px 8px;">Chat</a>
        </div>`;
      elements.srsList.appendChild(card);
    });

    // Reset tabs to overview when changing project
    const overviewTab = elements.tabButtons[0];
    if (overviewTab) overviewTab.click();

    // Diagrams
    await loadDiagrams(proj.project_name);
    
    // History
    await loadHistory(proj.project_name);
  }

  /* ── Load & render diagrams ───────────────────────────────────────────── */
  const DIAGRAM_TYPE_ICONS = {
    flowchart: '🔀', sequence: '🔁', erd: '🗄️', class: '🏛️', custom: '✨',
  };

  async function loadDiagrams(projectName) {
    elements.diagramsGrid.innerHTML = '<div class="muted" style="padding:8px;">Loading diagrams…</div>';
    elements.diagramsEmpty.style.display = 'none';

    try {
      const res = await fetch(`/api/diagrams/project/${encodeURIComponent(projectName)}`);
      if (!res.ok) throw new Error('Fetch failed');
      const diagrams = await res.json();

      elements.diagramsGrid.innerHTML = '';
      elements.statDiagrams.textContent = diagrams.length;
      elements.statDiagrams.closest('.stat-card').classList.remove('is-loading');

      if (!diagrams.length) {
        elements.diagramsEmpty.style.display = 'block';
        return;
      }

      diagrams.forEach((d, i) => {
        const v = d.versions[d.versions.length - 1]; // latest version
        const icon = DIAGRAM_TYPE_ICONS[d.diagram_type] || '🗺️';
        const thumbId = `bucket-thumb-${d.diagram_id}`;

        const card = document.createElement('a');
        card.className = 'diagram-card';
        card.href = `javascript:void(0)`;
        card.onclick = (e) => {
          e.preventDefault();
          if (v && v.svg_path) openDiagramModal(d.project_name, v.svg_path);
        };

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
        if (v?.mermaid_code) {
          const thumbEl = document.getElementById(thumbId);
          if (thumbEl) setTimeout(() => renderThumb(thumbEl, v.mermaid_code), i * 80);
        }
      });
    } catch (e) {
      elements.statDiagrams.closest('.stat-card').classList.remove('is-loading');
      elements.diagramsGrid.innerHTML = '<div class="docs-error">Error loading diagrams.</div>';
    }
  }

  /* ── Load & render history ───────────────────────────────────────────── */
  async function loadHistory(projectName) {
    elements.historyList.innerHTML = '<div class="muted" style="padding:8px;">Loading history…</div>';
    elements.historyEmpty.style.display = 'none';

    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectName)}/history`);
      if (!res.ok) throw new Error('Fetch history failed');
      const data = await res.json();
      const versions = (data.versions || []).slice().reverse(); // newest first
      
      elements.historyList.innerHTML = '';
      elements.statVersions.textContent = versions.length;
      elements.statVersions.closest('.stat-card').classList.remove('is-loading');

      if (!versions.length) {
        elements.historyEmpty.style.display = 'block';
        return;
      }

      versions.forEach((v, idx) => {
        const date = v.timestamp ? new Date(v.timestamp).toLocaleString() : 'Recently';
        const isLatest = idx === 0;
        
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
          <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
              <strong style="color:var(--text-primary);">Version ${v.version}</strong>
              ${isLatest ? '<span class="summary-feature" style="margin:0; font-size:0.65rem; padding:2px 6px;">Active</span>' : ''}
            </div>
            <div style="font-size:0.85rem; color:var(--text-secondary);">${escHtml(v.comment || 'Automatic update')}</div>
            <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:4px;">${date}</div>
          </div>
          <div style="display:flex; gap:8px;">
            <a href="/upgrade/generated/${encodeURIComponent(projectName)}/download-version/${v.version}" class="btn btn-link" style="font-size:0.8rem;">Download</a>
            ${!isLatest ? `<button class="btn btn-outline btn-restore" data-version="${v.version}" style="font-size:0.8rem; padding:4px 10px;">Restore</button>` : ''}
          </div>
        `;
        
        const restoreBtn = item.querySelector('.btn-restore');
        if (restoreBtn) {
          restoreBtn.addEventListener('click', () => {
            pendingRestoreVersion = v.version;
            elements.restoreModal.style.display = 'flex';
          });
        }
        
        elements.historyList.appendChild(item);
      });
    } catch (e) {
      elements.statVersions.closest('.stat-card').classList.remove('is-loading');
      elements.historyList.innerHTML = '<div class="docs-error">Error loading history.</div>';
    }
  }

  /* ── Restore Logic ───────────────────────────────────────────────────── */
  elements.btnCancelRestore.onclick = () => {
    elements.restoreModal.style.display = 'none';
    pendingRestoreVersion = null;
  };

  elements.btnConfirmRestore.onclick = async () => {
    if (!currentProject || !pendingRestoreVersion) return;
    
    elements.btnConfirmRestore.disabled = true;
    elements.btnConfirmRestore.textContent = 'Restoring...';
    
    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(currentProject.project_name)}/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: pendingRestoreVersion }),
      });
      
      if (!res.ok) throw new Error('Restore failed');
      
      elements.restoreModal.style.display = 'none';
      alert(`Project successfully restored to version ${pendingRestoreVersion}`);
      await selectProject(currentProject); // Refresh everything
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      elements.btnConfirmRestore.disabled = false;
      elements.btnConfirmRestore.textContent = 'Yes, Restore';
      pendingRestoreVersion = null;
    }
  };


  /* ── Diagram Viewer Modal ─────────────────────────────────────────────── */
  const diagramModal = document.getElementById('diagram-modal');
  const modalTitle = document.getElementById('modal-diagram-title');
  const modalContent = document.getElementById('modal-diagram-content');
  const modalClose = document.getElementById('modal-diagram-close');
  const modalDownload = document.getElementById('modal-diagram-download');

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
    modalDownload.href = svgPath;
    diagramModal.style.display = 'flex';
  }

  /* ── Helpers ──────────────────────────────────────────────────────────── */
  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c])
    );
  }

  function relativeTime(isoString) {
    if (!isoString) return 'unknown';
    const date = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z');
    const diffDays = Math.round((date - new Date()) / 86400000);
    if (diffDays === 0) return 'today';
    return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(diffDays, 'day');
  }

  init();
});