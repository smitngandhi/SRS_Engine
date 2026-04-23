/**
 * srs_history.js — Version History page
 *
 * Loads version list for a project, handles restore confirmation modal.
 */

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const projectId = params.get('project_id') || params.get('project');

  const projectNameEl = document.getElementById('projectName');
  const versionList   = document.getElementById('versionList');
  const restoreModal  = document.getElementById('restoreModal');
  const confirmBtn    = document.getElementById('confirmRestoreBtn');

  let pendingVersion = null;

  if (!projectId) {
    window.location.href = '/srs-generated-upgrader';
    return;
  }

  // Display project name in heading
  if (projectNameEl) {
    projectNameEl.textContent = `${decodeURIComponent(projectId)} — Version History`;
  }

  loadHistory();

  // ── Load history ────────────────────────────────────────────

  async function loadHistory() {
    try {
      const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectId)}/history`);
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = '/login';
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      const versions = (data.versions || []).slice().reverse(); // newest first

      if (versions.length === 0) {
        versionList.innerHTML = `
          <div class="empty-state">
            No version history found for this project.
          </div>
        `;
        return;
      }

      versionList.innerHTML = '';
      versions.forEach((v, idx) => {
        versionList.appendChild(createVersionCard(v, idx === 0));
      });

    } catch (err) {
      versionList.innerHTML = `
        <div class="empty-state">
          ⚠️ Failed to load history: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  // ── Build version card ───────────────────────────────────────

  function createVersionCard(v, isLatest) {
    const card = document.createElement('div');
    card.className = 'version-card';

    const date = v.timestamp
      ? new Date(v.timestamp).toLocaleString('en-US', {
          year: 'numeric', month: 'short', day: 'numeric',
          hour: '2-digit', minute: '2-digit',
        })
      : 'Unknown date';

    card.innerHTML = `
      <div class="version-card-left">
        <div style="display:flex;align-items:center;gap:10px;">
          <span class="version-number">v${v.version}</span>
          ${isLatest
            ? '<span class="gu-badge gu-badge-pageindex">Latest</span>'
            : ''
          }
        </div>
        <div class="version-comment">${escapeHtml(v.comment || 'No comment')}</div>
        <div class="version-date">📅 ${date}</div>
      </div>
      <div class="version-card-right">
        ${v.docx_backup
          ? `<a
               href="/upgrade/generated/${encodeURIComponent(projectId)}/download-version/${v.version}"
               class="gu-btn gu-btn-outline"
               style="font-size:.82rem;padding:8px 14px;"
               download
             >
               ⬇ Download
             </a>`
          : ''
        }
        ${!isLatest
          ? `<button
               class="gu-btn gu-btn-primary"
               style="font-size:.82rem;padding:8px 14px;"
               data-version="${v.version}"
               onclick="openRestoreModal(${v.version})"
             >
               ↩ Restore
             </button>`
          : ''
        }
      </div>
    `;

    return card;
  }

  // ── Restore modal ────────────────────────────────────────────

  window.openRestoreModal = function(version) {
    pendingVersion = version;
    if (restoreModal) restoreModal.style.display = 'flex';
  };

  window.closeRestoreModal = function() {
    pendingVersion = null;
    if (restoreModal) restoreModal.style.display = 'none';
  };

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (pendingVersion === null) return;

      confirmBtn.disabled = true;
      confirmBtn.innerHTML = '<span class="gu-spinner"></span> Restoring…';

      try {
        const res = await fetch(`/upgrade/generated/${encodeURIComponent(projectId)}/restore`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ version: pendingVersion }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }

        closeRestoreModal();
        showToast(`Restored to v${pendingVersion} successfully`, 'success');
        await loadHistory(); // refresh list

      } catch (err) {
        showToast(`Restore failed: ${err.message}`, 'error');
      } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Yes, Restore';
      }
    });
  }

  // Close modal on backdrop click
  if (restoreModal) {
    restoreModal.addEventListener('click', e => {
      if (e.target === restoreModal) closeRestoreModal();
    });
  }

  // ── Helpers ──────────────────────────────────────────────────

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showToast(message, type) {
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