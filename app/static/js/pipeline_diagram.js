/* ── Pipeline Diagram Interaction — ComfortLighting ────────────────────────── */
(function () {
  'use strict';

  const STAGES = [
    { name: 'New Lead',       desc: 'Lead record created — no contact made yet.' },
    { name: 'Call Scheduled', desc: 'First call or meeting is booked in the calendar.' },
    { name: 'Contacted',      desc: 'Rep has spoken with or emailed the decision-maker.' },
    { name: 'Quote Requested',desc: 'Prospect explicitly requested pricing or a formal proposal.' },
    { name: 'Proposal Sent',  desc: 'Formal ComfortLighting proposal delivered to prospect.' },
    { name: 'Follow-Up',      desc: 'Following up after proposal — no response yet or feedback received.' },
    { name: 'Negotiation',    desc: 'Prospect actively negotiating price, scope, or timeline.' },
    { name: 'Contract',       desc: 'Terms agreed — contract being drafted or reviewed internally.' },
    { name: 'Contract Sent',  desc: 'Contract delivered to prospect for signature.' },
    { name: 'Closed Won',     desc: 'Contract signed. Project confirmed!' },
    { name: 'Closed Lost',    desc: 'Prospect declined or went silent after final follow-up.' },
  ];

  const TERMINAL = ['Closed Won', 'Closed Lost'];

  // State — refreshed each time init() is called (after DOM replacement)
  let leadId, csrfToken, currentStage, userRole;
  let progressUrl, holdUrl, unholdUrl;

  function stageIdx(name) {
    return STAGES.findIndex(s => s.name === name);
  }

  // ── Initialise / Re-initialise ─────────────────────────────────────────────

  function init() {
    const diagram = document.getElementById('pipeline-diagram');
    if (!diagram) return;

    leadId       = diagram.dataset.leadId;
    currentStage = diagram.dataset.currentStage;
    userRole     = diagram.dataset.userRole;
    progressUrl  = diagram.dataset.progressUrl;
    holdUrl      = diagram.dataset.holdUrl;
    unholdUrl    = diagram.dataset.unholdUrl;
    csrfToken    = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

    attachNodeHandlers();
    attachArrowHoverPreviews();
  }

  // ── Node click / keyboard handlers ────────────────────────────────────────

  function attachNodeHandlers() {
    document.querySelectorAll('.stage-node').forEach(function (node) {
      node.addEventListener('click', function () { openModal(node.dataset.stage); });
      node.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openModal(node.dataset.stage); }
      });
    });

    const removeHoldBtn = document.querySelector('.remove-hold-btn');
    if (removeHoldBtn) {
      removeHoldBtn.addEventListener('click', doUnhold);
    }
  }

  // ── Arrow hover preview ────────────────────────────────────────────────────

  function attachArrowHoverPreviews() {
    const currIdx = stageIdx(currentStage);
    document.querySelectorAll('.stage-node').forEach(function (node) {
      const nodeIdx = parseInt(node.dataset.stageIdx, 10);
      if (nodeIdx > currIdx) {
        node.addEventListener('mouseenter', function () {
          document.querySelectorAll('.arrow-future').forEach(function (el) {
            el.classList.add('arrow-future-hover');
          });
        });
        node.addEventListener('mouseleave', function () {
          document.querySelectorAll('.arrow-future').forEach(function (el) {
            el.classList.remove('arrow-future-hover');
          });
        });
      }
    });
  }

  // ── Modal ──────────────────────────────────────────────────────────────────

  function openModal(targetStage) {
    if (targetStage === currentStage) return;

    const fromIdx          = stageIdx(currentStage);
    const toIdx            = stageIdx(targetStage);
    const isTerminal       = TERMINAL.includes(currentStage);
    const becomingTerminal = TERMINAL.includes(targetStage);
    const isRetreat        = fromIdx >= 0 && toIdx >= 0 && toIdx < fromIdx;
    const isSkip           = !isRetreat && fromIdx >= 0 && (toIdx - fromIdx) > 1;

    // Block non-admin re-open of closed leads
    if (isTerminal && !becomingTerminal && userRole !== 'admin') {
      alert('Only admins can re-open closed leads.');
      return;
    }

    // Populate modal fields
    var fromBadge = document.getElementById('modal-from-badge');
    var toBadge   = document.getElementById('modal-to-badge');
    if (fromBadge) fromBadge.textContent = currentStage || '(none)';
    if (toBadge)   toBadge.textContent   = targetStage;

    var descEl = document.getElementById('modal-stage-desc');
    if (descEl) {
      var sd = STAGES.find(function (s) { return s.name === targetStage; });
      descEl.textContent = sd ? sd.desc : '';
    }

    // Skip warning
    var skipEl  = document.getElementById('modal-skip-warning');
    var skipMsg = document.getElementById('modal-skip-msg');
    if (skipEl && skipMsg) {
      if (isSkip) {
        skipMsg.textContent = 'You are skipping ' + (toIdx - fromIdx) + ' stage(s). Are you sure?';
        skipEl.classList.remove('d-none');
      } else {
        skipEl.classList.add('d-none');
      }
    }

    // Retreat warning
    var retreatEl = document.getElementById('modal-retreat-warning');
    if (retreatEl) {
      isRetreat ? retreatEl.classList.remove('d-none') : retreatEl.classList.add('d-none');
    }

    // Reason field
    var reasonGroup    = document.getElementById('modal-reason-group');
    var reasonRequired = document.getElementById('modal-reason-required');
    var reasonLabel    = document.getElementById('modal-reason-label');
    var reasonInput    = document.getElementById('modal-reason');
    var needsReason    = isTerminal && !becomingTerminal && userRole === 'admin';

    if (reasonGroup) {
      if (needsReason) {
        reasonGroup.classList.remove('d-none');
        if (reasonRequired) reasonRequired.classList.remove('d-none');
        if (reasonLabel)    reasonLabel.textContent = 'Reason for re-opening';
      } else if (isRetreat) {
        reasonGroup.classList.remove('d-none');
        if (reasonRequired) reasonRequired.classList.add('d-none');
        if (reasonLabel)    reasonLabel.textContent = 'Reason for retreat (optional)';
      } else {
        reasonGroup.classList.add('d-none');
      }
    }
    if (reasonInput) {
      reasonInput.value = '';
      reasonInput.classList.remove('is-invalid');
    }

    // Closing notes for terminal targets
    var closingGroup = document.getElementById('modal-closing-notes-group');
    var closingInput = document.getElementById('modal-closing-notes');
    if (closingGroup) {
      becomingTerminal ? closingGroup.classList.remove('d-none') : closingGroup.classList.add('d-none');
    }
    if (closingInput) closingInput.value = '';

    // On Hold button — show for active non-terminal transitions
    var holdBtn = document.getElementById('modal-hold-btn');
    if (holdBtn) {
      var showHold = fromIdx >= 0 && fromIdx <= 8 && !isTerminal && targetStage !== 'On Hold';
      showHold ? holdBtn.classList.remove('d-none') : holdBtn.classList.add('d-none');
    }

    // Store target in modal dataset for confirm handler
    var modalEl = document.getElementById('stageModal');
    if (!modalEl) return;
    modalEl.dataset.targetStage  = targetStage;
    modalEl.dataset.needsReason  = needsReason ? '1' : '0';

    new bootstrap.Modal(modalEl).show();
  }

  // ── Modal confirm ──────────────────────────────────────────────────────────

  function wireModalButtons() {
    var confirmBtn = document.getElementById('modal-confirm-btn');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        var modalEl    = document.getElementById('stageModal');
        var target     = modalEl.dataset.targetStage;
        var needsReason= modalEl.dataset.needsReason === '1';
        var reasonEl   = document.getElementById('modal-reason');
        var closingEl  = document.getElementById('modal-closing-notes');
        var reason     = reasonEl ? reasonEl.value.trim() : '';
        var closing    = closingEl ? closingEl.value.trim() : '';

        if (needsReason && !reason) {
          if (reasonEl) { reasonEl.classList.add('is-invalid'); reasonEl.focus(); }
          return;
        }
        if (reasonEl) reasonEl.classList.remove('is-invalid');

        var bsModal = bootstrap.Modal.getInstance(modalEl);
        if (bsModal) bsModal.hide();

        doChangeStage(target, reason || closing);
      });
    }

    var holdBtn = document.getElementById('modal-hold-btn');
    if (holdBtn) {
      holdBtn.addEventListener('click', function () {
        var bsModal = bootstrap.Modal.getInstance(document.getElementById('stageModal'));
        if (bsModal) bsModal.hide();
        doHold();
      });
    }
  }

  // ── API calls ──────────────────────────────────────────────────────────────

  function doChangeStage(targetStage, reason) {
    if (!progressUrl) return;
    setLoading(true);
    fetchJSON(progressUrl, 'PATCH', { progress: targetStage, reason: reason || '' })
      .then(function (data) {
        if (data.success && data.diagram_html) {
          replaceDiagram(data.diagram_html, true);
          currentStage = data.action || targetStage;
          showToast('Stage updated to ' + (data.action || targetStage));
        } else {
          showToast(data.error || 'Failed to update stage.', 'danger');
        }
      })
      .catch(function (err) { showToast('Network error: ' + err.message, 'danger'); })
      .finally(function () { setLoading(false); });
  }

  function doHold() {
    if (!holdUrl) return;
    setLoading(true);
    fetchJSON(holdUrl, 'POST', {})
      .then(function (data) {
        if (data.success && data.diagram_html) {
          replaceDiagram(data.diagram_html, false);
          currentStage = 'On Hold';
          showToast('Lead placed On Hold.');
        } else {
          showToast(data.error || 'Failed to place on hold.', 'danger');
        }
      })
      .catch(function (err) { showToast('Network error: ' + err.message, 'danger'); })
      .finally(function () { setLoading(false); });
  }

  function doUnhold() {
    if (!unholdUrl) return;
    setLoading(true);
    fetchJSON(unholdUrl, 'POST', {})
      .then(function (data) {
        if (data.success && data.diagram_html) {
          replaceDiagram(data.diagram_html, true);
          currentStage = data.action || 'New Lead';
          showToast('Lead resumed from On Hold.');
        } else {
          showToast(data.error || 'Failed to remove hold.', 'danger');
        }
      })
      .catch(function (err) { showToast('Network error: ' + err.message, 'danger'); })
      .finally(function () { setLoading(false); });
  }

  // ── DOM helpers ────────────────────────────────────────────────────────────

  function fetchJSON(url, method, body) {
    return fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function replaceDiagram(html, animateActive) {
    var existing = document.getElementById('pipeline-diagram');
    if (!existing) return;
    existing.outerHTML = html;
    init();  // re-bind to new element
    if (animateActive) {
      var line = document.querySelector('.arrow-draw-on');
      if (line) {
        // Force reflow so animation restarts on the freshly inserted element
        void line.offsetWidth;
        line.classList.add('arrow-animating');
      }
    }
  }

  function setLoading(on) {
    var el = document.getElementById('pipeline-diagram');
    if (!el) return;
    el.style.opacity       = on ? '0.5' : '1';
    el.style.pointerEvents = on ? 'none' : '';
  }

  function showToast(msg, type) {
    type = type || 'success';
    var container = document.getElementById('pipeline-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'pipeline-toast-container';
      container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      container.style.zIndex = '1100';
      document.body.appendChild(container);
    }
    var el = document.createElement('div');
    el.className = 'toast align-items-center border-0 text-bg-' + type;
    el.setAttribute('role', 'alert');
    el.innerHTML = '<div class="d-flex"><div class="toast-body">' + msg +
      '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    container.appendChild(el);
    new bootstrap.Toast(el, { delay: 3500 }).show();
    el.addEventListener('hidden.bs.toast', function () { el.remove(); });
  }

  // ── Bootstrap event wiring (once on DOMContentLoaded) ─────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    wireModalButtons();
    init();
  });

})();
