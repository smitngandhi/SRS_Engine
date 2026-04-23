# SpecForge AI — Frontend Steps (F1–F10)

> Do AFTER all backend steps pass local tests.

---

## F1 — Rebrand: SRS_Engine → SpecForge AI

**Files:** `base.html`, `landing.html`, `login.html`, all page titles

**Changes:**
- Replace "SRS Engine" / "SRS_Engine" text → "SpecForge AI" everywhere
- Update `<title>` tags: `SpecForge AI — [Page Name]`
- Update logo/navbar brand text
- Update meta descriptions
- Update footer text

**Search & replace across all templates:**
```
"SRS Engine"    → "SpecForge AI"
"SRS_Engine"    → "SpecForge AI"
"srs_engine"    → "specforge-ai"  (only in user-visible text, NOT file paths)
```

> **Important:** Do NOT rename Python module paths — only user-visible strings.

---

## F2 — Update `base.html` (Remove Upload Upgrader from Nav)

**File:** `srs_engine/templates/base.html`

**Desktop nav (Tools dropdown):**
- Remove the `<a>` link to Upload Upgrader (`/srs-upgrader`)
- Replace with dimmed text:
```html
<span class="nav-link disabled" style="opacity:0.5; cursor:default;">
  🔒 Upload Upgrader <span class="badge">Coming Soon</span>
</span>
```

**Mobile drawer:** Same change — replace the link with a dimmed Coming Soon item.

**Keep these nav items active:**
- SRS Generator
- Section Upgrader (generated)
- Diagram Studio
- Document Navigator
- Job Tracker
- Project Buckets

---

## F3 — Update `landing.html` (Tool Card → Coming Soon)

**File:** `srs_engine/templates/pages/landing.html`

**Find the Upload Upgrader tool card** (`.tool-card--upgrader` or similar).

**Replace** the card's clickable link with a non-clickable Coming Soon card:
```html
<div class="tool-card tool-card--coming-soon" style="opacity:0.6; pointer-events:none; position:relative;">
  <div class="coming-soon-badge" style="position:absolute; top:12px; right:12px; 
       background:linear-gradient(135deg,#667eea,#764ba2); color:white; 
       padding:4px 12px; border-radius:12px; font-size:0.75rem; font-weight:600;">
    Coming Soon
  </div>
  <div class="tool-card__icon">📄</div>
  <h3>Upload Upgrader</h3>
  <p>Upload existing SRS documents (PDF/DOCX) and upgrade them with AI-powered multi-agent analysis.</p>
</div>
```

**Update tool count text** if it says "Six tools" → adjust or remove the count.

---

## F4 — Replace `srs_upgrader.html` (Coming Soon Page)

**File:** `srs_engine/templates/pages/srs_upgrader.html`

**Replace entire page content** with a premium Coming Soon design:

```html
{% extends "base.html" %}
{% block title %}Upload Upgrader — Coming Soon | SpecForge AI{% endblock %}
{% block content %}
<div style="display:flex; align-items:center; justify-content:center; min-height:70vh; padding:2rem;">
  <div style="max-width:600px; text-align:center; padding:3rem; 
       background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); 
       border-radius:24px; backdrop-filter:blur(20px);">
    <div style="font-size:4rem; margin-bottom:1rem;">🚀</div>
    <h1 style="font-size:2rem; margin-bottom:0.5rem;">Upload Upgrader</h1>
    <p style="color:var(--text-secondary); font-size:1.1rem; margin-bottom:2rem;">
      Upload existing SRS documents (PDF/DOCX) and upgrade them with our 
      multi-agent debate pipeline. This feature is coming in the next release.
    </p>
    <div style="padding:1rem; background:rgba(102,126,234,0.1); border-radius:12px; 
         border:1px solid rgba(102,126,234,0.2); margin-bottom:1.5rem;">
      <p style="margin:0; font-size:0.9rem; color:var(--text-secondary);">
        <strong>What's coming:</strong> Multi-format parsing (PDF, DOCX) · 
        Section-level analysis · AI-powered improvement suggestions · 
        Side-by-side comparison view
      </p>
    </div>
    <a href="/home" class="btn btn--primary" style="display:inline-block; padding:0.75rem 2rem;">
      ← Back to Dashboard
    </a>
  </div>
</div>
{% endblock %}
```

---

## F5 — Add "General SRS" Banner to `srs_generator.html`

**File:** `srs_engine/templates/pages/srs_generator.html`

**On Step 2 (System Context)**, below the domain selector, add:

```html
<div style="margin:1rem 0; padding:0.75rem 1rem; background:rgba(102,126,234,0.08); 
     border-left:3px solid #667eea; border-radius:0 8px 8px 0; font-size:0.85rem;">
  ℹ️ <strong>General SRS</strong> — Domain-specific templates 
  (Healthcare, Finance, Aerospace) are launching soon.
</div>
```

