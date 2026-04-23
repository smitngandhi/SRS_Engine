/**
 * quota_manager.js
 * ────────────────
 * Global unified quota manager. 
 * Fetches /api/my-quota and updates the floating quota bar in base.html.
 * 
 * Usage:
 *   window.refreshQuotas(); // Call this whenever a job finishes or a message is sent.
 */

window.refreshQuotas = async function() {
    const bar = document.getElementById('unifiedQuotaBar');
    if (!bar) return;

    try {
        const res = await fetch('/api/my-quota');
        if (!res.ok) return;
        const q = await res.json();

        const isAdmin = q.is_admin || false;

        // SRS (Global docx_count)
        updatePill('srs', q.docx_count, q.docx_limit, isAdmin);

        // Chat (Global chat_query_count)
        updatePill('chat', q.chat_query_count, q.chat_query_limit, isAdmin);

        // Per-project quotas (Diagrams & Upgrades)
        const urlParams = new URLSearchParams(window.location.search);
        const projectName = urlParams.get('project_id') || urlParams.get('project');
        
        if (projectName && q.projects && q.projects[projectName]) {
            const p = q.projects[projectName];
            updatePill('diagrams', p.diagram_count || 0, q.diag_limit || 2, isAdmin);
            updatePill('upgrades', p.upgrade_count || 0, q.upgrade_limit || 2, isAdmin);
            document.getElementById('quota-diagrams').style.display = 'flex';
            document.getElementById('quota-upgrades').style.display = 'flex';
        } else {
            document.getElementById('quota-diagrams').style.display = 'none';
            document.getElementById('quota-upgrades').style.display = 'none';
        }

        bar.style.display = 'flex';
        if (isAdmin) bar.classList.add('admin-tier');

    } catch (err) {
        console.warn('Quota refresh failed:', err);
    }
};

function updatePill(id, current, limit, isAdmin = false) {
    const valEl = document.getElementById(`val-${id}`);
    const fillEl = document.getElementById(`fill-${id}`);
    const pill = document.getElementById(`quota-${id}`);
    
    if (!valEl || !fillEl) return;

    if (isAdmin) {
        valEl.textContent = `∞ Unlimited`;
        fillEl.style.width = `100%`;
        fillEl.style.background = `linear-gradient(to right, #ffd700, #ffae00)`; // Gold for admin
        pill.classList.remove('warning', 'danger');
        pill.classList.add('admin');
        return;
    }

    valEl.textContent = `${current}/${limit}`;
    const percent = Math.min(100, (current / limit) * 100);
    fillEl.style.width = `${percent}%`;

    // Visual states
    pill.classList.remove('warning', 'danger', 'admin');
    if (percent >= 100) {
        pill.classList.add('danger');
    } else if (percent >= 70) {
        pill.classList.add('warning');
    }
}

// Auto-refresh on page load
document.addEventListener('DOMContentLoaded', () => {
    window.refreshQuotas();
    
    // Periodically refresh every 60 seconds as a fallback
    setInterval(window.refreshQuotas, 60000);

    // ── DRAGGABLE LOGIC ──────────────────────────────────────
    const bar = document.getElementById('unifiedQuotaBar');
    if (!bar) return;

    let isDragging = false;
    let offset = { x: 0, y: 0 };

    // Restore position from localStorage
    const savedPos = localStorage.getItem('quotaBarPos');
    if (savedPos) {
        const { left, top } = JSON.parse(savedPos);
        bar.style.left = left;
        bar.style.top = top;
        bar.style.bottom = 'auto';
        bar.style.transform = 'none';
    }

    bar.addEventListener('mousedown', (e) => {
        if (e.target.closest('button') || e.target.closest('a')) return;
        isDragging = true;
        bar.classList.add('dragging');
        
        // Calculate offset
        const rect = bar.getBoundingClientRect();
        offset.x = e.clientX - rect.left;
        offset.y = e.clientY - rect.top;
        
        // Prevent text selection
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;

        let x = e.clientX - offset.x;
        let y = e.clientY - offset.y;

        // Boundary checks
        const rect = bar.getBoundingClientRect();
        const pad = 10;
        x = Math.max(pad, Math.min(x, window.innerWidth - rect.width - pad));
        y = Math.max(pad, Math.min(y, window.innerHeight - rect.height - pad));

        bar.style.left = x + 'px';
        bar.style.top = y + 'px';
        bar.style.bottom = 'auto';
        bar.style.transform = 'none';
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            bar.classList.remove('dragging');
            // Save position
            localStorage.setItem('quotaBarPos', JSON.stringify({
                left: bar.style.left,
                top: bar.style.top
            }));
        }
    });

    // ── TOGGLE LOGIC ──────────────────────────────────────────
    const toggleBtn = document.getElementById('quotaToggle');
    if (toggleBtn) {
        // Restore collapse state
        const isCollapsed = localStorage.getItem('quotaBarCollapsed') === 'true';
        if (isCollapsed) {
            bar.classList.add('collapsed');
        }

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // prevent drag trigger
            bar.classList.toggle('collapsed');
            localStorage.setItem('quotaBarCollapsed', bar.classList.contains('collapsed'));
        });
    }
});
