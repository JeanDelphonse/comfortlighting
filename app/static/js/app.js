/**
 * ComfortLighting – app.js
 */

document.addEventListener('DOMContentLoaded', () => {

  // Auto-dismiss flash alerts after 5 s
  document.querySelectorAll('.alert-dismissible').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert.close();
    }, 5000);
  });

  // Warn on unsaved form changes
  const leadForm = document.querySelector('form[data-track-changes]');
  if (leadForm) {
    let dirty = false;
    leadForm.querySelectorAll('input, select, textarea').forEach(el => {
      el.addEventListener('change', () => { dirty = true; });
    });
    leadForm.addEventListener('submit', () => { dirty = false; });
    window.addEventListener('beforeunload', e => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    });
  }

});