**Also add quota display** at the top of the form:
```html
<div id="srs-quota-banner" style="display:none; margin-bottom:1rem; padding:0.75rem; 
     background:rgba(255,183,77,0.1); border:1px solid rgba(255,183,77,0.3); border-radius:8px;">
</div>
<script>
  fetch('/api/my-quota').then(r=>r.json()).then(q => {
    const remaining = 2 - (q.docx_count || 0);
    const el = document.getElementById('srs-quota-banner');
    el.style.display = 'block';
    if (remaining <= 0) {
      el.innerHTML = '🔒 You have used all 2 SRS document slots on the free plan.';
      el.style.background = 'rgba(244,67,54,0.1)';
      el.style.borderColor = 'rgba(244,67,54,0.3)';
      // Disable submit button
      document.querySelector('[type="submit"]')?.setAttribute('disabled', 'true');
    } else {
      el.innerHTML = `📄 ${remaining} of 2 SRS documents remaining on free plan.`;
    }
  }).catch(() => {});
</script>
```

---

## F6 — Add Quota UI to `diagram_studio.html`

**File:** `srs_engine/templates/pages/diagram_studio.html`

**Add after project selector loads**, a quota banner:
```html
<div id="diagram-quota" class="quota-banner" style="display:none;"></div>
```

**In the JS** (or `diagram_studio.js`), after project selection:
```javascript
async function updateDiagramQuota(projectName) {
  const res = await fetch('/api/my-quota');
  const q = await res.json();
  const projData = q.projects?.[projectName] || {};
  const used = projData.diagram_count || 0;
  const remaining = 2 - used;
  const el = document.getElementById('diagram-quota');
  el.style.display = 'block';
  if (remaining <= 0) {
    el.innerHTML = '🔒 You have used all 2 diagram slots for this project.';
    el.className = 'quota-banner quota-exhausted';
    document.getElementById('generate-btn')?.setAttribute('disabled', 'true');
  } else {
    el.innerHTML = `🎨 ${remaining} of 2 diagrams remaining for "${projectName}"`;
    el.className = 'quota-banner';
  }
}
```

---

## F7 — Add Quota UI to Section Upgrader

**Files:** `srs_generated_upgrader.html`, `srs_section_upgrader.html`, `generated_upgrader.js`

**Same pattern as F6:** After project is selected, fetch `/api/my-quota` and show:
```
🔧 2 of 2 upgrades remaining for "ProjectName"
```

Disable the "Preview Upgrade" button when quota is 0.

---

## F8 — Update `job_tracker.html` / `job_tracker.js` (Queue Position)

**File:** `srs_engine/static/job_tracker.js`

**In the SSE handler**, when job status is `pending`, show queue position:
```javascript
if (data.status === 'pending' && data.queue_position > 0) {
  const waitMin = data.queue_position * 4;
  stepEl.textContent = `⏳ You are #${data.queue_position} in queue — estimated wait: ~${waitMin} min`;
}
```

**Add email UX message** after job submission:
```javascript
// After receiving job_id from POST /generate_srs response
if (response.email_delivery) {
  showNotification('📧 ' + response.email_delivery, 'info');
}
```

**Add ephemeral file warning** in the job card when status = completed:
```javascript
if (data.status === 'completed') {
  // Add notice
  cardEl.querySelector('.download-area').insertAdjacentHTML('afterend',
    '<p class="file-notice">⚠️ Download now — files are not stored permanently. A copy has been emailed to you.</p>');
}
```

---

## F9 — Update `login.html` (Beta Full Message)

**File:** `srs_engine/templates/login.html`

**The `error` query param already displays.** Just style the beta-full message nicely. If `error` contains "closed beta":
```javascript
const errorEl = document.querySelector('.error-message');
if (errorEl && errorEl.textContent.includes('closed beta')) {
  errorEl.style.background = 'linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.1))';
  errorEl.style.borderColor = '#667eea';
  errorEl.innerHTML = `
    <div style="font-size:1.5rem; margin-bottom:0.5rem;">🚀</div>
    <strong>SpecForge AI is in closed beta</strong><br>
    All 10 spots are currently taken. Join our waitlist to be notified when we open up!<br>
    <a href="/home#contact" style="color:#667eea; margin-top:0.5rem; display:inline-block;">
      → Join Waitlist
    </a>
  `;
}
```

---

## F10 — Add Quota CSS Styles

**File:** `srs_engine/static/site.css`

**Add at the end:**
```css
/* Quota banners */
.quota-banner {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  margin-bottom: 1rem;
  background: rgba(102, 126, 234, 0.08);
  border: 1px solid rgba(102, 126, 234, 0.2);
  color: var(--text-secondary);
}
.quota-exhausted {
  background: rgba(244, 67, 54, 0.08);
  border-color: rgba(244, 67, 54, 0.2);
  color: #ef5350;
}
.file-notice {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(255, 183, 77, 0.08);
  border-radius: 6px;
}
.coming-soon-badge {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}
```

---

## Frontend Test Checklist (After F10)

```
□ Landing page shows "SpecForge AI" branding
□ Upload Upgrader not in nav (Coming Soon badge instead)
□ Landing page tool card shows Coming Soon overlay
□ /srs-upgrader shows premium Coming Soon page
□ SRS Generator shows "General SRS" info banner
□ SRS Generator shows quota: "2 of 2 remaining"
□ After 2 SRS: submit button disabled, quota banner red
□ Diagram Studio shows per-project quota
□ Section Upgrader shows per-project quota
□ Job Tracker shows queue position for pending jobs
□ Job Tracker shows "download now" warning
□ Login page shows friendly "beta full" message
□ All pages render correctly at 375px (mobile)
□ All pages render correctly at 768px (tablet)
```
