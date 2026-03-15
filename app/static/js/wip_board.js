/**
 * ComfortLighting – WIP Board Drag & Drop
 * Uses native HTML5 drag events to move leads between the WIP card grid
 * and the lead list table, which are incompatible container types.
 */

(function () {
  'use strict';

  // ── Toast ──────────────────────────────────────────────────────────────────
  function showToast(message, type, undoCallback) {
    type = type || 'info';
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      container.style.zIndex = '9999';
      document.body.appendChild(container);
    }

    const toastId = 'toast-' + Date.now();
    const undoBtn = undoCallback
      ? `<button class="btn btn-link btn-sm text-decoration-none p-0 ms-2" id="${toastId}-undo">Undo</button>`
      : '';
    const headerClass = { success: 'success', info: 'info', danger: 'danger' }[type] || 'secondary';

    const toast = document.createElement('div');
    toast.className = `toast show bg-white border-${headerClass}`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <div class="toast-header bg-${headerClass} text-white">
        <strong class="me-auto">${{ success: 'Success', info: 'Info', danger: 'Error' }[type] || 'Notice'}</strong>
        <button type="button" class="btn-close btn-close-white" onclick="this.closest('.toast').remove()"></button>
      </div>
      <div class="toast-body d-flex justify-content-between align-items-center">
        <span>${message}</span>${undoBtn}
      </div>`;
    container.appendChild(toast);

    if (undoCallback) {
      document.getElementById(toastId + '-undo').addEventListener('click', function () {
        undoCallback();
        toast.remove();
      });
    }

    setTimeout(function () {
      if (toast.parentNode) {
        toast.style.opacity = '0';
        setTimeout(function () { toast.remove(); }, 300);
      }
    }, undoCallback ? 6000 : 4000);
  }

  // ── WIP count badge ────────────────────────────────────────────────────────
  function updateWipCount(delta) {
    const badge = document.getElementById('wip-count');
    if (!badge) return;
    const newCount = Math.max(0, (parseInt(badge.textContent) || 0) + delta);
    badge.textContent = newCount;

    const wipGrid = document.getElementById('wip-grid');
    const emptyState = document.getElementById('wip-empty');
    if (wipGrid) wipGrid.style.display = newCount === 0 ? 'none' : '';
    if (emptyState) emptyState.style.display = newCount === 0 ? 'block' : 'none';
  }

  // ── API call ───────────────────────────────────────────────────────────────
  function getCsrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function wipUrl(leadId) {
    const tpl = (document.getElementById('wip-section') || {}).dataset.toggleUrl || '/leads/0/wip';
    return tpl.replace('/0/wip', '/' + leadId + '/wip');
  }

  function toggleWip(leadId, addToWip, callback) {
    fetch(wipUrl(leadId), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ wip: addToWip })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) { callback(data.success ? data : null); })
      .catch(function (err) {
        console.error('WIP toggle error:', err);
        showToast('Network error while updating WIP status', 'danger');
        callback(null);
      });
  }

  // ── Drag state ─────────────────────────────────────────────────────────────
  let dragLeadId = null;
  let dragSource = null; // 'wip' | 'list'

  function getLeadName(el) {
    const a = el.querySelector('a.fw-semibold, .card-title a');
    return a ? a.textContent.trim() : 'Lead';
  }

  // ── Set up draggable WIP cards ─────────────────────────────────────────────
  function bindWipCard(card) {
    card.addEventListener('dragstart', function (e) {
      dragLeadId = card.getAttribute('data-lead-id');
      dragSource = 'wip';
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', dragLeadId);
      card.style.opacity = '0.5';
    });
    card.addEventListener('dragend', function () {
      card.style.opacity = '';
      clearDropHighlight();
    });
  }

  // ── Set up draggable table rows ────────────────────────────────────────────
  function bindTableRow(row) {
    row.addEventListener('dragstart', function (e) {
      dragLeadId = row.getAttribute('data-lead-id');
      dragSource = 'list';
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', dragLeadId);
      row.style.opacity = '0.5';
    });
    row.addEventListener('dragend', function () {
      row.style.opacity = '';
      clearDropHighlight();
    });
  }

  // ── Drop zone helpers ──────────────────────────────────────────────────────
  function clearDropHighlight() {
    const wipGrid = document.getElementById('wip-grid');
    const tbody = document.getElementById('lead-list-body');
    if (wipGrid) wipGrid.classList.remove('border', 'border-primary', 'border-2', 'bg-light');
    if (tbody) tbody.classList.remove('table-primary');
  }

  // ── WIP grid as drop target (receives rows from lead list) ─────────────────
  function initWipDropZone() {
    const wipSection = document.getElementById('wip-section');
    if (!wipSection) return;

    wipSection.addEventListener('dragover', function (e) {
      if (dragSource !== 'list') return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const wipGrid = document.getElementById('wip-grid');
      if (wipGrid) wipGrid.classList.add('border', 'border-primary', 'border-2');
    });

    wipSection.addEventListener('dragleave', function (e) {
      if (!wipSection.contains(e.relatedTarget)) clearDropHighlight();
    });

    wipSection.addEventListener('drop', function (e) {
      if (dragSource !== 'list') return;
      e.preventDefault();
      clearDropHighlight();

      const leadId = dragLeadId;
      const tbody = document.getElementById('lead-list-body');
      const row = tbody ? tbody.querySelector(`tr[data-lead-id="${leadId}"]`) : null;
      const companyName = row ? getLeadName(row) : 'Lead';

      if (row) row.remove();

      toggleWip(leadId, true, function (data) {
        if (data) {
          updateWipCount(1);
          showToast(companyName + ' moved to Work In Progress', 'success', function () {
            toggleWip(leadId, false, function () { location.reload(); });
          });
        } else {
          // Restore: reload to get correct state
          location.reload();
        }
      });
    });
  }

  // ── Lead list tbody as drop target (receives WIP cards) ───────────────────
  function initListDropZone() {
    const tbody = document.getElementById('lead-list-body');
    if (!tbody) return;

    tbody.addEventListener('dragover', function (e) {
      if (dragSource !== 'wip') return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      tbody.classList.add('table-primary');
    });

    tbody.addEventListener('dragleave', function (e) {
      if (!tbody.contains(e.relatedTarget)) clearDropHighlight();
    });

    tbody.addEventListener('drop', function (e) {
      if (dragSource !== 'wip') return;
      e.preventDefault();
      clearDropHighlight();

      const leadId = dragLeadId;
      const wipGrid = document.getElementById('wip-grid');
      const card = wipGrid ? wipGrid.querySelector(`[data-lead-id="${leadId}"]`) : null;
      const companyName = card ? getLeadName(card) : 'Lead';

      if (card) card.remove();

      toggleWip(leadId, false, function (data) {
        if (data) {
          updateWipCount(-1);
          showToast(companyName + ' returned to Lead List', 'info', function () {
            toggleWip(leadId, true, function () { location.reload(); });
          });
        } else {
          location.reload();
        }
      });
    });
  }

  // ── Remove (×) buttons on WIP cards ───────────────────────────────────────
  function initRemoveButtons() {
    document.querySelectorAll('.wip-remove').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        const card = btn.closest('[data-lead-id]');
        const leadId = card.getAttribute('data-lead-id');
        const companyName = getLeadName(card);

        toggleWip(leadId, false, function (data) {
          if (data) {
            card.remove();
            updateWipCount(-1);
            showToast(companyName + ' returned to Lead List', 'info');
          } else {
            showToast('Failed to update WIP status', 'danger');
          }
        });
      });
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  function init() {
    const wipGrid = document.getElementById('wip-grid');
    const tbody = document.getElementById('lead-list-body');
    if (!wipGrid && !tbody) return;

    // Bind draggable WIP cards
    if (wipGrid) {
      wipGrid.querySelectorAll('[data-lead-id]').forEach(bindWipCard);
    }

    // Bind draggable table rows
    if (tbody) {
      tbody.querySelectorAll('tr[data-lead-id]').forEach(bindTableRow);
    }

    initWipDropZone();
    initListDropZone();
    initRemoveButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
