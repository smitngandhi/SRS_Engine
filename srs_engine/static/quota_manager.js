/**
 * quota_manager.js
 * ────────────────
 * Manages the integrated header usage status.
 * Fetches /api/my-quota and updates the header pill.
 */

let lastQuotaData = null;
let lastFetchTime = 0;

window.refreshQuotas = async function(force = false) {
    const headerPill = document.getElementById('headerUsage');
    if (!headerPill) return null;

    const now = Date.now();
    // Cache for 1 second unless forced
    if (!force && lastQuotaData && (now - lastFetchTime < 1000)) {
        updateHeaderUI(lastQuotaData);
        return lastQuotaData;
    }

    try {
        const res = await fetch('/api/my-quota');
        if (!res.ok) return null;
        const q = await res.json();
        
        lastQuotaData = q;
        lastFetchTime = now;

        updateHeaderUI(q);
        return q;
    } catch (err) {
        console.warn('Quota refresh failed:', err);
        return null;
    }
};

function updateHeaderUI(q) {
    const headerPill = document.getElementById('headerUsage');
    if (!headerPill) return;

    const isAdmin = q.is_admin || false;

    // Update counts
    updateCount('srs', q.docx_count, q.docx_limit, isAdmin);
    updateCount('chat', q.chat_query_count, q.chat_query_limit, isAdmin);

    // Per-project counts
    const urlParams = new URLSearchParams(window.location.search);
    const rawProject = window.currentProject || urlParams.get('project_id') || urlParams.get('project');
    const projectName = rawProject ? decodeURIComponent(rawProject) : null;
    
    let diagVal = 0;
    let diagLimit = q.diag_limit || 2;
    let upgradeVal = 0;
    let upgradeLimit = q.upgrade_limit || 2;

    if (projectName && q.projects && q.projects[projectName]) {
        diagVal = q.projects[projectName].diagram_count || 0;
        upgradeVal = q.projects[projectName].upgrade_count || 0;
    }
    updateCount('diagrams', diagVal, diagLimit, isAdmin);
    updateCount('upgrades', upgradeVal, upgradeLimit, isAdmin);

    headerPill.style.display = 'block';
}

function updateCount(id, current, limit, isAdmin = false) {
    const el = document.getElementById(`header-val-${id}`);
    if (!el) return;

    if (isAdmin) {
        el.textContent = '∞ Unlimited';
        el.style.color = '#00e5c9'; // Accent color for unlimited
        return;
    }

    el.textContent = `${current}/${limit}`;
    const percent = limit > 0 ? (current / limit) * 100 : 0;
    
    if (limit > 0 && percent >= 100) {
        el.style.color = '#ef4444';
    } else if (percent >= 80) {
        el.style.color = '#fbbf24';
    } else {
        el.style.color = 'var(--primary)';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.refreshQuotas();
    setInterval(window.refreshQuotas, 60000);
});
