/* ================================================================
   BlogForest — main.js
   Global UI behaviour: mobile nav, search dropdown, password toggle
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

  // ── Unread count polling ─────────────────────────────────────
  (function () {
    const badges = document.querySelectorAll('.nav-scroll-badge');
    const btns   = document.querySelectorAll('.nav-scroll-btn');
    if (!btns.length) return; // not logged in

    function updateBadges(count) {
      btns.forEach(btn => {
        let badge = btn.querySelector('.nav-scroll-badge');
        if (count > 0) {
          if (!badge) {
            badge = document.createElement('span');
            badge.className = 'nav-scroll-badge';
            btn.appendChild(badge);
          }
          badge.textContent = count;
        } else {
          if (badge) badge.remove();
        }
      });
    }

    function poll() {
      fetch('/api/unread-count/', { credentials: 'same-origin' })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data) updateBadges(data.count); })
        .catch(() => {});
    }

    // Poll every 60 seconds
    setInterval(poll, 60000);
  })();

  // ── Password toggle ───────────────────────────────────────────
  document.querySelectorAll('.password-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.closest('.password-wrap').querySelector('input');
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.classList.toggle('visible', isHidden);
    });
  });


  // ── Settings panel ───────────────────────────────────────────
  const settingsPanel   = document.getElementById('settings-panel');
  const settingsOverlay = document.getElementById('settings-overlay');
  const settingsBtnD    = document.getElementById('settings-btn-desktop');
  const colorsMenuItem  = document.getElementById('colors-menu-item');
  const colorSubmenu    = document.getElementById('color-submenu');

  function openSettings() {
    settingsPanel?.classList.add('open');
    settingsOverlay?.classList.add('open');
    settingsBtnD?.classList.add('open');
  }
  function closeSettings() {
    settingsPanel?.classList.remove('open');
    settingsOverlay?.classList.remove('open');
    settingsBtnD?.classList.remove('open');
    colorsMenuItem?.classList.remove('submenu-open');
    colorSubmenu?.classList.remove('open');
  }

  [settingsBtnD].forEach(btn => {
    btn?.addEventListener('click', function (e) {
      e.stopPropagation();
      settingsPanel?.classList.contains('open') ? closeSettings() : openSettings();
    });
  });

  settingsOverlay?.addEventListener('click', closeSettings);

  // Colors submenu toggle
  colorsMenuItem?.addEventListener('click', function () {
    const isOpen = colorSubmenu?.classList.contains('open');
    colorSubmenu?.classList.toggle('open', !isOpen);
    colorsMenuItem?.classList.toggle('submenu-open', !isOpen);
  });

  // Apply theme: set data-theme attribute and update swatch active state
  function applyTheme(theme) {
    if (!theme || theme === 'emerald') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
    document.querySelectorAll('.color-scheme-option').forEach(el => {
      el.classList.toggle('active', el.dataset.theme === (theme || 'emerald'));
    });
  }

  // Read current theme from <html data-theme> set by server (no localStorage needed)
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'emerald';
  applyTheme(currentTheme);

  // Color scheme picker — save to server so it persists across devices and sessions
  document.querySelectorAll('.color-scheme-option').forEach(option => {
    option.addEventListener('click', function () {
      const theme = this.dataset.theme;
      applyTheme(theme);
      // Persist on server via POST (CSRF token from cookie)
      const csrf = document.cookie.match(/csrftoken=([^;]+)/);
      if (csrf) {
        fetch('/set-theme/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrf[1],
          },
          body: 'theme=' + encodeURIComponent(theme),
        });
      }
    });
  });

  // ── Quote tooltip ────────────────────────────────────────────
  (function () {
    if (!document.querySelector('.quote-source')) return;

    // Derive post_create URL from current page: /blogs/<pk>/ → /blogs/<pk>/posts/create/
    var pathMatch = window.location.pathname.match(/\/blogs\/(\d+)/);
    if (!pathMatch) return;
    var createUrl = '/blogs/' + pathMatch[1] + '/posts/create/';

    var tooltip = document.createElement('div');
    tooltip.id = 'quote-tooltip';
    tooltip.textContent = '💬 Quote';
    document.body.appendChild(tooltip);

    var hideTimer = null;

    function showTooltip(x, y, text, authorId) {
      clearTimeout(hideTimer);
      tooltip.dataset.text = text;
      tooltip.dataset.authorId = authorId || '';
      tooltip.style.left = x + 'px';
      tooltip.style.top  = (y + window.scrollY - 44) + 'px';
      tooltip.style.display = 'block';
    }

    function hideTooltip() {
      hideTimer = setTimeout(function () { tooltip.style.display = 'none'; }, 150);
    }

    document.addEventListener('mouseup', function (e) {
      if (e.target === tooltip) return;
      var sel = window.getSelection();
      if (!sel || sel.isCollapsed) { hideTooltip(); return; }
      var text = sel.toString().trim();
      if (text.length < 3) { hideTooltip(); return; }

      // Walk up DOM to find .quote-source
      var node = sel.anchorNode;
      var source = null;
      while (node && node !== document.body) {
        if (node.nodeType === 1 && node.classList && node.classList.contains('quote-source')) {
          source = node; break;
        }
        node = node.parentNode;
      }
      if (!source) { hideTooltip(); return; }

      var authorId = source.dataset.authorId || '';
      var range = sel.getRangeAt(0);
      var rect  = range.getBoundingClientRect();
      showTooltip(rect.left + rect.width / 2, rect.top, text, authorId);
    });

    document.addEventListener('mousedown', function (e) {
      if (e.target !== tooltip) hideTooltip();
    });

    tooltip.addEventListener('mouseenter', function () { clearTimeout(hideTimer); });
    tooltip.addEventListener('mouseleave', hideTooltip);

    // preventDefault stops mousedown from collapsing the selection
    tooltip.addEventListener('mousedown', function (e) { e.preventDefault(); });

    tooltip.addEventListener('click', function () {
      var text     = tooltip.dataset.text;
      var authorId = tooltip.dataset.authorId;
      if (!text) return;
      var url = createUrl
        + '?quote=' + encodeURIComponent(text)
        + (authorId ? '&author_id=' + encodeURIComponent(authorId) : '');
      tooltip.style.display = 'none';
      window.getSelection().removeAllRanges();
      window.location.href = url;
    });
  })();

  // ── Drag & Drop file zones ────────────────────────────────────
  const MAX_FILE_MB = 5;
  const MAX_BYTES = MAX_FILE_MB * 1024 * 1024;

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function initDropzone(dropzoneEl, listEl) {
    if (!dropzoneEl || !listEl) return;
    const input = dropzoneEl.querySelector('.dropzone-input');
    if (!input) return;

    // Track selected files (DataTransfer trick for merging picks)
    let selectedFiles = [];

    function syncInputFiles() {
      const dt = new DataTransfer();
      selectedFiles.forEach(f => dt.items.add(f));
      input.files = dt.files;
    }

    function renderList() {
      listEl.innerHTML = '';
      selectedFiles.forEach((file, idx) => {
        const overLimit = file.size > MAX_BYTES;
        const item = document.createElement('div');
        item.className = 'dropzone-file-item';
        item.innerHTML =
          '<span>📄</span>' +
          '<span class="dropzone-file-item-name" title="' + file.name + '">' + file.name + '</span>' +
          '<span class="dropzone-file-item-size">' + formatBytes(file.size) + '</span>' +
          (overLimit ? '<span class="dropzone-file-item-err">⚠ too large</span>' : '') +
          '<button type="button" class="dropzone-file-item-remove" data-idx="' + idx + '" title="Remove">✕</button>';
        listEl.appendChild(item);
      });

      listEl.querySelectorAll('.dropzone-file-item-remove').forEach(btn => {
        btn.addEventListener('click', function () {
          selectedFiles.splice(parseInt(this.dataset.idx), 1);
          syncInputFiles();
          renderList();
        });
      });
    }

    function addFiles(fileList) {
      const incoming = Array.from(fileList);
      // Merge — avoid duplicates by name+size
      incoming.forEach(f => {
        const dup = selectedFiles.some(s => s.name === f.name && s.size === f.size);
        if (!dup) selectedFiles.push(f);
      });
      syncInputFiles();
      renderList();
    }

    // Click opens file picker (input already covers the zone with opacity:0)
    input.addEventListener('change', function () {
      const snapshot = Array.from(this.files);
      this.value = '';
      addFiles(snapshot);
    });

    // Drag events
    dropzoneEl.addEventListener('dragenter', e => { e.preventDefault(); dropzoneEl.classList.add('drag-over'); });
    dropzoneEl.addEventListener('dragover',  e => { e.preventDefault(); dropzoneEl.classList.add('drag-over'); });
    dropzoneEl.addEventListener('dragleave', e => {
      if (!dropzoneEl.contains(e.relatedTarget)) dropzoneEl.classList.remove('drag-over');
    });
    dropzoneEl.addEventListener('drop', function (e) {
      e.preventDefault();
      dropzoneEl.classList.remove('drag-over');
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    });
  }

  document.querySelectorAll('.dropzone').forEach(function (dz) {
    const listId = dz.id + '-list';
    const list = document.getElementById(listId);
    initDropzone(dz, list);
  });

  // ── Poll: динамические варианты ответов ───────────────────────
  (function () {
    const container = document.getElementById('options-container');
    const addBtn    = document.getElementById('add-option');
    if (!container || !addBtn) return;

    let counter = container.querySelectorAll('.option-row').length;

    function updateRemoveButtons() {
      const rows = container.querySelectorAll('.option-row');
      rows.forEach(row => {
        row.querySelector('.remove-option').style.display =
          rows.length > 2 ? 'inline-flex' : 'none';
      });
    }

    addBtn.addEventListener('click', function () {
      const row = document.createElement('div');
      row.className = 'option-row';
      row.style.cssText = 'display:flex; gap:8px; align-items:center; margin-bottom:8px;';
      row.innerHTML =
        '<input type="text" name="option_text_' + counter + '" class="form-control"' +
        ' placeholder="Option ' + (counter + 1) + '">' +
        '<button type="button" class="btn btn-ghost btn-sm remove-option"' +
        ' style="color:#c0392b; border-color:#f5c2c0; flex-shrink:0;" title="Remove option">✕</button>';
      container.appendChild(row);
      counter++;
      updateRemoveButtons();
      row.querySelector('input').focus();
    });

    container.addEventListener('click', function (e) {
      if (e.target.classList.contains('remove-option')) {
        e.target.closest('.option-row').remove();
        updateRemoveButtons();
      }
    });

    const pollForm = document.getElementById('poll-form');
    if (pollForm) {
      pollForm.addEventListener('submit', function (e) {
        const filled = Array.from(container.querySelectorAll('input[type="text"]'))
                            .filter(inp => inp.value.trim() !== '');
        const errEl = document.getElementById('options-error');
        if (filled.length < 2) {
          e.preventDefault();
          errEl.style.display = 'block';
          errEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          errEl.style.display = 'none';
        }
      });
    }
  })();

});
