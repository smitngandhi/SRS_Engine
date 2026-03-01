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
          <a class="btn btn-secondary" href="/api/download-srs/${escHtml(doc.id)}" download>
            ⬇ Download
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

document.addEventListener('DOMContentLoaded', loadDocuments);