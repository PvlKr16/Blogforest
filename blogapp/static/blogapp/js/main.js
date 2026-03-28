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

  // ── Password toggle ───────────────────────────────────────────
  document.querySelectorAll('.password-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.closest('.password-wrap').querySelector('input');
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.classList.toggle('visible', isHidden);
    });
  });


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
      addFiles(this.files);
      // Reset input so same file can be re-added after removal
      this.value = '';
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

});
