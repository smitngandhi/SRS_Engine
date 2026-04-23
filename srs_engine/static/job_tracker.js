/**
 * static/job_tracker.js
 *
 * API routes (no router prefix):
 *   GET  /my-jobs                       → list jobs for current user
 *   GET  /job/{job_id}/status           → single job object
 *   GET  /job/{job_id}/status/stream    → SSE stream
 *
 * /my-jobs is used instead of /jobs to avoid conflicting with the
 * GET /jobs HTML page route registered in pages_router.
 */

const TERMINAL = new Set(['completed', 'failed']);

const activeSources = new Map();
const cardMap       = new Map();

let currentFilter = 'all';
let allJobs       = [];

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    bindFilterTabs();
    loadJobs();
});

// ── Filter tabs ────────────────────────────────────────────────────────────

function bindFilterTabs() {
    document.getElementById('filterTabs').addEventListener('click', e => {
        const tab = e.target.closest('.filter-tab');
        if (!tab) return;
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter;
        applyFilter();
    });
}

function applyFilter() {
    const filtered = currentFilter === 'all'
        ? allJobs
        : allJobs.filter(j => j.status === currentFilter);
    renderGrid(filtered);
}

// ── Load jobs ──────────────────────────────────────────────────────────────

async function loadJobs() {
    showSkeletons();
    hideEmpty();
    hideError();

    try {
        const res = await fetch('/my-jobs');   // ← /my-jobs not /jobs

        if (res.status === 401 || res.status === 403) {
            window.location.href = '/login?next=/jobs';
            return;
        }
        if (!res.ok) throw new Error(`Server returned ${res.status}`);

        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            throw new Error('Expected JSON but got HTML — possible route conflict');
        }

        allJobs = await res.json();
        updateStats(allJobs);
        applyFilter();

        allJobs.forEach(job => {
            if (!TERMINAL.has(job.status)) openStream(job.job_id);
        });

    } catch (err) {
        console.error('loadJobs error:', err);
        showError('Could not load jobs — ' + err.message);
    }
}

// ── Render grid ────────────────────────────────────────────────────────────

function renderGrid(jobs) {
    const grid = document.getElementById('jobsGrid');
    grid.innerHTML = '';
    cardMap.clear();

    if (!jobs.length) {
        showEmpty();
        return;
    }

    hideEmpty();
    jobs.forEach((job, i) => {
        const card = buildCard(job);
        card.style.animationDelay = `${i * 0.05}s`;
        grid.appendChild(card);
        cardMap.set(job.job_id, card);
    });
}

// ── Build card ─────────────────────────────────────────────────────────────

function buildCard(job) {
    const tmpl = document.getElementById('jobCardTemplate');
    const card = tmpl.content.cloneNode(true).querySelector('.job-card');

    card.dataset.jobId  = job.job_id;
    card.dataset.status = job.status;

    const badge = card.querySelector('.job-status-badge');
    badge.dataset.status = job.status;
    badge.textContent    = statusLabel(job.status);

    card.querySelector('.job-name').textContent = job.project_name || 'Untitled Project';

    updateStepText(card, job);
    updateProgress(card, job);
    card.querySelector('.job-created').textContent = formatDate(job.created_at);
    updateElapsed(card, job);
    renderActions(card, job);

    return card;
}

