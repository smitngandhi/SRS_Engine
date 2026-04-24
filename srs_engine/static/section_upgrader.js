/**
 * section_upgrader.js — Section Upgrader page
 *
 * Handles: sidebar navigation, section loading (pageIndex + RAG),
 * preview/diff display, confirm/discard, mermaid rendering, and rebuild.
 */

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const projectName = params.get('project_id') || params.get('project');

  if (!projectName) {
    window.location.href = '/srs-generated-upgrader';
    return;
  }

  // DOM refs
  const sidebarList     = document.getElementById('sidebar-list');
  const topbarTitle     = document.getElementById('topbar-title');
  const topbarBadges    = document.getElementById('topbar-badges');
  const contentArea     = document.getElementById('content-area');
  const instructionText = document.getElementById('instruction-text');
  const previewBtn      = document.getElementById('preview-btn');
  const overlay         = document.getElementById('preview-overlay');
  const overlayBody     = document.getElementById('overlay-body');
  const confirmBtn      = document.getElementById('confirm-btn');
  const discardBtn      = document.getElementById('discard-btn');
  const closeOverlayBtn = document.getElementById('close-overlay-btn');
  const rebuildBtn      = document.getElementById('rebuild-btn');
  const projectTitle    = document.getElementById('project-title');

  // State
  let currentSection = null;
  let currentPageIndex = null;
  let previewData = null;
  let sectionMap = {};     // pageIndex → section info
  let modifiedSections = new Set();

  // Section definitions for technical domain
  const SECTIONS = [
    { page_index: 10, key: 'introduction_section',        label: 'Introduction',          type: 'text' },
    { page_index: 20, key: 'overall_description_section',  label: 'Overall Description',   type: 'text' },
    { page_index: 30, key: 'system_features_section',      label: 'System Features',       type: 'text' },
    { page_index: 40, key: 'external_interfaces_section',  label: 'External Interfaces',   type: 'diagram' },
    { page_index: 50, key: 'nfr_section',                  label: 'Non-Functional Req.',   type: 'text' },
    { page_index: 60, key: 'glossary_section',             label: 'Glossary',              type: 'text' },
    { page_index: 70, key: 'assumptions_section',          label: 'Assumptions',           type: 'text' },
  ];

  if (projectTitle) {
    projectTitle.textContent = projectName;
  }

  init();

  // ── Initialization ──────────────────────────────────────────

  /**
   * BUG FIX: The original init() only built the sidebar and loaded the first
   * section. modifiedSections was always an empty Set on page load, which meant
   * the Rebuild button was always blocked by the "No sections have been modified
   * yet" guard after a page refresh — even when the server had confirmed
   * modifications stored in meta.json. We now fetch the list of already-modified
   * sections from the server before loading any section content.
   */
  async function init() {
    window.currentProject = projectName;
    await fetchModifiedSections();
    buildSidebar();
    await updateUpgraderQuota();
    if (window.refreshQuotas) window.refreshQuotas();
    await loadSection(SECTIONS[0].page_index);
  }

  async function updateUpgraderQuota() {
    try {
      const q = window.refreshQuotas ? await window.refreshQuotas() : null;
      if (!q) return;

      const isAdmin = q.is_admin || false;
      const limit = q.upgrade_limit || 5;
      const projData = q.projects?.[projectName] || {};
      const used = projData.upgrade_count || 0;
      const remaining = limit - used;
      const el = document.getElementById('upgrader-quota');
      if (!el) return;
      el.style.display = 'block';

      if (isAdmin) {
        el.innerHTML = `✨ Administrative access: Unlimited upgrades available for "${projectName}"`;
        el.style.background = 'rgba(0,229,201,0.05)';
        el.style.borderColor = 'rgba(0,229,201,0.2)';
        document.getElementById('preview-btn')?.removeAttribute('disabled');
        return;
      }

      if (remaining <= 0) {
        el.innerHTML = `🔒 You have used all ${limit} section upgrades for this project.`;
        el.style.background = 'rgba(244,67,54,0.1)';
        el.style.borderColor = 'rgba(244,67,54,0.3)';
        document.getElementById('preview-btn')?.setAttribute('disabled', 'true');
      } else {
        el.innerHTML = `✨ ${remaining} of ${limit} section upgrades remaining for "${projectName}"`;
        el.style.background = 'rgba(255,255,255,0.03)';
        el.style.borderColor = 'var(--border)';
        document.getElementById('preview-btn')?.removeAttribute('disabled');
      }
    } catch(e) {}
  }

  async function fetchModifiedSections() {
    try {
      // Re-use the existing /list endpoint to grab meta for this project.
      const res = await fetch('/upgrade/generated/list');
      if (!res.ok) return;
      const data = await res.json();
      const docs = data.documents || [];
      const doc = docs.find(d => d.id === projectName || d.project_name === projectName);
      if (doc && Array.isArray(doc.modified_sections)) {
        doc.modified_sections.forEach(key => modifiedSections.add(key));
      }
    } catch (err) {
      // Non-fatal — worst case the rebuild guard is overly strict until the
      // user confirms a change in the current session.
      console.warn('[section_upgrader] Could not fetch modified sections:', err);
    }
  }

  function buildSidebar() {
    sidebarList.innerHTML = '';
    SECTIONS.forEach(sec => {
      sectionMap[sec.page_index] = sec;
      const pill = document.createElement('div');
      pill.className = 'gu-section-pill';
      pill.dataset.pageIndex = sec.page_index;
      pill.innerHTML = `
        <span class="pill-name">${sec.label}</span>
        <span class="gu-badge gu-badge-${sec.type === 'diagram' ? 'diagram' : 'text'}">${sec.type}</span>
        ${modifiedSections.has(sec.key) ? '<span class="pill-modified"></span>' : ''}
      `;
      pill.addEventListener('click', () => loadSection(sec.page_index));
      sidebarList.appendChild(pill);
    });
  }

  // ── Load Section ────────────────────────────────────────────

  async function loadSection(pageIndex) {
    currentPageIndex = pageIndex;
    const sec = sectionMap[pageIndex];

    // Update sidebar active state
    document.querySelectorAll('.gu-section-pill').forEach(p => {
      p.classList.toggle('active', parseInt(p.dataset.pageIndex) === pageIndex);
    });

    // Show loading
    contentArea.innerHTML = `
      <div class="gu-loading-overlay">
        <div class="gu-spinner gu-spinner-lg"></div>
        <div class="loading-text">Loading ${sec.label}…</div>
      </div>
    `;

    // Update topbar
    topbarTitle.textContent = sec.label;
    topbarBadges.innerHTML = `
      <span class="gu-badge gu-badge-${sec.type === 'diagram' ? 'diagram' : 'text'}">${sec.type}</span>
    `;

    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectName)}/section/${pageIndex}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      currentSection = data;

      // Update topbar with lookup method badge
      topbarBadges.innerHTML += `
        <span class="gu-badge gu-badge-${data.lookup_method === 'pageindex' ? 'pageindex' : 'rag'}">
          ${data.lookup_method === 'pageindex' ? 'PageIndex ✓' : 'RAG Fallback'}
        </span>
      `;

      if (modifiedSections.has(data.section_key)) {
        topbarBadges.innerHTML += '<span class="gu-badge gu-badge-modified">✓ Modified</span>';
      }

      renderSectionContent(data.section_data, data.section_type);

    } catch (err) {
      contentArea.innerHTML = `
        <div class="gu-empty">
          <div class="gu-empty-icon">⚠️</div>
          <h3>Failed to load section</h3>
          <p>${err.message}</p>
        </div>
      `;
    }
  }

  // ── Render Section Content ──────────────────────────────────

  function renderSectionContent(data, sectionType) {
    if (!data || typeof data !== 'object') {
      contentArea.innerHTML = '<div class="gu-empty"><h3>No section data available</h3></div>';
      return;
    }

    if (sectionType === 'diagram') {
      contentArea.innerHTML = renderDiagramSection(data);
      renderMermaidDiagrams();
    } else {
      contentArea.innerHTML = renderTextSection(data);
    }
  }

  function renderTextSection(data, highlights) {
    highlights = highlights || [];
    let html = '';
    for (const [key, value] of Object.entries(data)) {
      if (key === 'title') continue;
      html += renderField(key, value, '', highlights);
    }
    return html;
  }

  function renderField(key, value, parentPath, highlights) {
    const fullPath = parentPath ? `${parentPath}.${key}` : key;
    const isChanged = highlights.includes(fullPath);
    const changedClass = isChanged ? ' gu-diff-changed' : '';

    if (value === null || value === undefined) return '';

    if (Array.isArray(value)) {
      let items = '';
      value.forEach((item, i) => {
        if (typeof item === 'object') {
          items += `<div class="gu-field-group${changedClass}" style="margin-left:1rem;">`;
          for (const [k, v] of Object.entries(item)) {
            items += renderField(k, v, `${fullPath}[${i}]`, highlights);
          }
          items += '</div>';
        } else {
          items += `<li class="${changedClass}">${escapeHtml(String(item))}</li>`;
        }
      });

      if (value.length > 0 && typeof value[0] !== 'object') {
        return `
          <div class="gu-field${changedClass}">
            <div class="gu-field-label">${formatLabel(key)}</div>
            <div class="gu-field-value"><ul>${items}</ul></div>
          </div>
        `;
      }
      return `
        <div class="gu-field-group">
          <h3>${formatLabel(key)}</h3>
          ${items}
        </div>
      `;
    }

    if (typeof value === 'object') {
      let inner = '';
      for (const [k, v] of Object.entries(value)) {
        inner += renderField(k, v, fullPath, highlights);
      }
      return `
        <div class="gu-field-group${changedClass}">
          <h3>${formatLabel(key)}</h3>
          ${inner}
        </div>
      `;
    }

    return `
      <div class="gu-field${changedClass}">
        <div class="gu-field-label">${formatLabel(key)}</div>
        <div class="gu-field-value">${escapeHtml(String(value))}</div>
      </div>
    `;
  }

  function renderDiagramSection(data) {
    const interfaces = ['user_interfaces', 'hardware_interfaces', 'software_interfaces', 'communication_interfaces'];
    let html = '';

    for (const iface of interfaces) {
      if (!data[iface]) continue;
      const ifaceData = data[iface];
      const code = ifaceData.interface_diagram?.code || '';

      html += `
        <div class="gu-field-group">
          <h3>${formatLabel(iface)}</h3>
          <div class="gu-field">
            <div class="gu-field-label">Description</div>
            <div class="gu-field-value">${escapeHtml(ifaceData.description || '')}</div>
          </div>
          <div class="gu-diagram-label">Diagram</div>
          <div class="gu-diagram-container">
            <div class="mermaid">${escapeHtml(code)}</div>
          </div>
        </div>
      `;
    }

    // Also render the title if present
    if (data.title) {
      html = `<div class="gu-field"><div class="gu-field-label">Title</div><div class="gu-field-value">${escapeHtml(data.title)}</div></div>` + html;
    }

    return html;
  }

  function renderMermaidDiagrams() {
    if (typeof mermaid !== 'undefined') {
      mermaid.init(undefined, document.querySelectorAll('.mermaid'));
    }
  }


  // ── Preview Upgrade ─────────────────────────────────────────

  previewBtn.addEventListener('click', async () => {
    const instruction = instructionText.value.trim();
    if (!instruction) {
      showToast('Please enter an upgrade instruction', 'error');
      return;
    }
    if (!currentPageIndex) {
      showToast('Please select a section first', 'error');
      return;
    }

    previewBtn.disabled = true;
    previewBtn.innerHTML = '<span class="gu-spinner"></span> Generating preview…';

    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectName)}/section/${currentPageIndex}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instruction: instruction,
          lookup_method: currentSection?.lookup_method || 'pageindex',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      previewData = await res.json();
      showPreviewOverlay(previewData);

    } catch (err) {
      showToast(`Preview failed: ${err.message}`, 'error');
    } finally {
      previewBtn.disabled = false;
      previewBtn.innerHTML = '✨ Preview Upgrade';
    }
  });


  // ── Preview Overlay ─────────────────────────────────────────

  function showPreviewOverlay(data) {
    const sectionType = data.section_type || 'text';

    // Build changes summary
    let summaryHtml = '';
    if (data.changes_summary) {
      summaryHtml = `
        <div class="gu-changes-summary">
          <strong>Changes:</strong> ${escapeHtml(data.changes_summary)}
          ${data.fields_modified && data.fields_modified.length > 0 ? `
            <div class="gu-fields-list">
              ${data.fields_modified.map(f => `<span>${escapeHtml(f)}</span>`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    // Build diff view
    let diffHtml;
    if (sectionType === 'diagram') {
      diffHtml = buildDiagramDiff(data.original_json, data.upgraded_json);
    } else {
      diffHtml = buildTextDiff(data.original_json, data.upgraded_json, data.fields_modified || []);
    }

    overlayBody.innerHTML = summaryHtml + diffHtml;
    overlay.classList.add('visible');

    // Re-render mermaid in overlay
    if (sectionType === 'diagram' && typeof mermaid !== 'undefined') {
      setTimeout(() => {
        mermaid.init(undefined, overlay.querySelectorAll('.mermaid'));
      }, 100);
    }
  }

  function buildTextDiff(original, upgraded, modifiedFields) {
    return `
      <div class="gu-diff-grid">
        <div class="gu-diff-panel">
          <div class="gu-diff-panel-header original">Original</div>
          <div class="gu-diff-panel-body">${renderTextSection(original)}</div>
        </div>
        <div class="gu-diff-panel">
          <div class="gu-diff-panel-header upgraded">Upgraded</div>
          <div class="gu-diff-panel-body">${renderTextSection(upgraded, modifiedFields)}</div>
        </div>
      </div>
    `;
  }

  function buildDiagramDiff(original, upgraded) {
    const interfaces = ['user_interfaces', 'hardware_interfaces', 'software_interfaces', 'communication_interfaces'];
    let html = '<div class="gu-diff-grid">';

    for (const iface of interfaces) {
      if (!original[iface] && !upgraded[iface]) continue;

      const origCode = original[iface]?.interface_diagram?.code || '';
      const upCode = upgraded[iface]?.interface_diagram?.code || '';
      const isModified = origCode !== upCode;

      html += `
        <div class="gu-diff-panel" style="grid-column: 1 / -1;">
          <div class="gu-diff-panel-header ${isModified ? 'upgraded' : 'original'}">
            ${formatLabel(iface)} ${isModified ? '<span class="gu-badge gu-badge-modified">Modified</span>' : ''}
          </div>
          <div class="gu-diff-panel-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
              <div>
                <div class="gu-diagram-label">Original</div>
                <div class="gu-diagram-container"><div class="mermaid">${escapeHtml(origCode)}</div></div>
              </div>
              <div>
                <div class="gu-diagram-label">Upgraded</div>
                <div class="gu-diagram-container"><div class="mermaid">${escapeHtml(upCode)}</div></div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    html += '</div>';
    return html;
  }


  // ── Confirm / Discard ───────────────────────────────────────

  confirmBtn.addEventListener('click', async () => {
    if (!previewData || !previewData.upgraded_json) return;

    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="gu-spinner"></span> Saving…';

    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectName)}/section/${currentPageIndex}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upgraded_json: previewData.upgraded_json }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      // Track modified section
      if (previewData.section_key) {
        modifiedSections.add(previewData.section_key);
      }

      closeOverlay();
      showToast('Section upgraded successfully!', 'success');

      // Refresh sidebar and section
      buildSidebar();
      await loadSection(currentPageIndex);
      instructionText.value = '';

      // Live quota refresh
      if (window.refreshQuotas) window.refreshQuotas();

    } catch (err) {
      showToast(`Confirm failed: ${err.message}`, 'error');
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = '✅ Confirm';
    }
  });

  discardBtn.addEventListener('click', () => {
    closeOverlay();
    showToast('Changes discarded', 'error');
  });

  closeOverlayBtn.addEventListener('click', closeOverlay);

  function closeOverlay() {
    overlay.classList.remove('visible');
    previewData = null;
  }


  // ── Rebuild Document ────────────────────────────────────────

  rebuildBtn.addEventListener('click', async () => {
    if (modifiedSections.size === 0) {
      showToast('No sections have been modified yet', 'error');
      return;
    }

    const comment = prompt("Enter a comment for this new version (e.g. 'Added database features')", "Minor upgrades");
    if (comment === null) return; // User cancelled

    rebuildBtn.disabled = true;
    rebuildBtn.innerHTML = '<span class="gu-spinner"></span> Rebuilding…';

    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectName)}/rebuild`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: comment })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      showToast('Document rebuilt and versioned successfully!', 'success');

      if (confirm('Document rebuilt! Would you like to view version history?')) {
        window.location.href = `/srs-history?project=${encodeURIComponent(projectName)}`;
      }

    } catch (err) {
      showToast(`Rebuild failed: ${err.message}`, 'error');
    } finally {
      rebuildBtn.disabled = false;
      rebuildBtn.innerHTML = '📄 Rebuild Document';
    }
  });


  // ── Helpers ─────────────────────────────────────────────────

  function formatLabel(key) {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showToast(message, type) {
    // Remove existing toast
    const existing = document.querySelector('.gu-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `gu-toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
});