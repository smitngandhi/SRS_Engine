/**
 * generated_upgrader.js — SRS Document Picker page
 *
 * Fetches the list of generated SRS documents and renders clickable cards.
 */

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('doc-grid');
  const emptyState = document.getElementById('empty-state');
  const loadingState = document.getElementById('loading-state');

  loadDocuments();

  async function loadDocuments() {
    try {
      const res = await fetch('/upgrade/generated/list');
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = '/login?next=/srs-generated-upgrader';
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      const docs = data.documents || [];

      loadingState.style.display = 'none';

      if (docs.length === 0) {
        emptyState.style.display = 'block';
        return;
      }

      grid.innerHTML = '';
      docs.forEach(doc => {
        grid.appendChild(createDocCard(doc));
      });

    } catch (err) {
      loadingState.innerHTML = `
        <div class="gu-empty">
          <div class="gu-empty-icon">⚠️</div>
          <h3>Failed to load documents</h3>
          <p>${err.message}</p>
        </div>
      `;
    }
  }

  function createDocCard(doc) {
    const card = document.createElement('div');
    card.className = 'gu-doc-card';

    const modifiedCount = (doc.modified_sections || []).length;
    const versionCount = doc.version_count || 0;
    const generatedAt = doc.generated_at
      ? new Date(doc.generated_at).toLocaleDateString('en-US', {
          year: 'numeric', month: 'short', day: 'numeric'
        })
      : 'Unknown';

    card.innerHTML = `
      <div class="card-inner">
        <div class="card-title">${escapeHtml(doc.project_name || 'Untitled')}</div>
        <div class="card-meta">
          <span>📁 ${escapeHtml(doc.domain || 'technical')}</span>
          <span>📅 ${generatedAt}</span>
          ${doc.organization ? `<span>🏢 ${escapeHtml(doc.organization)}</span>` : ''}
          ${modifiedCount > 0
            ? `<span class="modified-count">✓ ${modifiedCount} modified</span>`
            : ''
          }
          ${versionCount > 0 ? `<span>📜 ${versionCount} versions</span>` : ''}
        </div>
        <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1.1rem;">
          ${(doc.section_keys || []).length > 0
            ? `<span class="gu-badge gu-badge-text">${(doc.section_keys || []).length} sections</span>`
            : ''
          }
          ${doc.has_sections
            ? '<span class="gu-badge gu-badge-pageindex">Ready to upgrade</span>'
            : '<span class="gu-badge gu-badge-rag">Sections not saved</span>'
          }
        </div>
        <div style="display:flex;gap:8px;">
          <button
            class="gu-btn gu-btn-primary"
            style="flex:1;"
            onclick="window.location.href='/srs-section-upgrader?project_id=${encodeURIComponent(doc.id)}'"
          >
            ✨ Upgrade
          </button>
          <button
            class="gu-btn gu-btn-outline"
            style="flex:1;"
            onclick="window.location.href='/srs-history?project_id=${encodeURIComponent(doc.id)}'"
          >
            📜 History
          </button>
        </div>
      </div>
    `;

    return card;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});