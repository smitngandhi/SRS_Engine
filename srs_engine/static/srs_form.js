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

/* ══════════════════════════════════════════════════════
   VALIDATION CONFIG
   Each step lists its required fields:
     label     — human-readable name shown in error messages
     passes()  — returns truthy if the field is filled
     highlight — returns the element(s) to outline red
   Step 6 is fully optional (empty array).
═══════════════════════════════════════════════════════ */
const STEP_VALIDATIONS = {
  1: [
    {
      label:     'Project Name',
      passes:    () => !!document.getElementById('project_name')?.value.trim(),
      highlight: () => [document.getElementById('project_name')],
    },
    {
      label:     'Author(s)',
      passes:    () => !!document.getElementById('author')?.value.trim(),
      highlight: () => [document.getElementById('author')],
    },
    {
      label:     'Organization',
      passes:    () => !!document.getElementById('organization')?.value.trim(),
      highlight: () => [document.getElementById('organization')],
    },
    {
      label:     'Problem Statement',
      passes:    () => !!document.getElementById('problem_statement')?.value.trim(),
      highlight: () => [document.getElementById('problem_statement')],
    },
    {
      label:     'Target Users (select at least one)',
      passes:    () => document.querySelectorAll('input[name="target_users"]:checked').length > 0,
      highlight: () => [document.getElementById('targetUsersGroup')],
    },
  ],
  2: [
    {
      label:     'Application Type',
      passes:    () => !!document.getElementById('application_type')?.value,
      highlight: () => [document.getElementById('application_type')],
    },
    {
      label:     'Domain / Industry',
      passes:    () => !!document.getElementById('domain')?.value,
      highlight: () => [document.getElementById('domain')],
    },
    {
      label:     'Domain is coming soon (Please select "General")',
      passes:    () => document.getElementById('domain')?.value === 'Other' || document.getElementById('domain')?.value === '',
      highlight: () => [document.getElementById('domain')],
    },
  ],
  3: [
    {
      label:     'Core Features',
      passes:    () => !!document.getElementById('core_features')?.value.trim(),
      highlight: () => [document.getElementById('core_features')],
    },
  ],
  4: [
    {
      label:     'Expected User Scale',
      passes:    () => !!document.getElementById('expected_user_scale')?.value,
      highlight: () => [document.getElementById('expected_user_scale')],
    },
    {
      label:     'Performance Expectation',
      passes:    () => !!document.getElementById('performance_expectation')?.value,
      highlight: () => [document.getElementById('performance_expectation')],
    },
  ],
  5: [
    {
      label:     'Authentication Required',
      passes:    () => !!document.querySelector('input[name="authentication_required"]:checked'),
      highlight: () => [document.querySelector('.radio-group:has(input[name="authentication_required"])')],
    },
    {
      label:     'Handles Sensitive Data',
      passes:    () => !!document.querySelector('input[name="sensitive_data_handling"]:checked'),
      highlight: () => [document.querySelector('.radio-group:has(input[name="sensitive_data_handling"])')],
    },
  ],
  6: [], // all optional
  7: [
    {
      label:     'SRS Detail Level',
      passes:    () => !!document.querySelector('input[name="srs_detail_level"]:checked'),
      highlight: () => [document.getElementById('detailCards')],
    },
  ],
};

/* ── Validate a single step → array of failing rules ─────────── */
function validateStep(n) {
  return (STEP_VALIDATIONS[n] || []).filter(rule => !rule.passes());
}

/* ── Validate every step → { step, label }[] ─────────────────── */
function validateAll() {
  const issues = [];
  for (let n = 1; n <= TOTAL_STEPS; n++) {
    validateStep(n).forEach(rule => issues.push({ step: n, label: rule.label }));
  }
  return issues;
}

/* ── Error banner (created once, reused) ──────────────────────── */
let _errorBanner = null;
function getErrorBanner() {
  if (_errorBanner) return _errorBanner;
  _errorBanner = document.createElement('div');
  _errorBanner.id = 'stepErrorBanner';
  _errorBanner.className = 'step-error-banner';
  const controls = document.querySelector('.step-controls');
  if (controls) controls.insertBefore(_errorBanner, controls.firstChild);
  return _errorBanner;
}

function showStepErrors(failedRules) {
  const banner = getErrorBanner();

  // Highlight failing fields
  clearFieldHighlights();
  failedRules.forEach(rule => {
    rule.highlight().forEach(el => el?.classList.add('field-error'));
  });

  // Build pill list of missing field names
  const pills = failedRules
    .map(r => `<span class="err-pill">${r.label}</span>`)
    .join('');
  banner.innerHTML = `<span class="err-icon">⚠</span><span>Please complete: ${pills}</span>`;
  banner.classList.add('visible');

  // Shake the active action button
  const activeBtn = currentStep === TOTAL_STEPS ? submitBtn : nextBtn;
  activeBtn.classList.remove('btn-shake');
  void activeBtn.offsetWidth; // force reflow
  activeBtn.classList.add('btn-shake');
}

