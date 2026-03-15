/**
 * activity_form.js — conditional field logic for the activity/expense entry form.
 * Called from form.html: initActivityForm(mileageRate)
 */

function initActivityForm(mileageRate) {
  const subSel      = document.getElementById('subcategory_id');
  const catHidden   = document.getElementById('category_id');
  const pmSel       = document.getElementById('payment_method');
  const amtDiv      = document.getElementById('field-amount');
  const milesDiv    = document.getElementById('field-mileage');
  const calcDiv     = document.getElementById('field-mileage-calc');
  const milesInput  = document.getElementById('miles_driven');
  const calcInput   = document.getElementById('mileage_calc');
  const amtInput    = document.getElementById('amount');
  const attenDiv    = document.getElementById('field-attendees');
  const countDiv    = document.getElementById('field-attendee-count');
  const countInput  = document.getElementById('attendee_count');
  const receiptCb   = document.getElementById('receipt_attached');
  const receiptDiv  = document.getElementById('field-receipt-upload');
  const ppWarn      = document.getElementById('per-person-warning');
  const reimbursCb  = document.getElementById('reimbursable');
  const dateInput   = document.querySelector('input[name="activity_date"]');

  // ── Date: block future dates ───────────────────────────────────────────────
  if (dateInput && !dateInput.readOnly) {
    const today = new Date().toISOString().slice(0, 10);
    dateInput.setAttribute('max', today);
    dateInput.addEventListener('change', () => {
      if (dateInput.value > today) {
        dateInput.value = today;
      }
    });
  }

  // ── Receipt checkbox toggle ───────────────────────────────────────────────
  function toggleReceipt() {
    if (!receiptCb || !receiptDiv) return;
    if (receiptCb.checked) {
      receiptDiv.classList.remove('d-none');
    } else {
      receiptDiv.classList.add('d-none');
    }
  }
  if (receiptCb) {
    receiptCb.addEventListener('change', toggleReceipt);
    toggleReceipt();
  }

  // ── Amount auto-check for receipt ─────────────────────────────────────────
  function checkReceiptRequired() {
    if (!amtInput || !receiptCb || receiptCb.disabled) return;
    const amt = parseFloat(amtInput.value) || 0;
    if (amt > 25 && !receiptCb.checked) {
      receiptCb.parentElement.querySelector('label').classList.add('text-warning');
    } else {
      receiptCb.parentElement.querySelector('label').classList.remove('text-warning');
    }
  }
  if (amtInput) amtInput.addEventListener('input', checkReceiptRequired);

  // ── Mileage calculation ───────────────────────────────────────────────────
  function calcMileage() {
    if (!milesInput || !calcInput) return;
    const miles = parseFloat(milesInput.value) || 0;
    const rate  = parseFloat(document.getElementById('mileage_rate_val')?.value || mileageRate) || mileageRate;
    if (miles > 0) {
      calcInput.value = '$' + (miles * rate).toFixed(2);
    } else {
      calcInput.value = '';
    }
  }
  if (milesInput) milesInput.addEventListener('input', calcMileage);

  // ── Per-person cost warning ────────────────────────────────────────────────
  function checkPerPerson() {
    if (!ppWarn) return;
    const count = parseInt(countInput?.value) || 0;
    const amt   = parseFloat(amtInput?.value) || 0;
    if (count > 0 && amt > 0 && (amt / count) > 75) {
      ppWarn.classList.remove('d-none');
    } else {
      ppWarn.classList.add('d-none');
    }
  }
  if (countInput) countInput.addEventListener('input', checkPerPerson);
  if (amtInput)   amtInput.addEventListener('input', checkPerPerson);

  // ── Show/hide mileage vs. amount fields ───────────────────────────────────
  function setMileageMode(isMileage) {
    if (!amtDiv || !milesDiv || !calcDiv) return;
    if (isMileage) {
      amtDiv.classList.add('d-none');
      milesDiv.classList.remove('d-none');
      calcDiv.classList.remove('d-none');
      if (amtInput) amtInput.removeAttribute('required');
      if (milesInput) milesInput.setAttribute('required', '');
      if (pmSel && !pmSel.disabled) {
        for (let opt of pmSel.options) {
          if (opt.value === 'Mileage') { opt.selected = true; break; }
        }
      }
      calcMileage();
    } else {
      amtDiv.classList.remove('d-none');
      milesDiv.classList.add('d-none');
      calcDiv.classList.add('d-none');
      if (amtInput) amtInput.setAttribute('required', '');
      if (milesInput) milesInput.removeAttribute('required');
    }
  }

  // ── Show/hide attendees fields ────────────────────────────────────────────
  function setAttendeesMode(required) {
    if (!attenDiv || !countDiv) return;
    if (required) {
      attenDiv.classList.remove('d-none');
      countDiv.classList.remove('d-none');
    } else {
      attenDiv.classList.add('d-none');
      countDiv.classList.add('d-none');
    }
  }

  // ── Payment method → reimbursable default ────────────────────────────────
  function updateReimbursable(pm) {
    if (!reimbursCb || reimbursCb.disabled) return;
    if (pm === 'Personal Card' || pm === 'Cash') {
      reimbursCb.checked = true;
    } else if (pm === 'Corporate Card' || pm === 'Mileage') {
      reimbursCb.checked = false;
    }
  }
  if (pmSel) {
    pmSel.addEventListener('change', () => updateReimbursable(pmSel.value));
  }

  // ── Combined category+subcategory select effects ──────────────────────────
  function applySubcategoryEffects() {
    if (!subSel) return;
    const selOpt = subSel.options[subSel.selectedIndex];
    const isMileage        = selOpt?.dataset.isMileage === '1';
    const subRequiresAt    = selOpt?.dataset.requiresAttendees === '1';
    const parentRequiresAt = selOpt?.dataset.parentRequiresAttendees === '1';

    if (catHidden) {
      catHidden.value = selOpt?.dataset.categoryId || '';
    }

    setAttendeesMode(subRequiresAt || parentRequiresAt);
    setMileageMode(isMileage);
    checkPerPerson();
  }

  if (subSel) {
    subSel.addEventListener('change', applySubcategoryEffects);
  }

  // ── Initialise state on page load ─────────────────────────────────────────
  applySubcategoryEffects();
  checkReceiptRequired();
  checkPerPerson();
}
