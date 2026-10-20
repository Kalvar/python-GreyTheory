'use strict';
// Native and direct-file windows share the same manual and reload controls.
const manualDialog = document.getElementById('manualDialog');
let manualOpener = null;
function showManual(section, opener) {
  manualOpener = opener;
  if (!manualDialog.open) manualDialog.showModal();
  const target = document.getElementById(`help-${section}`);
  if (target) {
    target.scrollIntoView({block: 'start'});
    target.focus({preventScroll: true});
  }
}
document.querySelectorAll('[data-help]').forEach(button => {
  button.addEventListener('click', () => {
    const section = button.dataset.help === 'scenario'
      ? document.getElementById('scenario').value || 'lab'
      : button.dataset.help;
    showManual(section, button);
  });
});
document.querySelectorAll('[data-manual-section]').forEach(link => {
  link.addEventListener('click', event => {
    event.preventDefault(); // Keep #desktop intact for the Python bridge.
    showManual(link.dataset.manualSection, manualOpener);
  });
});
document.getElementById('closeManual').addEventListener('click', () => manualDialog.close());
manualDialog.addEventListener('close', () => manualOpener?.focus());
document.getElementById('reloadPage').addEventListener('click', () => window.location.reload());