function clearStepErrors() {
  clearFieldHighlights();
  const banner = getErrorBanner();
  banner.classList.remove('visible');
  banner.innerHTML = '';
}

function clearFieldHighlights() {
  document.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
}

// Clear errors the moment the user starts typing / changing anything
document.getElementById('srsForm')?.addEventListener('input',  clearStepErrors);
document.getElementById('srsForm')?.addEventListener('change', clearStepErrors);

/* ══════════════════════════════════════════════════════
   STEP NAVIGATION
═══════════════════════════════════════════════════════ */
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
  clearStepErrors();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Next button: validate current step first ─────────────────── */
nextBtn.addEventListener('click', () => {
  const errors = validateStep(currentStep);
  if (errors.length) {
    showStepErrors(errors);
    return;
  }
  goToStep(currentStep + 1);
});

/* ── Back button: always allowed ──────────────────────────────── */
prevBtn.addEventListener('click', () => {
  clearStepErrors();
  goToStep(currentStep - 1);
});

/* ── Sidebar step buttons: block jumping forward past invalid steps */
stepBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const target = parseInt(btn.dataset.step);

    // Going back is always fine
    if (target <= currentStep) {
      clearStepErrors();
      goToStep(target);
      return;
    }

    // Validate every step between current and target
    for (let n = currentStep; n < target; n++) {
      const errors = validateStep(n);
      if (errors.length) {
        goToStep(n);
        requestAnimationFrame(() => showStepErrors(errors));
        return;
      }
    }
    goToStep(target);
  });
});

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

  const isGeneral = (key === 'Other');
  const comingSoonBadge = !isGeneral ? 
    '<span style="margin-left:auto; background:#ff9800; color:#fff; font-size:0.7rem; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold; vertical-align:middle;">COMING SOON</span>' : '';

  document.getElementById('domainTitle').innerHTML =
    `<div style="display:flex; align-items:center;"><span style="margin-right:8px">${d.icon}</span>${d.title} ${comingSoonBadge}</div>`;

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

  const comingSoonNote = !isGeneral ? 
    `<div style="margin-top:1rem; padding:0.75rem; background:rgba(255,183,77,0.1); border:1px solid rgba(255,183,77,0.3); border-radius:8px; color:var(--text); text-align:center;">
       <strong>Coming Soon:</strong> SRS Generation for ${d.title} is currently in development. You can preview the sections above, but please select <strong>General</strong> to generate a document today.
     </div>` : '';

  document.getElementById('infoNote').innerHTML = (d.note || '') + comingSoonNote;

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

/* ══════════════════════════════════════════════════════
   AI BUTTON STATE
═══════════════════════════════════════════════════════ */
const projectNameInput = document.getElementById('project_name');
const problemInput     = document.getElementById('problem_statement');
const enhanceBtn       = document.getElementById('enhanceProblemBtn');
const autoFeaturesBtn  = document.getElementById('autoGenerateFeaturesBtn');
const autoFlowBtn      = document.getElementById('autoGenerateFlowBtn');
const autoConstraintsBtn = document.getElementById('autoGenerateConstraintsBtn');
const autoAssumptionsBtn = document.getElementById('autoGenerateAssumptionsBtn');

function checkBtns() {
  const name   = (document.getElementById('project_name')?.value.trim().length ?? 0) > 0;
  const prob   = (document.getElementById('problem_statement')?.value.trim().length ?? 0) > 0;
  const bothOk = name && prob;

  if (enhanceBtn)      { enhanceBtn.disabled      = !bothOk; enhanceBtn.style.opacity      = bothOk ? '1' : '0.35'; }
  if (autoFeaturesBtn) { autoFeaturesBtn.disabled  = !bothOk; autoFeaturesBtn.style.opacity  = bothOk ? '1' : '0.35'; }
  if (autoFlowBtn)     { autoFlowBtn.disabled      = !bothOk; autoFlowBtn.style.opacity      = bothOk ? '1' : '0.35'; }
  if (autoConstraintsBtn){ autoConstraintsBtn.disabled = !bothOk; autoConstraintsBtn.style.opacity = bothOk ? '1' : '0.35'; }
  if (autoAssumptionsBtn){ autoAssumptionsBtn.disabled = !bothOk; autoAssumptionsBtn.style.opacity = bothOk ? '1' : '0.35'; }
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
    checkBtns();
  }
}

/* ── AI button listeners ────────────────────────────── */
enhanceBtn?.addEventListener('click', () => aiCall(
  '/enhance-problem-statement',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim() },
  document.getElementById('problemStatus'), enhanceBtn, '✨ Enhance',
  d => {
    if (d.enhanced_problem_statement) {
      problemInput.value = d.enhanced_problem_statement;
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
    }
  }
));

autoConstraintsBtn?.addEventListener('click', () => aiCall(
  '/auto-generate-section',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim(), section_type: 'constraints' },
  document.getElementById('constraintsStatus'), autoConstraintsBtn, '✨ Auto-Generate',
  d => {
    if (d.system_constraints) {
      document.getElementById('system_constraints').value = d.system_constraints;
    }
  }
));

