/* ── Scroll-reveal ──────────────────────────────────── */
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
);

document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach((el) => {
  revealObserver.observe(el);
});

/* ── Sticky header shadow on scroll ─────────────────── */
const header = document.querySelector('.site-header');
if (header) {
  const onScroll = () => {
    header.classList.toggle('scrolled', window.scrollY > 24);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/* ── Active nav link on scroll ───────────────────────── */
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav a[href*="#"]');

if (sections.length && navLinks.length) {
  const navObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          navLinks.forEach((link) => {
            link.classList.toggle(
              'active',
              link.getAttribute('href').endsWith(`#${entry.target.id}`)
            );
          });
        }
      });
    },
    { threshold: 0.4 }
  );
  sections.forEach((s) => navObserver.observe(s));
}

/* ── FAQ accordion ───────────────────────────────────── */
document.querySelectorAll('.faq-question').forEach((btn) => {
  btn.addEventListener('click', () => {
    const item = btn.closest('.faq-item');
    const isOpen = item.classList.contains('open');

    // Close all
    document.querySelectorAll('.faq-item.open').forEach((openItem) => {
      openItem.classList.remove('open');
      openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
    });

    // Toggle clicked
    if (!isOpen) {
      item.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');
    }
  });
});

/* ── Contact form (AJAX) ─────────────────────────────── */
const contactForm = document.getElementById('contactForm');
if (contactForm) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const status = document.getElementById('contactStatus');

    // Honeypot check
    if (contactForm.querySelector('[name="website"]')?.value) return;

    const data = Object.fromEntries(new FormData(contactForm));
    status.textContent = 'Sending…';
    status.style.color = 'var(--muted)';

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        status.textContent = '✓ Message sent! We\'ll get back to you soon.';
        status.style.color = 'var(--accent)';
        contactForm.reset();
      } else {
        throw new Error('Server error');
      }
    } catch {
      status.textContent = 'Something went wrong. Please try again.';
      status.style.color = '#ff8080';
    }
  });
}

/* ── Smooth-scroll for internal anchors ──────────────── */
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener('click', (e) => {
    const target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});


/* ── My Documents loader ────────────────────────────── */
async function loadDocuments() {
  const grid  = document.getElementById('docsGrid');
  const empty = document.getElementById('docsEmpty');
  const error = document.getElementById('docsError');
  if (!grid) return; // not logged in, section not in DOM

  error.style.display = 'none';

  try {
    const res  = await fetch('/api/my-documents');
    if (!res.ok) throw new Error(res.statusText);
    const docs = await res.json();

    // clear skeletons
    grid.innerHTML = '';

    if (!docs.length) {
      empty.style.display = 'block';
      return;
    }

    docs.forEach((doc, i) => {
      const date = new Date(doc.created_at * 1000).toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric'
      });

      const card = document.createElement('div');
      card.className = `doc-card reveal delay-${(i % 3) + 1}`;
      card.innerHTML = `
        <div class="doc-icon">📋</div>
        <div class="doc-name">${escHtml(doc.project_name)}</div>
        <div class="doc-meta">
          <span class="doc-domain">${escHtml(doc.domain || 'General')}</span>
          <span class="doc-date">${date}</span>
          <span class="doc-size">${doc.size_kb} KB</span>
        </div>
        <div class="doc-actions">
          <a class="btn-action btn-primary" href="/srs-section-upgrader?project_id=${escHtml(doc.id)}">
            ✨ Upgrade
          </a>
          <a class="btn-action btn-secondary" href="/srs-history?project_id=${escHtml(doc.id)}">
            🕒 History
          </a>
          <a class="btn-action btn-download" href="/api/download-srs/${escHtml(doc.id)}" download title="Download .docx">
            ⬇
          </a>
        </div>
      `;
      grid.appendChild(card);

      // plug into existing reveal observer
      revealObserver.observe(card);
    });

  } catch (err) {
    grid.innerHTML = '';
    error.style.display = 'block';
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
  loadDocuments();
  loadDiagrams();
  
  // Live updates: refresh lists every 30 seconds
  setInterval(() => {
    loadDocuments();
    loadDiagrams();
  }, 30000);
});

/* ── My Diagrams loader ─────────────────────────────── */
const DIAGRAM_TYPE_ICONS = {
  flowchart: '🔀', sequence: '🔁', erd: '🗄️', class: '🏛️', custom: '✨',
};

async function loadDiagrams() {
  const grid  = document.getElementById('diagramsGrid');
  const empty = document.getElementById('diagramsEmpty');
  if (!grid) return; // not on home page / not logged in

  try {
    const res = await fetch('/api/diagrams/recent');
    if (!res.ok) throw new Error(res.statusText);
    const diagrams = await res.json();

    grid.innerHTML = '';

    if (!diagrams.length) {
      if (empty) empty.style.display = 'block';
      return;
    }

    if (empty) empty.style.display = 'none';

    diagrams.forEach((d, i) => {
      const current = d.current_version;
      const date = new Date(d.updated_at).toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric',
      });
      const icon = DIAGRAM_TYPE_ICONS[d.diagram_type] || '🗺️';
      const hasThumb = current && current.svg_path;
      const thumbHtml = hasThumb
        ? `<img src="${escHtml(current.svg_path)}?t=${Date.now()}" alt="diagram preview" loading="lazy" />`
        : icon;

      const card = document.createElement('a');
      card.className = `diagram-card reveal delay-${(i % 3) + 1}`;
      card.href = `/diagrams`;
      card.innerHTML = `
        <div class="diagram-preview-thumb">${thumbHtml}</div>
        <div class="diagram-name">${escHtml(d.project_name)}</div>
        <div class="diagram-meta">
          <span class="diagram-type-badge">${escHtml(d.diagram_type)}</span>
          <span class="diagram-versions-count">${d.versions.length} version${d.versions.length !== 1 ? 's' : ''}</span>
          <span class="doc-date">${date}</span>
        </div>
      `;
      grid.appendChild(card);
      revealObserver.observe(card);
    });

  } catch (err) {
    // Silently fail — section just stays hidden
    console.warn('loadDiagrams error:', err);
  }
}