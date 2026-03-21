const TOTAL_STEPS = 7;
let currentStep = 1;

const steps         = document.querySelectorAll('.form-step');
const stepBtns      = document.querySelectorAll('.step-btn');
const nextBtn       = document.getElementById('nextBtn');
const prevBtn       = document.getElementById('prevBtn');
const submitBtn     = document.getElementById('submitBtn');
const progressFill  = document.getElementById('progressFill');
const progressLabel = document.getElementById('progressLabel');
const stepDotsEl    = document.getElementById('stepDots');

function buildDots() {
  stepDotsEl.innerHTML = '';
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const d = document.createElement('div');
    d.className = 'step-dot' + (i === currentStep ? ' active' : i < currentStep ? ' completed' : '');
    stepDotsEl.appendChild(d);
  }
}

function goToStep(n) {
  if (n < 1 || n > TOTAL_STEPS) return;
  steps.forEach(s => s.classList.remove('active'));
  document.querySelector(`.form-step[data-step="${n}"]`)?.classList.add('active');
  stepBtns.forEach(btn => {
    const s = parseInt(btn.dataset.step);
    btn.classList.toggle('active', s === n);
    btn.classList.toggle('completed', s < n);
  });
  currentStep = n;
  prevBtn.style.display   = n > 1 ? 'inline-flex' : 'none';
  nextBtn.style.display   = n < TOTAL_STEPS ? 'inline-flex' : 'none';
  submitBtn.style.display = n === TOTAL_STEPS ? 'inline-flex' : 'none';
  progressFill.style.width = ((n / TOTAL_STEPS) * 100) + '%';
  progressLabel.textContent = `Step ${n} of ${TOTAL_STEPS}`;
  buildDots();
  if (n === TOTAL_STEPS) buildReview();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

nextBtn.addEventListener('click', () => goToStep(currentStep + 1));
prevBtn.addEventListener('click', () => goToStep(currentStep - 1));
stepBtns.forEach(btn => btn.addEventListener('click', () => goToStep(parseInt(btn.dataset.step))));
goToStep(1);

/* ── Domain panel ──────────────────────────────────── */
const domainSelect      = document.getElementById('domain');
const domainInfoSection = document.getElementById('domainInfoSection');
const domainCustomInput = document.getElementById('domain_custom');

domainSelect?.addEventListener('change', function () {
  const val = this.value;
  domainCustomInput.style.display = val === 'Other' ? 'block' : 'none';
  if (val && typeof domainData !== 'undefined' && domainData[val]) {
    renderDomainPanel(val);
    domainInfoSection.style.display = 'block';
  } else {
    domainInfoSection.style.display = 'none';
  }
});

function renderDomainPanel(key) {
  const d = domainData[key];
  if (!d) return;

  document.getElementById('domainTitle').innerHTML =
    `<span style="margin-right:8px">${d.icon}</span>${d.title}`;

  document.getElementById('standardsList').innerHTML = d.standards.map(s => {
    const desc = d.standardDescriptions?.[s] || '';
    return `<span class="standard-badge" data-tooltip="${desc}">${s}</span>`;
  }).join('');

  const secList = document.getElementById('sectionsList');
  secList.innerHTML = d.sections.map(sec => renderSection(sec)).join('');
  secList.querySelectorAll('.sec-toggle').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.section-accordion-item').classList.toggle('open'));
  });

  const commonEl = document.getElementById('commonSectionsList');
  if (commonEl && typeof commonSections !== 'undefined') {
    commonEl.innerHTML = commonSections.map(s =>
      `<div class="common-section-item">
        <span class="common-sec-num">§${s.number}</span>
        <span>${s.title}</span>
      </div>`).join('');
  }

  document.getElementById('infoNote').textContent = d.note;

  document.getElementById('standardsList').querySelectorAll('[data-tooltip]').forEach(el => {
    el.addEventListener('mouseenter', showTooltip);
    el.addEventListener('mouseleave', hideTooltip);
  });
}

