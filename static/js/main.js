/* ── main.js — Indian Gemological Institute Frontend Logic ── */

/* =====================================================
   1. GEMSTONE AUTO-FILL & CUSTOM GEMSTONE LOGIC
   ===================================================== */
const csrfMeta = document.querySelector('meta[name="csrf-token"]');
const csrfToken = csrfMeta ? csrfMeta.content : '';
// Helper to create headers with CSRF token
const csrfHeaders = (extra = {}) => Object.assign(csrfToken ? { 'X-CSRFToken': csrfToken } : {}, extra);

const gemstoneSelect = document.getElementById('gemstone_name');

const autofillFields = {
  refractive_index: document.getElementById('refractive_index'),
  specific_gravity:  document.getElementById('specific_gravity'),
  hardness:          document.getElementById('hardness'),
  chemical_formula:  document.getElementById('chemical_formula'),
  crystal_system:    document.getElementById('crystal_system'),
};

if (gemstoneSelect) {
  gemstoneSelect.addEventListener('change', async () => {
    const name = gemstoneSelect.value;
    const otherWrap = document.getElementById('other-gemstone-wrap');

    // Show/hide "Add New Gemstone" input
    if (otherWrap) {
      otherWrap.style.display = (name === '__other__') ? 'block' : 'none';
    }

    if (!name || name === '__other__') return clearAutofill();
    try {
      const res  = await fetch(`/api/gemstone/${encodeURIComponent(name)}`);
      const data = await res.json();
      if (data.error) return clearAutofill();
      Object.keys(autofillFields).forEach(key => {
        const el = autofillFields[key];
        if (el && data[key] !== undefined) {
          el.value = data[key];
          el.classList.add('autofill-field');
        }
      });
    } catch {
      clearAutofill();
    }
  });
}

function clearAutofill() {
  Object.values(autofillFields).forEach(el => {
    if (el) { el.value = ''; el.classList.remove('autofill-field'); }
  });
}

/**
 * Save a new custom gemstone via API and inject it into the dropdown.
 * Called when user clicks "Save & Use" in the "Other" row.
 */
async function addGemstoneInline() {
  const input = document.getElementById('new_gemstone_name_input');
  const name  = (input?.value || '').trim();
  if (!name) { showToast('Please enter a gemstone name.', 'error'); return; }

  try {
    const res = await fetch('/api/gemstone/add', {
      method: 'POST',
      headers: csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name }),
    });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    // Inject as new option before "__other__"
    const sel = document.getElementById('gemstone_name');
    const otherOpt = sel.querySelector('option[value="__other__"]');
    const newOpt = document.createElement('option');
    newOpt.value    = name;
    newOpt.textContent = `${name} ★`;
    newOpt.selected = true;
    sel.insertBefore(newOpt, otherOpt);

    // Hide the "other" input and clear it
    const wrap = document.getElementById('other-gemstone-wrap');
    if (wrap) wrap.style.display = 'none';
    if (input) input.value = '';

    showToast(`"${name}" added and selected!`, 'success');
  } catch {
    showToast('Failed to add gemstone. Please try again.', 'error');
  }
}

/* =====================================================
   2. DRAG-DROP IMAGE UPLOAD
   ===================================================== */
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('image-upload');
const imgPreview = document.getElementById('img-preview');
const imgWrap    = document.getElementById('img-wrap');
const uploadedPath = document.getElementById('uploaded_image_path');

function setupDropZone() {
  if (!dropZone) return;

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadImage(file);
  });
  dropZone.addEventListener('click', () => fileInput && fileInput.click());
  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) uploadImage(fileInput.files[0]);
    });
  }
}

async function uploadImage(file) {
  const allowed = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowed.includes(file.type)) {
    showToast('Only JPEG, PNG, or WEBP images are allowed.', 'error');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('Image must be under 10 MB.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('image', file);

  dropZone.innerHTML = `<div class="flex flex-col items-center gap-2 text-blue-600">
    <svg class="animate-spin h-8 w-8" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
    </svg>
    <span>Uploading…</span>
  </div>`;

  try {
    const headers = {};
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    const res  = await fetch('/api/upload-image', { method: 'POST', headers, body: formData });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); resetDropZone(); return; }

    if (imgPreview) { imgPreview.src = data.thumbnail_url; imgPreview.classList.remove('hidden'); }
    if (imgWrap)    imgWrap.classList.remove('hidden');
    if (uploadedPath) uploadedPath.value = data.image_path;
    dropZone.innerHTML = `<div class="flex flex-col items-center gap-1 text-green-600">
      <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
      </svg>
      <span class="text-sm font-medium">Image uploaded!</span>
      <span class="text-xs text-gray-500">Click to replace</span>
    </div>`;
    showToast('Image uploaded successfully!', 'success');
  } catch {
    showToast('Upload failed. Please try again.', 'error');
    resetDropZone();
  }
}

