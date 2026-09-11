/* ============================================================================
   Delivery ASAP hub — the theme, before the first paint.

   Loaded blocking in <head>, and doing nothing else: the choice has to be on
   <html> before the body renders, or a forced dark theme flashes white on
   every navigation. Everything else about it lives in app.js.
   ========================================================================== */
(function () {
  'use strict';
  try {
    var theme = localStorage.getItem('dah_theme');
    // Any key themes.css declares; the pattern is the whole validation there is
    // to do, since an unknown one simply matches no block.
    if (theme && /^[a-z0-9-]{1,40}$/.test(theme) && theme !== 'system') {
      document.documentElement.setAttribute('data-theme', theme);
    }
  } catch (err) {
    /* No storage: the system preference decides, which is the default anyway. */
  }
})();