function renderSection(sec) {
  const hasSubs     = Array.isArray(sec.subsections) && sec.subsections.length > 0;
  const hasIncludes = Array.isArray(sec.includes) && sec.includes.length > 0;
  const hasDetails  = hasSubs || hasIncludes || sec.what || sec.why;

  if (!hasDetails) {
    return `<div class="section-item-simple">
      <span class="sec-num-badge">${sec.number}</span><span>${sec.title}</span>
    </div>`;
  }

  const subsHTML = hasSubs ? sec.subsections.map(sub => `
    <div class="subsection-item">
      <div class="subsec-header">
        <span class="subsec-num">${sub.id}</span>
        <span class="subsec-title">${sub.title}</span>
      </div>
      ${sub.what ? `<div class="subsec-meta"><strong>What:</strong> ${sub.what}</div>` : ''}
      ${sub.why  ? `<div class="subsec-meta"><strong>Why:</strong> ${sub.why}</div>`  : ''}
      ${Array.isArray(sub.includes) && sub.includes.length ? `<ul class="subsec-includes">${sub.includes.map(i => `<li>${i}</li>`).join('')}</ul>` : ''}
    </div>`).join('') : '';

  const incHTML = hasIncludes && !hasSubs
    ? `<ul class="sec-includes">${sec.includes.map(i => `<li>${i}</li>`).join('')}</ul>` : '';

  const wwHTML = !hasSubs && (sec.what || sec.why)
    ? `${sec.what ? `<div class="sec-meta"><strong>What:</strong> ${sec.what}</div>` : ''}
       ${sec.why  ? `<div class="sec-meta"><strong>Why:</strong> ${sec.why}</div>`  : ''}` : '';

  return `<div class="section-accordion-item">
    <button class="sec-toggle" type="button">
      <span class="sec-num-badge">${sec.number}</span>
      <span class="sec-toggle-title">${sec.title}</span>
      <span class="sec-chevron">▾</span>
    </button>
    <div class="sec-content">${wwHTML}${incHTML}${subsHTML}</div>
  </div>`;
}

/* ── Tooltip ───────────────────────────────────────── */
let _tip = null;
function showTooltip(e) {
  const text = e.currentTarget.dataset.tooltip;
  if (!text) return;
  _tip = document.createElement('div');
  _tip.className = 'srs-tooltip';
  _tip.textContent = text;
  document.body.appendChild(_tip);
  const r = e.currentTarget.getBoundingClientRect();
  _tip.style.left = r.left + window.scrollX + 'px';
  _tip.style.top  = r.bottom + window.scrollY + 8 + 'px';
}
function hideTooltip() { _tip?.remove(); _tip = null; }

/* ── Other checkboxes ──────────────────────────────── */
document.getElementById('target_users_other_check')?.addEventListener('change', function () {
  document.getElementById('target_users_custom').style.display = this.checked ? 'block' : 'none';
});
document.getElementById('compliance_other_check')?.addEventListener('change', function () {
  document.getElementById('compliance_custom').style.display = this.checked ? 'block' : 'none';
});

/* ── AI button state ───────────────────────────────── */
const projectNameInput = document.getElementById('project_name');
const problemInput     = document.getElementById('problem_statement');
const enhanceBtn       = document.getElementById('enhanceProblemBtn');
const autoFeaturesBtn  = document.getElementById('autoGenerateFeaturesBtn');
const autoFlowBtn      = document.getElementById('autoGenerateFlowBtn');

let enhanceDone = false; // unlocks auto buttons even if user didn't manually type problem

function checkBtns() {
  // Always re-read from DOM so restored/programmatic values are picked up
  const name   = (document.getElementById('project_name')?.value.trim().length ?? 0) > 0;
  const prob   = (document.getElementById('problem_statement')?.value.trim().length ?? 0) > 0;
  const autoOk = name && (prob || enhanceDone);

  if (enhanceBtn)      { enhanceBtn.disabled     = !name;   enhanceBtn.style.opacity     = name   ? '1' : '0.35'; }
  if (autoFeaturesBtn) { autoFeaturesBtn.disabled = !autoOk; autoFeaturesBtn.style.opacity = autoOk ? '1' : '0.35'; }
  if (autoFlowBtn)     { autoFlowBtn.disabled     = !autoOk; autoFlowBtn.style.opacity     = autoOk ? '1' : '0.35'; }
}