function patchCard(card, job) {
    card.dataset.status = job.status;

    const badge = card.querySelector('.job-status-badge');
    badge.dataset.status = job.status;
    badge.textContent    = statusLabel(job.status);

    updateStepText(card, job);
    updateProgress(card, job);
    updateElapsed(card, job);
    renderActions(card, job);

    let errEl = card.querySelector('.job-error-msg');
    if (job.status === 'failed' && job.error) {
        if (!errEl) {
            errEl = document.createElement('div');
            errEl.className = 'job-error-msg';
            card.querySelector('.job-actions').before(errEl);
        }
        errEl.textContent = `Error: ${job.error}`;
    } else if (errEl) {
        errEl.remove();
    }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function updateProgress(card, job) {
    const pct = job.progress ?? 0;
    card.querySelector('.job-progress-fill').style.width = `${pct}%`;
    card.querySelector('.job-progress-pct').textContent  = `${pct}%`;
}

function updateStepText(card, job) {
    const el = card.querySelector('.job-step-text');
    const qRow = card.querySelector('.job-queue-row');
    const qPos = card.querySelector('.job-queue-pos');

    if      (job.status === 'completed') el.textContent = 'Document ready';
    else if (job.status === 'failed')    el.textContent = 'Generation failed';
    else                                  el.textContent = job.current_step || '—';

    // Queue position indicator
    if (job.status === 'pending' && job.queue_position !== undefined && job.queue_position !== null) {
        if (qRow) qRow.style.display = 'block';
        if (qPos) qPos.textContent = job.queue_position;
    } else {
        if (qRow) qRow.style.display = 'none';
    }
}

function updateElapsed(card, job) {
    const el = card.querySelector('.job-elapsed');
    if (job.completed_at) {
        const dur = new Date(job.completed_at) - new Date(job.created_at);
        el.textContent = `Completed in ${formatMs(dur)}`;
    } else if (job.status === 'processing' || job.status === 'pending') {
        const age = Date.now() - new Date(job.created_at);
        el.textContent = `Started ${formatMs(age)} ago`;
    } else {
        el.textContent = '';
    }
}

/**
 * BUG FIX: The old code used job.job_id (a MongoDB UUID) as the doc_id,
 * which never matched any file on disk. The /api/download-srs/{doc_id}
 * endpoint looks for ./generated_srs/{user_id}/{doc_id}.docx, and the
 * file is named {project_name}_SRS.docx — so doc_id must be
 * "{project_name}_SRS".
 */
function renderActions(card, job) {
    const container = card.querySelector('.job-actions');
    container.innerHTML = '';

    if (job.status === 'completed') {
        container.appendChild(makeBtn('⬇ Download', 'btn-secondary', () => {
            const docId = encodeURIComponent(`${job.project_name}_SRS`);
            window.location.href = `/api/download-srs/${docId}`;
        }));
    }
    if (job.status === 'failed') {
        container.appendChild(makeBtn('↺ Retry', 'btn-outline', () => {
            window.location.href = '/srs-generator';
        }));
    }
    if (job.status === 'processing' || job.status === 'pending') {
        const btn = makeBtn('● Live', 'btn-outline', null);
        btn.disabled = true;
        btn.style.opacity = '0.55';
        btn.style.cursor  = 'default';
        container.appendChild(btn);
    }
}

function makeBtn(label, cls, onClick) {
    const btn = document.createElement('button');
    btn.className = `btn ${cls}`;
    btn.textContent = label;
    if (onClick) btn.addEventListener('click', onClick);
    return btn;
}

// ── SSE ────────────────────────────────────────────────────────────────────

function openStream(jobId) {
    if (activeSources.has(jobId)) return;

    const es = new EventSource(`/job/${jobId}/status/stream`);
    activeSources.set(jobId, es);

    es.onmessage = e => {
        let job;
        try { job = JSON.parse(e.data); } catch { return; }

        const idx = allJobs.findIndex(j => j.job_id === jobId);
        if (idx !== -1) allJobs[idx] = job;

        const card = cardMap.get(jobId);
        if (card) patchCard(card, job);

        updateStats(allJobs);

        if (TERMINAL.has(job.status)) {
            es.close();
            activeSources.delete(jobId);
            // Refresh unified quota bar if job completed
            if (job.status === 'completed' && window.refreshQuotas) {
                window.refreshQuotas();
            }
        }
    };

    es.onerror = () => {};
}

// ── Stats ──────────────────────────────────────────────────────────────────

function updateStats(jobs) {
    const active = jobs.filter(j => j.status === 'pending' || j.status === 'processing').length;
    const done   = jobs.filter(j => j.status === 'completed').length;
    const fail   = jobs.filter(j => j.status === 'failed').length;

    document.getElementById('countAll').textContent    = jobs.length;
    document.getElementById('countActive').textContent = active;
    document.getElementById('countDone').textContent   = done;
    document.getElementById('countFail').textContent   = fail;

    const dot = document.querySelector('.stat-pill-dot');
    if (dot) dot.style.display = active > 0 ? 'block' : 'none';
}

// ── UI state ───────────────────────────────────────────────────────────────

function showSkeletons() {
    document.getElementById('jobsGrid').innerHTML = `
        <div class="job-card job-skeleton"></div>
        <div class="job-card job-skeleton"></div>
        <div class="job-card job-skeleton"></div>`;
}

function showEmpty()  { document.getElementById('jobsEmpty').style.display  = 'block'; }
function hideEmpty()  { document.getElementById('jobsEmpty').style.display  = 'none';  }

function showError(msg) {
    document.getElementById('jobsErrorMsg').textContent = msg;
    document.getElementById('jobsError').style.display  = 'flex';
    document.getElementById('jobsGrid').innerHTML       = '';
}

function hideError() { document.getElementById('jobsError').style.display = 'none'; }

// ── Format ─────────────────────────────────────────────────────────────────

function statusLabel(s) {
    return { pending: 'Pending', processing: 'Processing',
             completed: 'Completed', failed: 'Failed' }[s] ?? s;
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
}

function formatMs(ms) {
    if (ms < 60_000) return `${Math.round(ms / 1000)}s`;
    const m = Math.floor(ms / 60_000);
    const s = Math.round((ms % 60_000) / 1000);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

window.addEventListener('beforeunload', () => {
    activeSources.forEach(es => es.close());
});