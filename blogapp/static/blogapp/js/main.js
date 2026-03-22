/* ================================================================
   BlogForest — main.js
   Global UI behaviour: mobile nav, search dropdown
   ================================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // ── Mobile nav burger ─────────────────────────────────────────
  const burger = document.getElementById('burger-btn');
  const nav    = document.getElementById('main-nav');

  burger?.addEventListener('click', function () {
    nav.classList.toggle('open');
  });

  // ── Search dropdown ───────────────────────────────────────────
  const input    = document.getElementById('search-input');
  const dropdown = document.getElementById('search-dropdown');
  const wrapper  = document.getElementById('search-wrapper');

  if (input && dropdown && wrapper) {

    function openDropdown() {
      dropdown.style.display = 'block';
      // Force reflow so CSS transition fires from the initial state
      dropdown.getBoundingClientRect();
      dropdown.classList.add('search-dropdown-open');
    }

    function closeDropdown() {
      dropdown.classList.remove('search-dropdown-open');
      // Hide after the slide-up transition finishes
      dropdown.addEventListener('transitionend', function hide() {
        if (!dropdown.classList.contains('search-dropdown-open')) {
          dropdown.style.display = 'none';
        }
        dropdown.removeEventListener('transitionend', hide);
      });
    }

    // Open when user focuses the search input
    input.addEventListener('focus', openDropdown);

    // Close when clicking anywhere outside the wrapper
    document.addEventListener('mousedown', function (e) {
      if (!wrapper.contains(e.target)) {
        closeDropdown();
      }
    });

    // Prevent clicks inside the dropdown from bubbling to the document listener
    dropdown.addEventListener('mousedown', function (e) {
      e.stopPropagation();
    });

    // If the page loaded with an active query, show the panel immediately
    if (input.value.trim()) {
      openDropdown();
    }
  }

});