projectNameInput?.addEventListener('input', checkBtns);
problemInput?.addEventListener('input', checkBtns);

/* ── AI helper ─────────────────────────────────────── */
async function aiCall(url, body, statusEl, btn, label, onSuccess) {
  btn.disabled = true;
  btn.textContent = '⏳ Working...';
  statusEl.textContent = 'Thinking...';
  statusEl.style.color = 'var(--muted)';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.status === 401) {
      statusEl.textContent = '⚠ Please log in first.';
      statusEl.style.color = '#ff8080';
      return;
    }
    if (!res.ok) throw new Error();
    onSuccess(await res.json());
    statusEl.textContent = '✓ Done!';
    statusEl.style.color = 'var(--accent)';
  } catch {
    statusEl.textContent = 'Failed. Please try again.';
    statusEl.style.color = '#ff8080';
  } finally {
    btn.disabled = false;
    btn.textContent = label;
  }
}

/* ── AI button listeners (each defined exactly once) ── */
enhanceBtn?.addEventListener('click', () => aiCall(
  '/enhance-problem-statement',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim() },
  document.getElementById('problemStatus'), enhanceBtn, '✨ Enhance',
  d => {
    if (d.enhanced_problem_statement) {
      problemInput.value = d.enhanced_problem_statement;
      enhanceDone = true; // unlock auto buttons even if user never typed in problem field
      checkBtns();
    }
  }
));

autoFeaturesBtn?.addEventListener('click', () => aiCall(
  '/auto-generate-section',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim(), section_type: 'features' },
  document.getElementById('featuresStatus'), autoFeaturesBtn, '✨ Auto-Generate',
  d => {
    if (d.core_features) {
      document.getElementById('core_features').value =
        Array.isArray(d.core_features) ? d.core_features.join('\n') : d.core_features;
      checkBtns();
    }
  }
));

autoFlowBtn?.addEventListener('click', () => aiCall(
  '/auto-generate-section',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim(), section_type: 'flow' },
  document.getElementById('flowStatus'), autoFlowBtn, '✨ Auto-Generate',
  d => {
    if (d.primary_user_flow) {
      document.getElementById('primary_user_flow').value = d.primary_user_flow;
      checkBtns();
    }
  }
));

/* ── Review panel ──────────────────────────────────── */
function buildReview() {
  const grid = document.getElementById('reviewGrid');
  if (!grid) return;
  const fields = [
    { label: 'Project',      id: 'project_name' },
    { label: 'Organization', id: 'organization' },
    { label: 'App Type',     id: 'application_type' },
    { label: 'Domain',       id: 'domain' },
    { label: 'User Scale',   id: 'expected_user_scale' },
    { label: 'Performance',  id: 'performance_expectation' },
    { label: 'Backend',      id: 'preferred_backend' },
    { label: 'Database',     id: 'database_preference' },
  ];
  grid.innerHTML = fields.map(f => {
    const val = document.getElementById(f.id)?.value?.trim() || '—';
    return `<div class="review-item">
      <span class="review-item-label">${f.label}</span>
      <span class="review-item-value">${val}</span>
    </div>`;
  }).join('');
}

/* ── Persist form across login redirect ────────────── */
const PERSIST_FIELDS = [
  'project_name', 'organization', 'problem_statement',
  'core_features', 'primary_user_flow', 'application_type', 'domain',
];

function saveFormState() {
  const data = {};
  PERSIST_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) data[id] = el.value;
  });
  sessionStorage.setItem('srs_form_draft', JSON.stringify(data));
}

