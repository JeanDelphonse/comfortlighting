/**
 * ComfortLighting – AI Agent Autofill
 * Handles the Research button on the Add Lead form:
 *   1. POST to /leads/research
 *   2. Animate a progress bar while waiting
 *   3. Populate form fields with agent results
 *   4. Render confidence badges on each filled field
 *   5. Show the Research Summary panel
 */
(function () {
  'use strict';

  // ── Progress messages ────────────────────────────────────────────────────────
  const STEPS = [
    { pct: 10,  msg: 'Searching the web for company information…' },
    { pct: 25,  msg: 'Analyzing company profile and facility data…' },
    { pct: 45,  msg: 'Searching for contact information…' },
    { pct: 60,  msg: 'Retrieving financial intelligence…' },
    { pct: 75,  msg: 'Calculating LED retrofit ROI…' },
    { pct: 88,  msg: 'Synthesizing findings and mapping fields…' },
    { pct: 95,  msg: 'Populating form fields…' },
  ];

  let stepInterval = null;
  let currentStep  = 0;

  function startProgress() {
    const bar  = document.getElementById('research-progress-bar');
    const text = document.getElementById('research-status-text');
    document.getElementById('research-progress').style.display = '';
    currentStep = 0;

    function tick() {
      if (currentStep < STEPS.length) {
        bar.style.width  = STEPS[currentStep].pct + '%';
        text.textContent = STEPS[currentStep].msg;
        currentStep++;
      }
    }
    tick();
    stepInterval = setInterval(tick, 5000);
  }

  function stopProgress(success) {
    clearInterval(stepInterval);
    const bar  = document.getElementById('research-progress-bar');
    const text = document.getElementById('research-status-text');
    bar.style.width  = '100%';
    bar.classList.remove('progress-bar-animated', 'progress-bar-striped');
    bar.classList.add(success ? 'bg-success' : 'bg-danger');
    text.textContent = success ? 'Research complete.' : 'Research failed.';
    setTimeout(function () {
      document.getElementById('research-progress').style.display = 'none';
      bar.classList.add('progress-bar-animated', 'progress-bar-striped');
      bar.classList.remove('bg-success', 'bg-danger');
      bar.classList.add('bg-primary');
    }, 2000);
  }

  // ── Confidence badges ────────────────────────────────────────────────────────

  function renderBadge(wrapper, confidence, source) {
    const old = wrapper.querySelector('.confidence-badge');
    if (old) old.remove();

    if (!confidence || confidence === 'Not Found') return;

    const badge = document.createElement('span');
    badge.className    = 'confidence-badge confidence-' + confidence.toLowerCase().replace(' ', '-');
    badge.textContent  = confidence;
    badge.title        = source || 'No source available';
    badge.style.cursor = 'help';

    const label = wrapper.querySelector('label');
    if (label) label.appendChild(badge);
  }

  function clearBadges() {
    document.querySelectorAll('.confidence-badge').forEach(function (b) { b.remove(); });
  }

  // ── Field map: agent key → form field selector ───────────────────────────────
  // Looks for the wrapper div with data-agent-field, then the input/select/textarea inside it.

  const FIELD_MAP = {
    'company_name':         'company_name',
    'contact_name':         'contact',
    'phone':                'number',
    'email':                'email',
    'address':              'address',
    'sq_footage':           'sq_ft',
    'potential_roi':        'potential',
    'annual_sales':         'annual_sales_locations',
    'notes':                'new_note',
    'facility_type':        'targets',
  };

  function populateField(agentKey, fieldData) {
    const formName = FIELD_MAP[agentKey];
    if (!formName || !fieldData || !fieldData.value) return;

    // Find the wrapper div with data-agent-field
    const wrapper = document.querySelector('[data-agent-field="' + formName + '"]');
    const input   = document.querySelector('[name="' + formName + '"]');
    if (!input) return;

    // For numeric fields, extract digits only
    let value = fieldData.value;
    if (formName === 'sq_ft' || formName === 'potential') {
      const num = value.toString().replace(/[^0-9.]/g, '');
      value = num || value;
    }

    // For contact: combine name + title if both present
    if (agentKey === 'contact_name') {
      // title is in extended, handled separately — just use name here
      input.value = value;
    } else if (input.tagName === 'SELECT') {
      // Try to set the matching option
      const opt = Array.from(input.options).find(function (o) {
        return o.value.toLowerCase() === value.toLowerCase() ||
               o.text.toLowerCase()  === value.toLowerCase();
      });
      if (opt) input.value = opt.value;
    } else {
      input.value = value;
    }

    if (wrapper) {
      renderBadge(wrapper, fieldData.confidence, fieldData.source);
      // Highlight low-confidence fields
      if (fieldData.confidence === 'Low') {
        input.classList.add('agent-low-confidence');
      } else {
        input.classList.remove('agent-low-confidence');
      }
    }
  }

  // Set Action dropdown to 'New Lead' for agent-populated leads
  function setDefaultAction() {
    const sel = document.querySelector('[name="action"]');
    if (sel && !sel.value) {
      const opt = Array.from(sel.options).find(function (o) {
        return o.value === 'New Lead';
      });
      if (opt) sel.value = 'New Lead';
    }
  }

  // ── Research Summary panel ───────────────────────────────────────────────────

  function renderSummary(extended, meta) {
    const panel = document.getElementById('research-summary');
    const body  = document.getElementById('research-summary-body');
    const badge = document.getElementById('research-meta-badge');
    if (!panel || !body) return;

    badge.textContent = meta.fields_populated + '/' + meta.fields_total + ' fields populated · ' +
                        meta.run_duration_sec + 's · ' + meta.tokens_used + ' tokens';
    badge.className   = 'badge small ' + (meta.status === 'success' ? 'bg-success' : meta.status === 'timeout' ? 'bg-warning text-dark' : 'bg-secondary');

    const items = [
      { label: 'Contact Title',     data: extended.contact_title     },
      { label: 'Employees',         data: extended.employee_count     },
      { label: 'Other Locations',   data: extended.other_locations    },
      { label: 'Annual kWh Savings',data: extended.annual_kwh_savings },
      { label: 'Payback Period',    data: extended.payback_period     },
      { label: 'Website',           data: extended.website_url        },
      { label: 'LinkedIn',          data: extended.linkedin_url       },
      { label: 'Recent News',       data: extended.recent_news        },
    ];

    body.innerHTML = '';
    items.forEach(function (item) {
      if (!item.data || !item.data.value) return;
      const col = document.createElement('div');
      col.className = 'col-md-6';

      let valHtml = item.data.value;
      if (item.data.value.startsWith('http')) {
        valHtml = '<a href="' + item.data.value + '" target="_blank" rel="noopener">' +
                  item.data.value + '</a>';
      }

      col.innerHTML = '<strong>' + item.label + ':</strong> ' + valHtml +
                      ' <span class="confidence-badge confidence-' +
                      (item.data.confidence || 'low').toLowerCase() + '">' +
                      (item.data.confidence || '') + '</span>';
      body.appendChild(col);
    });

    if (meta.error_message) {
      const warn = document.createElement('div');
      warn.className = 'col-12 text-warning small';
      warn.textContent = 'Note: ' + meta.error_message;
      body.appendChild(warn);
    }

    panel.style.display = '';
  }

  // ── Clear all agent data ─────────────────────────────────────────────────────

  function clearResearch() {
    Object.values(FIELD_MAP).forEach(function (formName) {
      const input = document.querySelector('[name="' + formName + '"]');
      if (input) {
        input.value = '';
        input.classList.remove('agent-low-confidence');
      }
    });
    clearBadges();
    document.getElementById('research-summary').style.display       = 'none';
    document.getElementById('research-clear-btn').style.display     = 'none';
    document.getElementById('agent_research_run_id').value          = '';
  }

  // ── Main research trigger ────────────────────────────────────────────────────

  function runResearch() {
    const company  = (document.getElementById('research-company').value  || '').trim();
    const location = (document.getElementById('research-location').value || '').trim();

    if (!company) {
      document.getElementById('research-company').focus();
      document.getElementById('research-company').classList.add('is-invalid');
      return;
    }
    document.getElementById('research-company').classList.remove('is-invalid');

    const btn = document.getElementById('research-btn');
    btn.disabled    = true;
    btn.innerHTML   = '<span class="spinner-border spinner-border-sm me-1"></span>Researching…';

    document.getElementById('research-summary').style.display   = 'none';
    document.getElementById('research-clear-btn').style.display = 'none';
    clearBadges();
    startProgress();

    fetch(RESEARCH_URL, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  CSRF_TOKEN,
      },
      body: JSON.stringify({ company_name: company, location_hint: location }),
    })
      .then(function (res) {
        if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || 'Server error'); });
        return res.json();
      })
      .then(function (data) {
        stopProgress(true);

        // Populate form fields
        Object.keys(FIELD_MAP).forEach(function (agentKey) {
          if (data.fields && data.fields[agentKey]) {
            populateField(agentKey, data.fields[agentKey]);
          }
        });

        setDefaultAction();

        // Store run_id for linking on save
        document.getElementById('agent_research_run_id').value = data.run_id || '';

        // Show summary panel
        if (data.extended && data.meta) {
          renderSummary(data.extended, data.meta);
        }

        document.getElementById('research-clear-btn').style.display = '';

        // Warning for timeout/partial
        if (data.status === 'timeout') {
          showAlert('Research timed out — partial results shown. Fields left blank need manual entry.', 'warning');
        } else if (data.status === 'error') {
          showAlert((data.meta && data.meta.error_message) || 'Research encountered an error.', 'danger');
        }
      })
      .catch(function (err) {
        stopProgress(false);
        showAlert('Research failed: ' + err.message, 'danger');
      })
      .finally(function () {
        btn.disabled  = false;
        btn.innerHTML = '<i class="bi bi-search me-1"></i>Research';
      });
  }

  // ── Inline alert helper ──────────────────────────────────────────────────────

  function showAlert(msg, type) {
    const bar = document.getElementById('research-bar');
    let al = document.getElementById('research-alert');
    if (!al) {
      al = document.createElement('div');
      al.id = 'research-alert';
      bar.appendChild(al);
    }
    al.className   = 'alert alert-' + type + ' mb-0 small mt-2';
    al.textContent = msg;
    setTimeout(function () { if (al.parentNode) al.remove(); }, 8000);
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    const btn      = document.getElementById('research-btn');
    const clearBtn = document.getElementById('research-clear-btn');
    const rerunBtn = document.getElementById('research-rerun-btn');
    const company  = document.getElementById('research-company');

    if (!btn) return;   // Not on the Add Lead page

    btn.addEventListener('click', runResearch);

    if (clearBtn) clearBtn.addEventListener('click', clearResearch);
    if (rerunBtn) rerunBtn.addEventListener('click', function () {
      if (confirm('Re-running will overwrite all agent-filled fields. Continue?')) {
        runResearch();
      }
    });

    // Allow Enter key in the company input
    if (company) {
      company.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); runResearch(); }
      });
    }
  });

})();
