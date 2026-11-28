(function (settings) {
  'use strict';
  // Direct style properties preserve the service's existing CSP.
  function style(selector, properties) {
    document.querySelectorAll(selector).forEach(function (element) {
      Object.keys(properties).forEach(function (key) { element.style[key] = properties[key]; });
    });
  }
  style('html, body', { maxWidth: '100%' });
  style('main, .card, .grid2 > *, .fields > *, .answer-row > *', { minWidth: '0' });
  style('input, textarea, select, pre', { maxWidth: '100%' });
  style('header', { flexWrap: 'wrap', gap: '12px', padding: '14px 16px' });
  style('header div, header nav', { minWidth: '0', maxWidth: '100%', flexWrap: 'wrap', gap: '8px' });
  style('header nav a', { marginLeft: '0' });
  style('.lang, .lang select', { minWidth: '0', maxWidth: '100%' });
  const checkout = document.getElementById('checkout');
  if (checkout) {
    checkout.disabled = true;
    checkout.textContent = settings.checkoutUnavailable;
    checkout.setAttribute('aria-label', settings.checkoutUnavailable);
    checkout.style.opacity = '0.75';
    checkout.style.cursor = 'default';
  }
  if (!window.__wrAndroidPurchasesBlocked) {
    document.addEventListener('click', function (event) {
      const target = event.target instanceof Element ? event.target.closest('#checkout') : null;
      if (target) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);
    window.__wrAndroidPurchasesBlocked = true;
  }
})