function restoreFormState() {
  const saved = sessionStorage.getItem('srs_form_draft');
  if (!saved) return;
  try {
    const data = JSON.parse(saved);
    PERSIST_FIELDS.forEach(id => {
      const el = document.getElementById(id);
      if (el && data[id]) el.value = data[id];
    });
    // if problem statement was restored, treat it as if user typed it
    const prob = document.getElementById('problem_statement')?.value.trim();
    if (prob && prob.length > 0) enhanceDone = true;
  } catch (e) {
    sessionStorage.removeItem('srs_form_draft');
  }
}

// Save on every interaction
document.getElementById('srsForm')?.addEventListener('input',  saveFormState);
document.getElementById('srsForm')?.addEventListener('change', saveFormState);

// Restore values, then check buttons after two paint frames so DOM is settled
restoreFormState();
requestAnimationFrame(() => requestAnimationFrame(checkBtns));


/* ── Form submission ───────────────────────────────── */
document.getElementById('srsForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);

  // helpers
  const getChecked = (name) =>
    Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(el => el.value).filter(v => v !== 'Other');

  const splitArr = (val) =>
    val ? val.split(/[\n,]/).map(v => v.trim()).filter(Boolean) : [];

  // target users
  const targetUsers = getChecked('target_users');
  const customUser  = document.getElementById('target_users_custom')?.value.trim();
  if (customUser) targetUsers.push(customUser);
  if (!targetUsers.length) { alert('Please select at least one target user.'); return; }

  // domain
  let domain = formData.get('domain');
  if (domain === 'Other') {
    const customDomain = document.getElementById('domain_custom')?.value.trim();
    if (customDomain) domain = customDomain;
  }

  // compliance
  const compliance    = getChecked('compliance_requirements');
  const customCompli  = document.getElementById('compliance_custom')?.value.trim();
  if (customCompli) compliance.push(customCompli);

  // authors & features
  const authors      = splitArr(formData.get('author'));
  const coreFeatures = splitArr(formData.get('core_features'));
  if (!authors.length)      { alert('Please provide at least one author.');       return; }
  if (!coreFeatures.length) { alert('Please provide at least one core feature.'); return; }

  const payload = {
    project_identity: {
      project_name:       formData.get('project_name')?.trim(),
      author:             authors,
      organization:       formData.get('organization')?.trim(),
      problem_statement:  formData.get('problem_statement')?.trim(),
      target_users:       targetUsers,
    },
    system_context: {
      application_type: formData.get('application_type'),
      domain:           domain,
    },
    functional_scope: {
      core_features:      coreFeatures,
      primary_user_flow:  formData.get('primary_user_flow')?.trim() || null,
    },
    non_functional_requirements: {
      expected_user_scale:     formData.get('expected_user_scale'),
      performance_expectation: formData.get('performance_expectation'),
    },
    security_and_compliance: {
      authentication_required: formData.get('authentication_required') === 'true',
      sensitive_data_handling: formData.get('sensitive_data_handling') === 'true',
      compliance_requirements: compliance,
    },
    technical_preferences: {
      preferred_backend:    formData.get('preferred_backend')?.trim()    || null,
      database_preference:  formData.get('database_preference')?.trim()  || null,
      deployment_preference: formData.get('deployment_preference')?.trim() || null,
    },
    output_control: {
      srs_detail_level: formData.get('srs_detail_level'),
    },
  };
  
  
  const submitBtn = document.getElementById('submitBtn');
  const origText  = submitBtn.textContent;
  submitBtn.disabled    = true;
  submitBtn.textContent = '⏳ Generating SRS...';

  try {
    const res = await fetch('/generate_srs', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    if (res.status === 401) {
      alert('Please log in to generate an SRS.');
      window.location.href = '/login';
      return;
    }
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Server error ${res.status}: ${err}`);
    }

    const result = await res.json();
    console.log('SRS generated:', result);

    // Clear saved draft on success
    sessionStorage.removeItem('srs_form_draft');
    window.location.href = '/jobs';

  } catch (err) {
    console.error('Submission error:', err);
    alert(`❌ Failed to generate SRS: ${err.message}`);
  } finally {
    submitBtn.disabled    = false;
    submitBtn.textContent = origText;
  }
});