function resetDropZone() {
  if (!dropZone) return;
  dropZone.innerHTML = `<div class="flex flex-col items-center gap-2 text-gray-400">
    <svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
        d="M3 16.5V18a2 2 0 002 2h14a2 2 0 002-2v-1.5M12 3v12m0-12L8.5 6.5M12 3l3.5 3.5"/>
    </svg>
    <span class="text-sm font-medium">Drag &amp; drop image here</span>
    <span class="text-xs">or click to browse — JPEG / PNG / WEBP up to 10 MB</span>
  </div>`;
}

/* =====================================================
   3. BULK CLONE MODAL
   ===================================================== */
function openCloneModal(certId) {
  const modal = document.getElementById('clone-modal');
  const certIdInput = document.getElementById('clone-cert-id');
  if (modal) modal.classList.remove('hidden');
  if (certIdInput) certIdInput.value = certId;
}

function closeCloneModal() {
  const modal = document.getElementById('clone-modal');
  if (modal) modal.classList.add('hidden');
}

async function submitClone() {
  const certId = document.getElementById('clone-cert-id')?.value;
  const count  = parseInt(document.getElementById('clone-count')?.value || '0');
  const btn    = document.getElementById('clone-submit-btn');

  if (!certId || count < 1 || count > 500) {
    showToast('Enter a valid count (1–500).', 'error'); return;
  }

  if (btn) { btn.disabled = true; btn.textContent = 'Cloning…'; }

  try {
    const res  = await fetch(`/certificate/${certId}/clone`, {
      method: 'POST',
      headers: csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ count }),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }
    showToast(`✅ ${data.created} certificates created!`, 'success');
    closeCloneModal();
    setTimeout(() => location.reload(), 1200);
  } catch {
    showToast('Clone failed. Please try again.', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Clone'; }
  }
}

/* =====================================================
   4. DELETE CERTIFICATE
   ===================================================== */
async function deleteCert(certId, reportNum) {
  if (!confirm(`Delete certificate ${reportNum}? This cannot be undone.`)) return;
  try {
    const res  = await fetch(`/certificate/${certId}`, { 
      method: 'DELETE',
      headers: csrfHeaders()
    });
    const data = await res.json();
    if (data.success) {
      showToast('Certificate deleted.', 'success');
      document.getElementById(`row-${certId}`)?.remove();
    } else {
      showToast(data.error || 'Delete failed.', 'error');
    }
  } catch {
    showToast('Delete failed.', 'error');
  }
}

/* =====================================================
   5. DASHBOARD SEARCH / FILTER
   ===================================================== */