autoAssumptionsBtn?.addEventListener('click', () => aiCall(
  '/auto-generate-section',
  { project_name: projectNameInput.value.trim(), problem_statement: problemInput.value.trim(), section_type: 'assumptions' },
  document.getElementById('assumptionsStatus'), autoAssumptionsBtn, '✨ Auto-Generate',
  d => {
    if (d.key_assumptions) {
      document.getElementById('key_assumptions').value = d.key_assumptions;
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
    { label: 'Constraints',  id: 'system_constraints' },
    { label: 'Backend',      id: 'preferred_backend' },
    { label: 'Database',     id: 'database_preference' },
  ];
  
  const getChecked = (name) => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(el => el.value);
  
  let html = fields.map(f => {
    const val = document.getElementById(f.id)?.value?.trim() || '—';
    return `<div class="review-item">
      <span class="review-item-label">${f.label}</span>
      <span class="review-item-value">${val}</span>
    </div>`;
  }).join('');
  
  const envChecked = getChecked('operating_environment');
  html += `<div class="review-item">
      <span class="review-item-label">Environment</span>
      <span class="review-item-value">${envChecked.length ? envChecked.join(', ') : '—'}</span>
    </div>`;
    
  grid.innerHTML = html;
}

/* ── Persist form across login redirect ────────────── */
const PERSIST_FIELDS = [
  'project_name', 'organization', 'problem_statement',
  'core_features', 'primary_user_flow', 'application_type', 'domain',
  'system_constraints', 'key_assumptions'
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
  } catch (e) {
    sessionStorage.removeItem('srs_form_draft');
  }
}

document.getElementById('srsForm')?.addEventListener('input',  saveFormState);
document.getElementById('srsForm')?.addEventListener('change', saveFormState);

restoreFormState();
requestAnimationFrame(() => requestAnimationFrame(checkBtns));

/* ══════════════════════════════════════════════════════
   FORM SUBMISSION — validates every step before sending
═══════════════════════════════════════════════════════ */
document.getElementById('srsForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();

  // ── Full-form validation ──────────────────────────
  const allIssues = validateAll();
  if (allIssues.length) {
    // Jump to the first step that has errors
    const firstFailStep = allIssues[0].step;
    goToStep(firstFailStep);
    requestAnimationFrame(() => {
      const stepErrors = STEP_VALIDATIONS[firstFailStep].filter(r => !r.passes());
      showStepErrors(stepErrors);
    });
    return;
  }

  // ── Build payload ─────────────────────────────────
  const formData = new FormData(e.target);

  const getChecked = (name) =>
    Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(el => el.value).filter(v => v !== 'Other');

  const splitArr = (val) =>
    val ? val.split(/[\n,]/).map(v => v.trim()).filter(Boolean) : [];

  const targetUsers = getChecked('target_users');
  const customUser  = document.getElementById('target_users_custom')?.value.trim();
  if (customUser) targetUsers.push(customUser);

  let domain = formData.get('domain');
  if (domain === 'Other') {
    const customDomain = document.getElementById('domain_custom')?.value.trim();
    if (customDomain) domain = customDomain;
  }

  const compliance   = getChecked('compliance_requirements');
  const customCompli = document.getElementById('compliance_custom')?.value.trim();
  if (customCompli) compliance.push(customCompli);

  const authors      = splitArr(formData.get('author'));
  const coreFeatures = splitArr(formData.get('core_features'));
  const operatingEnv = getChecked('operating_environment');

  const payload = {
    project_identity: {
      project_name:      formData.get('project_name')?.trim(),
      author:            authors,
      organization:      formData.get('organization')?.trim(),
      problem_statement: formData.get('problem_statement')?.trim(),
      target_users:      targetUsers,
    },
    system_context: {
      application_type: formData.get('application_type'),
      domain,
    },
    functional_scope: {
      core_features:     coreFeatures,
      primary_user_flow: formData.get('primary_user_flow')?.trim() || null,
    },
    non_functional_requirements: {
      expected_user_scale:     formData.get('expected_user_scale'),
      performance_expectation: formData.get('performance_expectation'),
      key_assumptions:         formData.get('key_assumptions')?.trim() || null,
      system_constraints:      formData.get('system_constraints')?.trim() || null,
    },
    security_and_compliance: {
      authentication_required: formData.get('authentication_required') === 'true',
      sensitive_data_handling: formData.get('sensitive_data_handling') === 'true',
      compliance_requirements: compliance,
    },
    technical_preferences: {
      preferred_backend:     formData.get('preferred_backend')?.trim()     || null,
      database_preference:   formData.get('database_preference')?.trim()   || null,
      deployment_preference: formData.get('deployment_preference')?.trim() || null,
      operating_environment: operatingEnv,
    },
    output_control: {
      srs_detail_level: formData.get('srs_detail_level'),
    },
  };

  // ── Submit ────────────────────────────────────────
  const origText = submitBtn.textContent;
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

    await res.json();
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