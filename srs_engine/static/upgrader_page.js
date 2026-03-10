/* ═══════════════════════════════════════════════════════
   upgrader_page.js
   SRS Upgrader — upload & parse step
   Depends on: escHtml() from site.js
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── DOM refs ──────────────────────────────────────────
  const dropZone      = document.getElementById('upDropZone');
  const fileInput     = document.getElementById('upFileInput');
  const filePreview   = document.getElementById('upFilePreview');
  const previewIcon   = document.getElementById('upPreviewIcon');
  const previewName   = document.getElementById('upPreviewName');
  const previewMeta   = document.getElementById('upPreviewMeta');
  const removeBtn     = document.getElementById('upRemoveFile');
  const uploadBtn     = document.getElementById('upUploadBtn');
  const uploadBtnLbl  = document.getElementById('upUploadBtnLabel');
  const progress      = document.getElementById('upProgress');
  const progressFill  = document.getElementById('upProgressFill');
  const statusEl      = document.getElementById('upStatus');
  const filesList     = document.getElementById('upFilesList');
  const filesCount    = document.getElementById('upFilesCount');

  if (!dropZone) return; // auth gate shown — nothing to wire

  let selectedFile = null;

  // ════════════════════════════════════════════════════
  // DRAG & DROP
  // ════════════════════════════════════════════════════

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  ['dragleave', 'dragend'].forEach(evt =>
    dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-over'))
  );

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) setFile(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files?.[0]) setFile(fileInput.files[0]);
  });

  // ════════════════════════════════════════════════════
  // FILE SELECTION
  // ════════════════════════════════════════════════════

  function setFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();

    if (!['pdf', 'docx'].includes(ext)) {
      showStatus('Only PDF and DOCX files are accepted.', 'error');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      showStatus('File exceeds the 20 MB size limit.', 'error');
      return;
    }

    selectedFile = file;
    previewIcon.textContent = ext === 'pdf' ? '📕' : '📘';
    previewName.textContent = file.name;
    previewMeta.textContent = `${ext.toUpperCase()} · ${(file.size / 1024).toFixed(1)} KB`;
    filePreview.classList.add('visible');
    uploadBtn.disabled = false;
    clearStatus();
  }

  removeBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    filePreview.classList.remove('visible');
    uploadBtn.disabled = true;
    clearStatus();
  });

  // ════════════════════════════════════════════════════
  // UPLOAD
  // ════════════════════════════════════════════════════

  uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Lock UI
    uploadBtn.disabled = true;
    uploadBtnLbl.textContent = 'Uploading…';
    progress.classList.add('visible');
    animateProgress(75);
    clearStatus();

    try {
      const form = new FormData();
      form.append('file', selectedFile);

      const res = await fetch('/upload/srs', { method: 'POST', body: form });
      progressFill.style.width = '100%';

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error (${res.status})`);
      }

      const data = await res.json();
      showStatus(`✓ "${escHtml(data.file.original_filename)}" uploaded successfully.`, 'success');

      // Reset selection
      selectedFile = null;
      fileInput.value = '';
      filePreview.classList.remove('visible');

      await loadFiles();

    } catch (err) {
      showStatus(`✕ ${err.message}`, 'error');
    } finally {
      uploadBtn.disabled = true; // stays disabled until new file selected
      uploadBtnLbl.textContent = 'Upload SRS Document';
      setTimeout(() => {
        progress.classList.remove('visible');
        progressFill.style.width = '0%';
      }, 900);
    }
  });

  function animateProgress(target) {
    let current = 0;
    const tick = () => {
      if (current < target) {
        current = Math.min(current + Math.random() * 7 + 2, target);
        progressFill.style.width = current + '%';
        requestAnimationFrame(tick);
      }
    };
    requestAnimationFrame(tick);
  }

  // ════════════════════════════════════════════════════
  // STATUS HELPERS
  // ════════════════════════════════════════════════════

  function showStatus(msg, type) {
    statusEl.innerHTML = msg;
    statusEl.className = `up-status visible ${type}`;
  }

  function clearStatus() {
    statusEl.className = 'up-status';
    statusEl.textContent = '';
  }

  // ════════════════════════════════════════════════════
  // LOAD FILES LIST
  // ════════════════════════════════════════════════════

  async function loadFiles() {
    // Show skeleton
    filesList.innerHTML = `
      <div class="up-files-loading">
        <div class="up-file-skeleton"></div>
        <div class="up-file-skeleton"></div>
      </div>`;

    try {
      const res = await fetch('/upload/srs/list');
      if (!res.ok) throw new Error('Failed to fetch');
      const { files } = await res.json();
      renderFiles(files);
    } catch {
      filesList.innerHTML = `
        <div class="up-files-empty">
          <div class="up-files-empty-icon">⚠️</div>
          Failed to load files. <button class="btn btn-link" style="padding:0" onclick="window.location.reload()">Refresh</button>
        </div>`;
    }
  }

  function renderFiles(files) {
    if (filesCount) filesCount.textContent = files.length || '';

    if (!files.length) {
      filesList.innerHTML = `
        <div class="up-files-empty">
          <div class="up-files-empty-icon">📂</div>
          No files uploaded yet. Upload your first SRS above.
        </div>`;
      return;
    }

    filesList.innerHTML = files.map(f => buildFileCard(f)).join('');

    // Wire up parse + delete buttons
    filesList.querySelectorAll('[data-parse]').forEach(btn => {
      btn.addEventListener('click', () => triggerParse(btn.dataset.parse, btn));
    });

    filesList.querySelectorAll('[data-delete]').forEach(btn => {
      btn.addEventListener('click', () => deleteFile(btn.dataset.delete));
    });
  }

  function buildFileCard(f) {
    const date = new Date(f.uploaded_at).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
    const icon = f.file_type === 'pdf' ? '📕' : '📘';

    return `
      <div class="up-file-card" id="card-${f.file_id}">
        <div class="up-file-card-top">
          <div class="up-fc-icon">${icon}</div>
          <div class="up-fc-info">
            <div class="up-fc-name">${escHtml(f.original_filename)}</div>
            <div class="up-fc-meta">
              <span>${f.size_kb} KB</span>
              <span>·</span>
              <span>${date}</span>
            </div>
          </div>
          <span class="up-fc-badge ${f.file_type}">${f.file_type.toUpperCase()}</span>
        </div>
        <div class="up-file-card-actions">
          <button class="up-btn-parse" data-parse="${f.file_id}">
            <span>🔍</span> Parse Document
          </button>
          <button class="up-btn-delete" data-delete="${f.file_id}" title="Delete file">🗑</button>
        </div>
        <div class="up-parse-result" id="parse-result-${f.file_id}"></div>
      </div>`;
  }

  // ════════════════════════════════════════════════════
  // PARSE
  // ════════════════════════════════════════════════════

  async function triggerParse(fileId, btn) {
    const resultPanel = document.getElementById(`parse-result-${fileId}`);
    if (!resultPanel) return;

    // Lock button
    btn.disabled = true;
    btn.classList.add('parsing');
    btn.innerHTML = '<span>⏳</span> Parsing…';

    resultPanel.classList.remove('visible');
    resultPanel.innerHTML = '';

    try {
      const res = await fetch(`/parse/srs/${fileId}`, { method: 'POST' });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Parse failed (${res.status})`);
      }

      // Fetch the preview for display
      const previewRes = await fetch(`/parse/srs/${fileId}/preview`);
      if (!previewRes.ok) throw new Error('Could not load parse preview');
      const preview = await previewRes.json();

      renderParseResult(resultPanel, preview);
      btn.innerHTML = '<span>✓</span> Parsed';
      btn.style.borderColor = 'rgba(0,229,201,0.4)';
      btn.style.color = 'var(--accent)';

    } catch (err) {
      resultPanel.innerHTML = `
        <div class="up-parse-result-title">Parse Error</div>
        <div class="up-parse-warning">✕ ${escHtml(err.message)}</div>`;
      resultPanel.classList.add('visible');
      btn.disabled = false;
      btn.classList.remove('parsing');
      btn.innerHTML = '<span>🔍</span> Retry Parse';
    }
  }

  function renderParseResult(panel, preview) {
    const meta = preview.metadata;

    // Stat boxes
    const stats = [
      { val: preview.section_count,          label: 'Sections' },
      { val: meta.word_count?.toLocaleString() ?? '—', label: 'Words' },
      { val: meta.page_count ?? '—',         label: 'Pages' },
      { val: meta.file_type.toUpperCase(),   label: 'Format' },
    ];

    const statsHtml = stats.map(s => `
      <div class="up-parse-stat">
        <div class="up-parse-stat-val">${escHtml(String(s.val))}</div>
        <div class="up-parse-stat-label">${s.label}</div>
      </div>`).join('');

    // Extractor info
    let extractorText = `Extracted with <code>${escHtml(meta.primary_extractor)}</code>`;
    if (meta.fallback_used && meta.fallback_extractor) {
      extractorText += ` → fallback: <code>${escHtml(meta.fallback_extractor)}</code>`;
    }

    // Special badges
    const badges = [];
    if (meta.ocr_used)      badges.push('<span class="up-badge ocr">OCR</span>');
    if (meta.fallback_used) badges.push('<span class="up-badge fallback">Fallback</span>');
    if (meta.partial_parse) badges.push('<span class="up-badge partial">Partial</span>');

    // Top-level sections list (max 6 shown)
    const shown   = preview.top_level_sections.slice(0, 6);
    const more    = preview.top_level_sections.length - shown.length;
    const secHtml = shown.map((s, i) => `
      <div class="up-parse-section-item">
        <span class="up-parse-section-num">${i + 1}</span>
        ${escHtml(s)}
      </div>`).join('') + (more > 0
        ? `<div class="up-parse-section-item" style="color:var(--muted);font-style:italic">+${more} more sections</div>`
        : '');

    // Warnings
    const warningsHtml = meta.warnings?.length
      ? `<div class="up-parse-warnings">
           ${meta.warnings.map(w => `<div class="up-parse-warning">⚠ ${escHtml(w)}</div>`).join('')}
         </div>`
      : '';

    panel.innerHTML = `
      <div class="up-parse-result-title">Parse Result</div>
      ${badges.length ? `<div class="up-parse-badges">${badges.join('')}</div>` : ''}
      <div class="up-parse-stats">${statsHtml}</div>
      <div class="up-parse-extractor">${extractorText}</div>
      <div class="up-parse-sections">${secHtml}</div>
      ${warningsHtml}
    `;
    panel.classList.add('visible');
  }

  // ════════════════════════════════════════════════════
  // DELETE
  // ════════════════════════════════════════════════════

  async function deleteFile(fileId) {
    if (!confirm('Delete this file? This cannot be undone.')) return;

    try {
      const res = await fetch(`/upload/srs/${fileId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');

      // Animate card out
      const card = document.getElementById(`card-${fileId}`);
      if (card) {
        card.style.transition = 'opacity 0.25s, transform 0.25s';
        card.style.opacity = '0';
        card.style.transform = 'translateX(12px)';
        setTimeout(() => loadFiles(), 280);
      } else {
        await loadFiles();
      }

    } catch (err) {
      showStatus(`✕ Failed to delete: ${err.message}`, 'error');
    }
  }

  // ════════════════════════════════════════════════════
  // INIT
  // ════════════════════════════════════════════════════

  loadFiles();

});