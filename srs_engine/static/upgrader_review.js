/* ═══════════════════════════════════════════════════════
   upgrader_review.js
   SRS Upgrader — analysis, Q&A, and review step
   Depends on: escHtml() from site.js
               window.UPGRADE_FILE_ID set by template
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  const FILE_ID  = window.UPGRADE_FILE_ID  || '';
  const FILENAME = window.UPGRADE_FILENAME || 'Unknown file';

  // ── DOM refs ──────────────────────────────────────────
  const analysePanel   = document.getElementById('rvAnalysePanel');
  const analyseBtn     = document.getElementById('rvAnalyseBtn');
  const analyseBtnLbl  = document.getElementById('rvAnalyseBtnLabel');
  const rvProgress     = document.getElementById('rvProgress');
  const rvProgressFill = document.getElementById('rvProgressFill');
  const rvStatus       = document.getElementById('rvStatus');
  const rvFilename     = document.getElementById('rvFilename');
  const summaryBar     = document.getElementById('rvSummaryBar');
  const sectionsEl     = document.getElementById('rvSections');

  // Q&A modal
  const qaBackdrop = document.getElementById('rvQaBackdrop');
  const qaTitle    = document.getElementById('rvQaTitle');
  const qaBody     = document.getElementById('rvQaBody');
  const qaClose    = document.getElementById('rvQaClose');
  const qaCancel   = document.getElementById('rvQaCancel');
  const qaSubmit   = document.getElementById('rvQaSubmit');

  // State
  let sessionData   = null;   // full UpgradeSession from server
  let activeSection = null;   // section_id currently in Q&A modal

  if (rvFilename) rvFilename.textContent = FILENAME;

  // ════════════════════════════════════════════════════
  // INIT — load existing session if available
  // ════════════════════════════════════════════════════

  async function init() {
    try {
      const res = await fetch(`/upgrade/srs/${FILE_ID}/session`);
      if (res.ok) {
        sessionData = await res.json();
        if (sessionData.pipeline_status !== 'created') {
          renderSession(sessionData);
        }
      }
    } catch {
      // No session yet — show analyse panel, that's fine
    }
  }

  init();

  // ════════════════════════════════════════════════════
  // STEP 1: ANALYSE
  // ════════════════════════════════════════════════════

  analyseBtn?.addEventListener('click', async () => {
    if (!FILE_ID) return;

    analyseBtn.disabled = true;
    analyseBtnLbl.textContent = 'Analysing…';
    showOverlay('Preparing analysis…', 0, 0);

    // Open SSE stream BEFORE triggering analysis
    const evtSource = new EventSource(`/upgrade/srs/${FILE_ID}/progress`);
    evtSource.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data);
        if (ev.type === 'heartbeat') return;

        if (ev.type === 'start') {
          updateOverlay('Starting analysis…', 0, ev.total, null);

        } else if (ev.type === 'section_start') {
          // ← This fires BEFORE the agent call — shows what's being analysed RIGHT NOW
          updateOverlay('Analysing section…', ev.index - 1, ev.total, ev.heading);

        } else if (ev.type === 'section_done') {
          // Fires AFTER — advances the counter
          updateOverlay('Analysing…', ev.index, ev.total, ev.heading + ' ✓');

        } else if (ev.type === 'stage_done' && ev.stage === 'analysis') {
          updateOverlay(ev.message, ev.total, ev.total, null);

        } else if (ev.type === 'start' && ev.stage === 'questions') {
          updateOverlay('Generating questions…', 0, ev.total, null);

        } else if (ev.type === 'section_start' && ev.stage === 'questions') {
          updateOverlay('Generating questions…', ev.index - 1, ev.total, ev.heading);

        } else if (ev.type === 'section_done' && ev.stage === 'questions') {
          updateOverlay('Generating questions…', ev.index, ev.total, ev.heading + ' ✓');

        } else if (ev.type === 'stage_done' && ev.stage === 'questions') {
          updateOverlay(ev.message, ev.total, ev.total, null);

        } else if (ev.type === 'done') {
          evtSource.close();
        }
      } catch {}
    };
    evtSource.onerror = () => evtSource.close();

    try {
      // Step 1: run analysis (auto-creates session)
      const res = await fetch(`/upgrade/srs/${FILE_ID}/analyse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score_threshold: 6.5 }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Analysis failed (${res.status})`);
      }

      updateOverlay('Generating clarification questions…', 0, 0);

      // Step 2: generate questions
      const qRes = await fetch(`/upgrade/srs/${FILE_ID}/questions`, { method: 'POST' });
      if (!qRes.ok) {
        const err = await qRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Question generation failed');
      }

      // Load full session for render
      const sessionRes = await fetch(`/upgrade/srs/${FILE_ID}/session`);
      sessionData = await sessionRes.json();

      hideOverlay();
      renderSession(sessionData);

    } catch (err) {
      evtSource.close();
      hideOverlay();
      showStatus(`✕ ${err.message}`, 'error');
      analyseBtn.disabled = false;
      analyseBtnLbl.textContent = 'Retry Analysis';
    }
  });

  // ════════════════════════════════════════════════════
  // PROGRESS OVERLAY
  // ════════════════════════════════════════════════════

  let _overlayEl = null;

  function showOverlay(message, current, total) {
    if (!_overlayEl) {
      _overlayEl = document.createElement('div');
      _overlayEl.id = 'rvOverlay';
      _overlayEl.innerHTML = `
        <div class="rv-overlay-card">
          <div class="rv-overlay-icon">🔬</div>
          <div class="rv-overlay-title" id="rvOvTitle">Analysing…</div>
          <div class="rv-overlay-sub" id="rvOvSub"></div>
          <div class="rv-overlay-track">
            <div class="rv-overlay-fill" id="rvOvFill"></div>
          </div>
          <div class="rv-overlay-counter" id="rvOvCounter"></div>
        </div>`;
      _overlayEl.style.cssText = `
        position:fixed;inset:0;z-index:2000;
        background:rgba(0,0,0,0.72);
        backdrop-filter:blur(6px);
        display:flex;align-items:center;justify-content:center;
        animation:fadeIn .2s ease;`;
      document.body.appendChild(_overlayEl);
    }
    updateOverlay(message, current, total);
  }

  function updateOverlay(message, current, total, currentSection) {
    if (!_overlayEl) return;
    const title   = document.getElementById('rvOvTitle');
    const sub     = document.getElementById('rvOvSub');
    const fill    = document.getElementById('rvOvFill');
    const counter = document.getElementById('rvOvCounter');

    if (title) title.textContent = message;

    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    if (fill)  fill.style.width = (total > 0 ? pct : 30) + '%';

    // Show which section is being processed right now
    if (sub) {
      if (currentSection) {
        sub.textContent = currentSection;
        sub.style.color = 'var(--accent)';
      } else if (total > 0 && current > 0) {
        sub.textContent = `${pct}% complete`;
        sub.style.color = 'var(--accent)';
      } else {
        sub.textContent = '';
      }
    }

    if (counter) {
      counter.textContent = total > 0 ? `${current} of ${total} sections` : '';
    }
  }

  function hideOverlay() {
    if (_overlayEl) {
      _overlayEl.style.opacity = '0';
      _overlayEl.style.transition = 'opacity .3s';
      setTimeout(() => { _overlayEl?.remove(); _overlayEl = null; }, 320);
    }
  }

  // ════════════════════════════════════════════════════
  // RENDER SESSION
  // ════════════════════════════════════════════════════

  function renderSession(session) {
    // Hide analyse panel, show results
    if (analysePanel) analysePanel.style.display = 'none';
    summaryBar.style.display    = 'flex';
    sectionsEl.style.display    = 'flex';

    // Summary bar
    const s = session.upgrade_summary;
    setVal('rvStatTotal', session.sections.length);
    setVal('rvStatKept',  s.kept || 0);
    setVal('rvStatFlag',  s.needs_upgrade || 0);
    setVal('rvStatDone',  (s.accepted || 0) + (s.edited || 0));

    // Section cards
    sectionsEl.innerHTML = session.sections.map(renderSectionCard).join('');

    // Wire up interactions
    wireCardHeaders();
    wireActionButtons();
  }

  function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) {
      const valEl = el.querySelector('.rv-summary-val');
      if (valEl) valEl.textContent = val;
    }
  }

  // ════════════════════════════════════════════════════
  // SECTION CARD HTML
  // ════════════════════════════════════════════════════

  function renderSectionCard(s) {
    const score      = s.score_overall;
    const scoreLabel = score !== null ? score.toFixed(1) : '—';
    const scoreCls   = score === null ? 'rv-score-na'
                     : score >= 7    ? 'rv-score-good'
                     : score >= 5    ? 'rv-score-warn'
                     :                 'rv-score-bad';

    const statusCls  = statusClass(s.status);
    const cardCls    = cardClass(s.status);

    const indentPx = (s.level - 1) * 16;

    return `
      <div class="rv-section-card ${cardCls}" id="card-${safeId(s.section_id)}" data-sid="${escHtml(s.section_id)}">
        <div class="rv-card-header" data-toggle="${safeId(s.section_id)}">
          <div style="width:${indentPx}px;flex-shrink:0"></div>
          <div class="rv-section-num">${escHtml(s.section_id)}</div>
          <div class="rv-section-heading">${escHtml(s.heading)}</div>
          <span class="rv-score-badge ${scoreCls}">${scoreLabel}</span>
          <span class="rv-status-pill ${statusCls}">${statusLabel(s.status)}</span>
          <span class="rv-chevron">▼</span>
        </div>
        <div class="rv-card-body">
          ${renderScoreBreakdown(s.score)}
          ${renderFlags(s.flags)}
          ${s.original_content && s.status !== 'upgraded' ? `
            <div style="margin-bottom:12px">
              <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-bottom:6px">Original content</div>
              <div style="background:rgba(0,0,0,0.15);border:1px solid var(--border);border-radius:10px;padding:10px 12px;font-size:0.8rem;color:var(--color-text-secondary);line-height:1.6;white-space:pre-wrap;max-height:160px;overflow-y:auto">${escHtml(s.original_content)}</div>
            </div>` : ''}
          ${renderSectionActions(s)}
        </div>
      </div>`;
  }

  function renderScoreBreakdown(score) {
    if (!score) return '<div style="color:var(--color-text-secondary);font-size:0.78rem;margin:10px 0;padding:8px 12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid var(--border)">This subsection was not individually scored — it is part of a parent section.</div>';

    const dims = [
      { key: 'completeness',   label: 'Complete' },
      { key: 'clarity',        label: 'Clarity' },
      { key: 'ieee_compliance',label: 'IEEE 830' },
      { key: 'testability',    label: 'Testable' },
      { key: 'consistency',    label: 'Consistent' },
    ];

    return `<div class="rv-score-breakdown">
      ${dims.map(d => {
        const val = score[d.key] ?? 0;
        const pct = (val / 10) * 100;
        const color = val >= 7 ? '#22c55e' : val >= 5 ? '#f59e0b' : '#f87171';
        return `
          <div class="rv-dim">
            <div class="rv-dim-label">${d.label}</div>
            <div class="rv-dim-bar">
              <div class="rv-dim-fill" style="width:${pct}%;background:${color}"></div>
            </div>
            <div class="rv-dim-val">${val.toFixed(1)}</div>
          </div>`;
      }).join('')}
    </div>`;
  }

  function renderFlags(flags) {
    if (!flags || !flags.length) return '';
    return `<div class="rv-flags">
      ${flags.map(f => `<div class="rv-flag-item">${escHtml(f)}</div>`).join('')}
    </div>`;
  }

  function renderSectionActions(s) {
    // Kept / already reviewed — no actions needed
    if (s.status === 'kept') {
      return `<div style="font-size:0.8rem;color:#22c55e;padding:4px 0">✓ Section passes quality threshold</div>`;
    }

    if (s.status === 'accepted') {
      return `<div style="font-size:0.8rem;color:var(--accent);padding:4px 0">✓ Upgrade accepted</div>`;
    }

    if (s.status === 'edited') {
      return `<div style="font-size:0.8rem;color:var(--primary);padding:4px 0">✓ Custom edit saved</div>`;
    }

    if (s.status === 'rejected') {
      return `<div style="font-size:0.8rem;color:#f87171;padding:4px 0">✕ Rejected — original content will be kept</div>`;
    }

    // Has questions pending
    if ((s.status === 'questioned' || s.status === 'pending') && s.questions && s.questions.length) {
      const allAnswered = s.questions.every(q => q.answered);
      if (!allAnswered) {
        return `<div class="rv-section-actions">
          <button class="rv-btn-action rv-btn-qa" data-qa="${escHtml(s.section_id)}">
            💬 Answer Questions (${s.questions.filter(q => !q.answered).length} remaining)
          </button>
        </div>`;
      }
    }

    // Upgraded content ready for review
    if (s.status === 'upgraded' && s.upgraded_content) {
      return renderDiffActions(s);
    }

    // Answered — waiting for upgrade writer
    if (s.status === 'answered') {
      return `<div style="font-size:0.8rem;color:var(--muted);padding:4px 0">⏳ Waiting for upgrade writer…</div>`;
    }

    // status=pending + needs_upgrade=false = subsection not individually analysed
    if (s.status === 'pending' && !s.needs_upgrade) {
      return `<div style="font-size:0.78rem;color:var(--color-text-secondary);padding:4px 0">
        Original content preserved as-is.
      </div>`;
    }

    // Flagged but no questions generated (edge case — re-run analysis)
    return `<div style="font-size:0.75rem;color:#f59e0b;padding:4px 0">
      ⚑ Flagged for upgrade — re-run analysis to generate questions.
    </div>`;
  }

  function renderDiffActions(s) {
    return `
      <div style="margin-bottom:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
          <div>
            <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-bottom:6px">Original</div>
            <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:10px;padding:10px 12px;font-size:0.8rem;color:var(--muted);line-height:1.6;max-height:140px;overflow-y:auto;white-space:pre-wrap">${escHtml(s.original_content || '[empty]')}</div>
          </div>
          <div>
            <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--accent);margin-bottom:6px">Upgraded</div>
            <div style="background:rgba(0,229,201,0.06);border:1px solid rgba(0,229,201,0.2);border-radius:10px;padding:10px 12px;font-size:0.8rem;color:var(--text);line-height:1.6;max-height:140px;overflow-y:auto;white-space:pre-wrap">${escHtml(s.upgraded_content)}</div>
          </div>
        </div>
        <textarea class="rv-question-input" id="edit-${safeId(s.section_id)}" placeholder="Edit the upgraded content here if needed…" style="min-height:80px">${escHtml(s.upgraded_content)}</textarea>
      </div>
      <div class="rv-section-actions">
        <button class="rv-btn-action rv-btn-accept" data-accept="${escHtml(s.section_id)}">✓ Accept</button>
        <button class="rv-btn-action rv-btn-accept" data-edit="${escHtml(s.section_id)}" style="background:rgba(79,142,255,0.1);border-color:rgba(79,142,255,0.3);color:var(--primary)">✏ Save Edit</button>
        <button class="rv-btn-action rv-btn-reject" data-reject="${escHtml(s.section_id)}">✕ Reject</button>
      </div>`;
  }

  // ════════════════════════════════════════════════════
  // WIRE INTERACTIONS
  // ════════════════════════════════════════════════════

  function wireCardHeaders() {
    sectionsEl.querySelectorAll('[data-toggle]').forEach(header => {
      header.addEventListener('click', () => {
        const id   = header.dataset.toggle;
        const card = document.getElementById(`card-${id}`);
        card?.classList.toggle('open');
      });
    });
  }

  function wireActionButtons() {
    // Q&A button
    sectionsEl.querySelectorAll('[data-qa]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        openQaModal(btn.dataset.qa);
      });
    });

    // Accept
    sectionsEl.querySelectorAll('[data-accept]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        actOnSection(btn.dataset.accept, 'accept');
      });
    });

    // Edit
    sectionsEl.querySelectorAll('[data-edit]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const sid = btn.dataset.edit;
        const textarea = document.getElementById(`edit-${safeId(sid)}`);
        actOnSection(sid, 'edit', textarea?.value || '');
      });
    });

    // Reject
    sectionsEl.querySelectorAll('[data-reject]').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        actOnSection(btn.dataset.reject, 'reject');
      });
    });
  }

  // ════════════════════════════════════════════════════
  // Q&A MODAL
  // ════════════════════════════════════════════════════

  function openQaModal(sectionId) {
    if (!sessionData) return;
    const section = sessionData.sections.find(s => s.section_id === sectionId);
    if (!section || !section.questions?.length) return;

    activeSection = sectionId;
    qaTitle.textContent = `${section.section_id} — ${section.heading}`;

    qaBody.innerHTML = section.questions.map(q => `
      <div class="rv-question-item">
        <div class="rv-question-dim">${escHtml(q.dimension)}</div>
        <div class="rv-question-label">${escHtml(q.question)}</div>
        <textarea
          class="rv-question-input"
          data-qid="${escHtml(q.question_id)}"
          placeholder="Your answer…"
        >${escHtml(q.answer || '')}</textarea>
      </div>`).join('');

    qaBackdrop.style.display = 'flex';
  }

  function closeQaModal() {
    qaBackdrop.style.display = 'none';
    activeSection = null;
  }

  qaClose?.addEventListener('click', closeQaModal);
  qaCancel?.addEventListener('click', closeQaModal);
  qaBackdrop?.addEventListener('click', e => {
    if (e.target === qaBackdrop) closeQaModal();
  });

  qaSubmit?.addEventListener('click', async () => {
    if (!activeSection) return;

    const answers = {};
    qaBody.querySelectorAll('[data-qid]').forEach(ta => {
      answers[ta.dataset.qid] = ta.value.trim();
    });

    const unanswered = Object.values(answers).filter(v => !v).length;
    if (unanswered > 0) {
      alert(`Please answer all ${unanswered} remaining question(s).`);
      return;
    }

    qaSubmit.disabled = true;
    qaSubmit.textContent = 'Saving…';

    try {
      const res = await fetch(`/upgrade/srs/${FILE_ID}/answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          submissions: [{ section_id: activeSection, answers }],
        }),
      });

      if (!res.ok) throw new Error('Failed to save answers');

      // Reload session to reflect updated state
      const sessionRes = await fetch(`/upgrade/srs/${FILE_ID}/session`);
      sessionData = await sessionRes.json();

      closeQaModal();
      renderSession(sessionData);

    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      qaSubmit.disabled = false;
      qaSubmit.innerHTML = '<span>💬</span> Submit Answers';
    }
  });

  // ════════════════════════════════════════════════════
  // SECTION ACCEPT / REJECT / EDIT
  // ════════════════════════════════════════════════════

  async function actOnSection(sectionId, action, editedContent = '') {
    try {
      const res = await fetch(`/upgrade/srs/${FILE_ID}/section/${encodeURIComponent(sectionId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, edited_content: editedContent }),
      });

      if (!res.ok) throw new Error('Action failed');

      // Reload session
      const sessionRes = await fetch(`/upgrade/srs/${FILE_ID}/session`);
      sessionData = await sessionRes.json();
      renderSession(sessionData);

    } catch (err) {
      showStatus(`✕ ${err.message}`, 'error');
    }
  }

  // ════════════════════════════════════════════════════
  // HELPERS
  // ════════════════════════════════════════════════════

  function statusClass(status) {
    const map = {
      kept: 'kept', pending: 'flagged', questioned: 'flagged',
      answered: 'answered', upgraded: 'flagged',
      accepted: 'accepted', edited: 'edited', rejected: 'rejected',
    };
    return map[status] || 'flagged';
  }

  function cardClass(status) {
    if (status === 'kept')     return 'status-kept';
    if (status === 'accepted') return 'status-accepted';
    if (status === 'rejected') return 'status-rejected';
    if (status === 'edited')   return 'status-edited';
    return 'status-flagged';
  }

  function statusLabel(status) {
    const map = {
      pending: 'Flagged', kept: 'Passed', questioned: 'Needs answers',
      answered: 'Answered', upgraded: 'Review', accepted: 'Accepted',
      edited: 'Edited', rejected: 'Rejected',
    };
    return map[status] || status;
  }

  function safeId(sid) {
    return String(sid).replace(/[^a-zA-Z0-9_-]/g, '_');
  }

  function animateProgress(fill, target) {
    let current = 0;
    const tick = () => {
      if (current < target) {
        current = Math.min(current + Math.random() * 6 + 2, target);
        fill.style.width = current + '%';
        requestAnimationFrame(tick);
      }
    };
    requestAnimationFrame(tick);
  }

  function showStatus(msg, type) {
    rvStatus.innerHTML = msg;
    rvStatus.className = `up-status visible ${type}`;
  }

  function clearStatus() {
    rvStatus.className = 'up-status';
    rvStatus.textContent = '';
  }

});