function filterTable() {
  const q   = document.getElementById('table-search')?.value.toLowerCase() || '';
  const rows = document.querySelectorAll('.cert-row');
  rows.forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

/* =====================================================
   6. TOAST NOTIFICATIONS
   ===================================================== */
function showToast(msg, type = 'info') {
  const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' };
  const toast  = document.createElement('div');
  toast.className = `fixed bottom-6 right-6 z-50 px-5 py-3 rounded-lg text-white text-sm shadow-lg
    fade-in ${colors[type] || colors.info}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

/* =====================================================
   7. PRINT HELPERS
   ===================================================== */
function printArea(areaId) {
  const area = document.getElementById(areaId);
  if (!area) return;
  area.classList.add('print-area');
  window.print();
  area.classList.remove('print-area');
}

/* =====================================================
   8. VERIFY PAGE — ONLINE MANUAL SEARCH
   ===================================================== */
async function verifyManual(e) {
  if (e) e.preventDefault();
  const reportNum = document.getElementById('v-report')?.value.trim();
  const pin       = document.getElementById('v-pin')?.value.trim() || '';
  const resultDiv = document.getElementById('verify-result');

  if (!reportNum) { showToast('Please enter a Report Number.', 'error'); return; }

  resultDiv.innerHTML = `<div class="flex justify-center py-8">
    <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
    </svg>
  </div>`;

  try {
    let url = `/api/verify?report=${encodeURIComponent(reportNum)}`;
    if (pin) url += `&pin=${encodeURIComponent(pin)}`;
    const res  = await fetch(url);
    const data = await res.json();
    if (data.error) {
      resultDiv.innerHTML = `<div class="bg-white rounded-2xl shadow-2xl p-8 text-center fade-in">
        <div class="text-6xl mb-4">❌</div>
        <h3 class="text-xl font-bold text-red-600">Certificate Not Found</h3>
        <p class="text-gray-500 mt-2">${data.error}</p>
      </div>`;
    } else {
      renderVerifyResult(data, resultDiv);
    }
  } catch {
    resultDiv.innerHTML = `<p class="text-red-600 text-center py-8">Verification failed. Please try again.</p>`;
  }
}

function renderVerifyResult(data, container) {
  container.innerHTML = `
  <div class="fade-in bg-white rounded-2xl shadow-2xl overflow-hidden border-2 border-emerald-500/30 relative">
    <!-- Centered Background Watermark Logo -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-0 overflow-hidden">
      <img src="/static/logo.jpeg" alt="" class="w-56 h-56 sm:w-72 sm:h-72 md:w-80 md:h-80 object-contain rounded-full opacity-[0.07] select-none" onerror="this.style.display='none'"/>
    </div>

    <div class="bg-gradient-to-r from-emerald-600 to-teal-700 text-white flex flex-col sm:flex-row sm:items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4 gap-2.5 relative z-10">
      <div class="flex items-center gap-3">
        <span class="text-2xl sm:text-3xl">✅</span>
        <div>
          <h3 class="text-base sm:text-lg font-bold">Certificate Found — Online Verified</h3>
          <p class="text-xs text-emerald-100">Issued by ${data.institute || 'Indian Gemological Institute'}</p>
        </div>
      </div>
      <span class="self-start sm:self-auto bg-white/20 backdrop-blur-sm text-white text-[11px] sm:text-xs px-3 py-1 sm:px-3.5 sm:py-1.5 rounded-full font-bold uppercase tracking-wider shadow-inner">
        ✔ Verified
      </span>
    </div>
    <div class="p-4 sm:p-6 md:p-8 grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
      <div class="md:col-span-2 space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2.5 text-sm">
          ${row('Report No.', data.report_number)}
          ${row('Customer', data.customer_name)}
          ${row('Gemstone', data.gemstone_name)}
          ${row('Weight', data.weight_carat ? data.weight_carat + ' ct' : '')}
          ${row('Shape / Cut', data.shape_cut)}
          ${row('Color', data.color)}
          ${row('Refractive Index', data.refractive_index)}
          ${row('Specific Gravity', data.specific_gravity)}
          ${row('Hardness', data.hardness ? data.hardness + ' (Mohs)' : '')}
          ${row('Chemical Formula', data.chemical_formula)}
          ${row('Crystal System', data.crystal_system)}
          ${row('Issued On', data.created_at ? data.created_at.slice(0, 10) : '')}
          ${row('Institute', data.institute || 'Indian Gemological Institute')}
        </div>
        ${data.comments ? `<div class="bg-amber-50 border border-amber-200 rounded-xl p-3 sm:p-3.5 text-xs sm:text-sm text-amber-900"><strong class="text-amber-800">Gemologist's Remarks:</strong> ${data.comments}</div>` : ''}
      </div>
      <div class="w-full flex flex-col sm:flex-row md:flex-col items-center justify-center gap-4 bg-slate-50 rounded-xl p-4 border border-slate-200">
        ${data.image_url ? `<img src="${data.image_url}" class="w-36 h-36 sm:w-40 sm:h-40 object-cover rounded-xl border-2 border-white shadow-md" alt="Gemstone">` : ''}
        ${data.qr_url ? `<div class="text-center"><img src="${data.qr_url}" class="w-24 h-24 p-1 bg-white border border-gray-200 rounded-lg shadow-sm mx-auto" alt="QR Code"><span class="text-[10px] text-gray-400 font-mono mt-1 block">${data.report_number || ''}</span></div>` : ''}
        <p class="text-[11px] text-gray-400 text-center">For cryptographic offline verification, use the QR payload in the Offline tab.</p>
      </div>
    </div>
  </div>`;
}

function row(label, value) {
  return `<div class="flex justify-between sm:block border-b sm:border-0 pb-1 sm:pb-0"><span class="font-semibold text-gray-500">${label}:</span> <span class="text-gray-900 font-medium block sm:inline">${value || '—'}</span></div>`;
}

/* =====================================================
   9. VERIFY PAGE — OFFLINE QR SIGNATURE CHECK
   ===================================================== */
async function verifyOfflineQR() {
  const input     = document.getElementById('offline-qr-input');
  const resultDiv = document.getElementById('verify-result');
  const qrData    = (input?.value || '').trim();

  if (!qrData) {
    showToast('Paste a QR payload first.', 'error');
    return;
  }

  resultDiv.innerHTML = `<div class="flex justify-center py-8">
    <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
    </svg>
  </div>`;

  try {
    const res  = await fetch('/api/verify-qr', {
      method: 'POST',
      headers: csrfHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ qr_data: qrData }),
    });
    const data = await res.json();
    renderOfflineResult(data, resultDiv);
  } catch {
    resultDiv.innerHTML = `<div class="bg-white rounded-2xl shadow-2xl p-6">
      <div class="sig-invalid">❌ Verification request failed. Check your connection.</div>
    </div>`;
  }
}

function renderOfflineResult(data, container) {
  let statusHTML, statusClass;
  if (data.status === 'VALID') {
    statusClass = 'sig-valid';
    statusHTML  = `✅ ${data.status_label}`;
  } else if (data.status === 'LEGACY') {
    statusClass = 'sig-legacy';
    statusHTML  = `⚠️ ${data.status_label}`;
  } else {
    statusClass = 'sig-invalid';
    statusHTML  = `❌ ${data.status_label}`;
  }

  const fields = data.status === 'VALID' ? `
    <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2.5 text-sm">
      ${row('Certificate No.', data.cert_no)}
      ${row('Institute', data.inst)}
      ${row('Gemstone', data.gem)}
      ${row('Weight', data.weight ? data.weight + ' ct' : '')}
      ${row('Shape / Cut', data.shape)}
      ${row('Color', data.color)}
      ${row('Refractive Index', data.ri)}
      ${row('Hardness (Mohs)', data.hardness)}
      ${row('Crystal System', data.crystal)}
      ${row('Issued To', data.issued_to)}
      ${row('Issue Date', data.date)}
      ${row('Key ID', data.kid)}
    </div>
    <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
      ℹ️ ${data.disclaimer || ''}
    </div>` : (data.reason ? `<p class="mt-3 text-sm text-gray-600">${data.reason}</p>` : '');

  container.innerHTML = `
  <div class="fade-in bg-white rounded-2xl shadow-2xl p-4 sm:p-6">
    <div class="${statusClass}">${statusHTML}</div>
    ${fields}
  </div>`;
}

/* =====================================================
   10. VERIFY PAGE — TAB SWITCHING
   ===================================================== */
function switchTab(tab) {
  const onlinePanel  = document.getElementById('panel-online');
  const offlinePanel = document.getElementById('panel-offline');
  const onlineBtn    = document.getElementById('tab-online');
  const offlineBtn   = document.getElementById('tab-offline');
  const resultDiv    = document.getElementById('verify-result');

  if (!onlinePanel) return;

  if (tab === 'online') {
    onlinePanel.classList.remove('hidden');
    offlinePanel?.classList.add('hidden');
    onlineBtn?.classList.add('tab-active-btn');
    onlineBtn?.classList.remove('text-white/60');
    offlineBtn?.classList.remove('tab-active-btn');
    offlineBtn?.classList.add('text-white/60');
  } else {
    onlinePanel.classList.add('hidden');
    offlinePanel?.classList.remove('hidden');
    offlineBtn?.classList.add('tab-active-btn');
    offlineBtn?.classList.remove('text-white/60');
    onlineBtn?.classList.remove('tab-active-btn');
    onlineBtn?.classList.add('text-white/60');
  }
  if (resultDiv) resultDiv.innerHTML = '';
}

/* =====================================================
   11. CAMERA QR SCANNER (HTML5-QRCode)
   ===================================================== */
let html5QrScanner = null;

async function openCameraScanner() {
  const wrap = document.getElementById('camera-scanner-wrap');
  if (!wrap) return;

  if (typeof Html5Qrcode === 'undefined') {
    showToast('Camera scanner library not loaded. Please check your internet connection.', 'error');
    return;
  }

  wrap.classList.remove('hidden');

  try {
    if (html5QrScanner) {
      try {
        await html5QrScanner.stop();
        html5QrScanner.clear();
      } catch (e) {}
    }

    html5QrScanner = new Html5Qrcode('qr-reader');
    await html5QrScanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decodedText) => {
        handleScannedQR(decodedText);
      },
      () => {}
    );
  } catch (err) {
    showToast('Camera access denied or unavailable: ' + (err.message || err), 'error');
    wrap.classList.add('hidden');
  }
}

async function closeCameraScanner() {
  const wrap = document.getElementById('camera-scanner-wrap');
  if (wrap) wrap.classList.add('hidden');
  if (html5QrScanner) {
    try {
      await html5QrScanner.stop();
      html5QrScanner.clear();
    } catch (e) {}
    html5QrScanner = null;
  }
}

function handleScannedQR(text) {
  closeCameraScanner();
  showToast('QR Code Scanned successfully!', 'success');

  const cleanText = (text || '').trim();

  // 1. Check if it's a URL
  try {
    if (cleanText.includes('/verify?')) {
      const url = new URL(cleanText.startsWith('http') ? cleanText : window.location.origin + cleanText);
      const rp = url.searchParams.get('report');
      const pin = url.searchParams.get('pin');
      if (rp) {
        const ri = document.getElementById('v-report');
        const pi = document.getElementById('v-pin');
        if (ri) ri.value = rp;
        if (pi && pin) pi.value = pin;
        verifyManual(null);
        return;
      }
    }
  } catch (e) {}

  // 2. Check if it's JSON payload
  try {
    const obj = JSON.parse(cleanText);
    if (obj.cert_no || obj.report_number) {
      const ri = document.getElementById('v-report');
      if (ri) ri.value = obj.cert_no || obj.report_number;
      verifyManual(null);
      return;
    }
  } catch (e) {}

  // 3. Plain Report Number fallback
  const ri = document.getElementById('v-report');
  if (ri) ri.value = cleanText;
  verifyManual(null);
}

/* =====================================================
   12. INIT
   ===================================================== */
document.addEventListener('DOMContentLoaded', () => {
  setupDropZone();

  // Close clone modal on backdrop click
  document.getElementById('clone-modal')?.addEventListener('click', function(e) {
    if (e.target === this) closeCloneModal();
  });

  // Online verify form submit
  document.getElementById('verify-form')?.addEventListener('submit', verifyManual);

  // Auto-run online verify if URL has params and server-rendered result is not present
  const urlParams = new URLSearchParams(window.location.search);
  const rp = urlParams.get('report'), pin = urlParams.get('pin');
  const alreadyRendered = document.querySelector('#verify-result .fade-in');
  if (rp && !alreadyRendered) {
    const ri = document.getElementById('v-report'), pi = document.getElementById('v-pin');
    if (ri) ri.value = rp;
    if (pi && pin) pi.value = pin;
    verifyManual(null);
  }

  // Table search
  document.getElementById('table-search')?.addEventListener('input', filterTable);

  // If the "other" option was already selected on page load (e.g. form re-render),
  // show the input
  const sel = document.getElementById('gemstone_name');
  const otherWrap = document.getElementById('other-gemstone-wrap');
  if (sel && otherWrap && sel.value === '__other__') {
    otherWrap.style.display = 'block';
  }

  // Mobile sidebar drawer event listeners
  document.getElementById('sidebar-backdrop')?.addEventListener('click', () => toggleMobileSidebar(false));
  document.getElementById('sidebar-close-btn')?.addEventListener('click', () => toggleMobileSidebar(false));
  document.getElementById('mobile-menu-btn')?.addEventListener('click', () => toggleMobileSidebar(true));

  document.querySelectorAll('#sidebar .nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 1024) toggleMobileSidebar(false);
    });
  });
});

/* =====================================================
   13. MOBILE SIDEBAR DRAWER TOGGLE
   ===================================================== */
function toggleMobileSidebar(shouldOpen) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar) return;

  const isClosed = sidebar.classList.contains('-translate-x-full');
  const open = (typeof shouldOpen === 'boolean') ? shouldOpen : isClosed;

  if (open) {
    sidebar.classList.remove('-translate-x-full');
    backdrop?.classList.remove('hidden');
    document.body.classList.add('overflow-hidden', 'lg:overflow-auto');
  } else {
    sidebar.classList.add('-translate-x-full');
    backdrop?.classList.add('hidden');
    document.body.classList.remove('overflow-hidden', 'lg:overflow-auto');
  }
}

