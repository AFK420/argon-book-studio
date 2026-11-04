/**
 * Argon Book Studio Pro v2.0 - Master Typesetting & Publishing Frontend.
 * Powers:
 * 1. Live Book Design, Typography & Margin Inspector
 * 2. Click-to-Style Paragraph & In-World Block Controller
 * 3. Granular Image & Plate Inspector + Interactive Vector Callouts
 * 4. True WYSIWYG Spread Preview + Live PDF Raster Preview (PyMuPDF)
 * 5. Visual Pin-Dropper Callout Studio with Leader Pointers
 * 6. Image Print Lab with Split Before/After comparison slider
 * 7. Bird's-Eye Thumbnail Filmstrip & Short Ending Balancer
 * 8. Comprehensive Front & Back Matter Visual Editor (Map, Appendix, Glossary)
 * 9. Multi-Format Export Sync (PDF, DOCX, EPUB, Release ZIP)
 */

const state = {
  profiles: {},
  books: [],
  activeBookId: "book01",
  activeBook: null,
  manuscript: null,
  manifest: { assets: [] },
  settings: null,
  pagination: { spreads: [], pages: [], filmstrip: [], short_endings: [] },
  currentSpreadIndex: 1,
  showMargins: true,
  showBleed: false,
  showFilmstrip: true,
  zoomLevel: 1.0,
  activeLeftTab: "manifest", // 'manifest' or 'tree'
  activeRightTab: "geometry", // 'geometry', 'matter', 'export'
  viewMode: "html", // 'html' or 'pdf'
  activeEditingId: null,
  // 5-Step Sequential Wizard Pipeline State
  currentStep: 1,
  maxUnlockedStep: 1,
  layoutMode: "wizard", // 'wizard' (default) or 'studio'
  queueFilter: "all",   // 'all', 'ready', 'pending'
  drawerTab: "geometry", // 'geometry' or 'matter'
  isDrawerOpen: false,
  imageLabState: {
    assetId: null,
    filter_preset: "cyanotype_silver_plate",
    grain: 0.08,
    contrast: 1.35,
    vignette: 0.38,
    brightness: 1.0,
    target_dpi: 300,
    splitPercent: 50
  },
  pinStudioState: {
    assetId: null,
    callouts: [],
    activePinIndex: null,
    targetMode: false
  }
};

// ======================================================================
// API HELPERS & TOASTS
// ======================================================================
async function fetchAPI(endpoint, options = {}) {
  try {
    const res = await fetch(endpoint, options);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Request failed");
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    showToast(err.message, "error");
    throw err;
  }
}

function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = "position:fixed; top:18px; right:22px; z-index:9999; display:flex; flex-direction:column; gap:8px;";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const bg = type === "error" ? "#EF4444" : type === "success" ? "#10B981" : "#1E293B";
  const border = type === "error" ? "#B91C1C" : type === "success" ? "#059669" : "#3B82F6";
  toast.style.cssText = `background:${bg}; color:#FFF; border-left:4px solid ${border}; padding:8px 14px; border-radius:6px; font-size:0.82rem; box-shadow:0 4px 15px rgba(0,0,0,0.5); display:flex; align-items:center; gap:8px; transition:all 0.3s ease;`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ"}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// ======================================================================
// STUDIO INITIALIZATION & BOOK LOADING
// ======================================================================
async function initStudio() {
  try {
    const profilesRes = await fetchAPI("/api/profiles");
    state.profiles = profilesRes.profiles;

    const booksRes = await fetchAPI("/api/books");
    state.books = booksRes.books;
    state.activeBookId = booksRes.active_book_id || "book01";

    await loadBook(state.activeBookId);
    setupHeaderListeners();
    checkLocalAIStatus();
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

async function loadBook(bookId) {
  state.activeBookId = bookId;
  const data = await fetchAPI(`/api/book/${bookId}`);
  state.activeBook = data.profile;
  state.manuscript = data.manuscript;
  state.manifest = data.manifest;
  state.settings = data.settings;
  state.pagination = data.pagination;
  state.frontMatter = data.front_matter;
  if (state.currentSpreadIndex >= (state.pagination.spreads || []).length) {
    state.currentSpreadIndex = 1;
  }

  // If manuscript exists, unlock step 2
  if (state.manuscript && state.manuscript.chapters && state.manuscript.chapters.length > 0) {
    state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 2);
  }

  renderAll();
  applyLayoutMode();
}

function renderAll() {
  renderHeader();
  if (state.layoutMode === "wizard") {
    updateStepperUI();
    renderWizardStep();
  } else {
    renderLeftPanel();
    renderSpreadCanvas();
    renderFilmstrip();
    renderRightPanel();
  }
}

// ======================================================================
// 1. TOP HEADER & LAYOUT MODE CONTROLLER
// ======================================================================
function renderHeader() {
  const selector = document.getElementById("book-profile-select");
  if (selector) {
    selector.innerHTML = state.books.map(b => `
      <option value="${b.id}" ${b.id === state.activeBookId ? "selected" : ""}>
        ${b.short_title} (${(b.genre || '').split("/")[0].trim()})
      </option>
    `).join("");
  }

  const indicator = document.getElementById("active-profile-indicator");
  if (indicator && state.activeBook && state.settings) {
    const s = state.settings;
    const typo = s.typography || {};
    const bodyFont = typo.body_font_name || s.body_font || state.activeBook.body_font_name;
    const bodySize = typo.body_font_size_pt || s.font_size_pt || 11;
    const leading = typo.body_leading_pt || (bodySize * (s.line_height || 1.36));
    const accent = typo.accent_color || state.activeBook.accent_color || "#D97706";

    indicator.innerHTML = `
      <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${accent};"></span>
      <span style="font-weight:600;">${state.activeBook.short_title}</span>
      <span style="color:var(--text-dim); font-size:0.75rem;">${s.trim_width_in}×${s.trim_height_in}" • ${bodyFont} ${parseFloat(bodySize).toFixed(1)}pt/${parseFloat(leading).toFixed(1)}pt</span>
    `;
  }
}

function toggleLayoutMode() {
  state.layoutMode = state.layoutMode === "wizard" ? "studio" : "wizard";
  applyLayoutMode();
}

function applyLayoutMode() {
  const wizardWs = document.getElementById("wizard-workspace");
  const studioWs = document.getElementById("studio-workspace");
  const modeBtn = document.getElementById("mode-toggle-btn");
  const stepperBar = document.getElementById("stepper-bar");

  if (state.layoutMode === "wizard") {
    if (wizardWs) wizardWs.style.display = "block";
    if (studioWs) studioWs.style.display = "none";
    if (stepperBar) stepperBar.style.display = "flex";
    if (modeBtn) modeBtn.innerHTML = "🔧 Switch to Advanced 3-Panel Studio";
    updateStepperUI();
    renderWizardStep();
  } else {
    if (wizardWs) wizardWs.style.display = "none";
    if (studioWs) studioWs.style.display = "grid";
    if (stepperBar) stepperBar.style.display = "flex";
    if (modeBtn) modeBtn.innerHTML = "🧙 Switch to 5-Step Pipeline";
    renderLeftPanel();
    renderSpreadCanvas();
    renderFilmstrip();
    renderRightPanel();
  }
}

function setupHeaderListeners() {
  const profileSelect = document.getElementById("book-profile-select");
  if (profileSelect) {
    profileSelect.addEventListener("change", (e) => selectTheme(e.target.value));
  }

  const dropzone = document.getElementById("step1-upload-dropzone");
  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleWizardManuscriptUpload({ target: { files: e.dataTransfer.files } });
      }
    });
  }
}

// ======================================================================
// 2. SEQUENTIAL 5-STEP PIPELINE CONTROLLER
// ======================================================================
function goToStep(stepNum) {
  if (stepNum > state.maxUnlockedStep && stepNum > state.currentStep) {
    showToast(`Complete Stage 0${state.currentStep} to unlock Stage 0${stepNum}.`, "warning");
    return;
  }
  state.currentStep = stepNum;
  updateStepperUI();
  renderWizardStep();
}

function updateStepperUI() {
  for (let i = 1; i <= 5; i++) {
    const btn = document.getElementById(`step-btn-${i}`);
    const num = document.getElementById(`step-num-${i}`);
    const line = document.getElementById(`line-${i}`);

    if (!btn || !num) continue;

    btn.classList.remove("active", "completed", "pending");

    if (i === state.currentStep) {
      btn.classList.add("active");
      num.innerText = `${i}`;
    } else if (i < state.currentStep) {
      btn.classList.add("completed");
      num.innerText = "✓";
    } else if (i <= state.maxUnlockedStep) {
      btn.classList.add("completed");
      num.innerText = `${i}`;
    } else {
      btn.classList.add("pending");
      num.innerText = `${i}`;
    }

    if (line) {
      if (i < state.currentStep) {
        line.classList.add("completed");
      } else {
        line.classList.remove("completed");
      }
    }
  }
}

function renderWizardStep() {
  for (let i = 1; i <= 5; i++) {
    const view = document.getElementById(`wizard-step-${i}`);
    if (view) {
      view.style.display = (i === state.currentStep) ? "flex" : "none";
    }
  }

  if (state.currentStep === 1) renderStep1();
  else if (state.currentStep === 2) renderStep2();
  else if (state.currentStep === 3) renderStep3();
  else if (state.currentStep === 4) renderStep4();
  else if (state.currentStep === 5) renderStep5();
}

// --- STEP 1: THEME & MANUSCRIPT UPLOAD ---
const BOOK_PROFILE_DETAILS = {
  book01: {
    title: "The Last Forty Minutes of Cormac Vane",
    subtitle: "A Speculative Forensic Mystery",
    genre: "Gaslamp Speculative Forensic Mystery",
    fonts: "Cinzel & EB Garamond",
    colors: ["#1B365D", "#B8860B", "#FBF8F1"],
    containers: "Inquest Writs & Sensory Draws"
  },
  book02: {
    title: "The Fourteen-Hour Barometer",
    subtitle: "A Chronometric Island Thriller and Speculative Romance",
    genre: "Chronometric Island Thriller & Speculative Romance",
    fonts: "Oswald & Lora",
    colors: ["#1E2229", "#00A896", "#F5F6F8"],
    containers: "Welsh Slate & Telemetry Equations"
  },
  book03: {
    title: "The Dead-Room Transcripts",
    subtitle: "A Locked-Room Mystery and Acoustic Forensic Thriller",
    genre: "Locked-Room Mystery & Acoustic Forensic Thriller",
    fonts: "JetBrains Mono & Source Serif 4",
    colors: ["#0F172A", "#38BDF8", "#F8FAFC"],
    containers: "DAW Audio Transcripts & FSK Payloads"
  },
  book04: {
    title: "The Salt Orchard of Saint Jude",
    subtitle: "An Ecological & Institutional Gothic Mystery",
    genre: "Ecological & Institutional Southern Gothic Mystery",
    fonts: "Cormorant Garamond & Crimson Pro",
    colors: ["#2C402E", "#D97706", "#FCFAF2"],
    containers: "Pelham Ledgers & Archival Journals"
  },
  book05: {
    title: "The Provenance of Ashes",
    subtitle: "An Epigraphic Crime & Field Excavation Thriller",
    genre: "Archaeometric & Epigraphic Geopolitical Thriller",
    fonts: "Cinzel Decorative & Source Serif 4",
    colors: ["#5A2A18", "#C98A2C", "#FAF6EE"],
    containers: "Cuneiform Tablets & Cedar Note Blocks"
  }
};

function renderStep1() {
  const grid = document.getElementById("step1-theme-grid");
  if (!grid) return;

  const books = state.books.length > 0 ? state.books : [
    { id: "book01", short_title: "Cormac Vane" },
    { id: "book02", short_title: "Fourteen-Hour Barometer" },
    { id: "book03", short_title: "Dead-Room Transcripts" },
    { id: "book04", short_title: "Salt Orchard" },
    { id: "book05", short_title: "Provenance of Ashes" }
  ];

  grid.innerHTML = books.map(b => {
    const meta = BOOK_PROFILE_DETAILS[b.id] || {
      title: b.title || b.short_title,
      genre: b.genre || "Illustrated Edition",
      fonts: "Serif & Sans",
      colors: ["#1B365D", "#D97706", "#FAF7F0"],
      containers: "In-World Documents"
    };
    const isSelected = b.id === state.activeBookId;
    return `
      <div class="theme-card ${isSelected ? 'selected' : ''}" onclick="selectTheme('${b.id}')">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="theme-card-badge" style="background:${meta.colors[0]}; color:#FFF;">${b.id.toUpperCase()}</span>
            ${isSelected ? '<span style="color:#10B981; font-weight:800; font-size:0.75rem;">✓ ACTIVE</span>' : ''}
          </div>
          <div class="theme-card-title">${meta.title}</div>
          <div class="theme-card-genre">${meta.genre}</div>
        </div>
        <div class="theme-card-meta">
          <div><strong style="color:#D1D5DB;">Fonts:</strong> ${meta.fonts}</div>
          <div><strong style="color:#D1D5DB;">Containers:</strong> ${meta.containers}</div>
          <div class="theme-card-swatches">
            ${meta.colors.map(c => `<span class="theme-swatch" style="background:${c};"></span>`).join('')}
          </div>
        </div>
      </div>
    `;
  }).join('');

  const sampleName = document.getElementById("step1-sample-name");
  if (sampleName && state.activeBook) {
    sampleName.innerText = state.activeBook.short_title || "Active Book";
  }

  const parseStatus = document.getElementById("step1-parse-status");
  const continueBtn = document.getElementById("step1-continue-btn");
  if (state.manuscript && state.manuscript.chapters && state.manuscript.chapters.length > 0) {
    const chCount = state.manuscript.chapters.length;
    let pCount = 0;
    state.manuscript.chapters.forEach(ch => {
      pCount += (ch.elements || []).filter(el => el.type === "paragraph" || el.type === "container").length;
    });
    if (parseStatus) {
      parseStatus.style.display = "flex";
      parseStatus.innerText = `✓ Parsed ${chCount} Chapter${chCount === 1 ? '' : 's'} and ${pCount} Paragraphs`;
    }
    if (continueBtn) continueBtn.disabled = false;
  }
}

async function selectTheme(bookId) {
  if (state.activeBookId === bookId && state.activeBook) return;
  showToast(`Switching to ${bookId.toUpperCase()} theme profile...`, "info");
  await loadBook(bookId);
  renderStep1();
}

function handleHeaderProfileChange(bookId) {
  selectTheme(bookId);
}

// --- DYNAMIC PROJECT CREATOR MODAL ---
function openCreateProjectModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-card" style="max-width:540px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3>📖 Create New Book Project</h3>
          <button class="btn-close-modal" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
          <form id="create-project-form" onsubmit="submitCreateProject(event)" style="display:flex; flex-direction:column; gap:14px;">
            <div>
              <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
                BOOK TITLE *
              </label>
              <input type="text" id="new-project-title" required placeholder="e.g. The Chronometric Crypt"
                     style="width:100%; box-sizing:border-box; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.88rem;">
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <div>
                <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
                  AUTHOR
                </label>
                <input type="text" id="new-project-author" placeholder="e.g. Margaret Sterling"
                       style="width:100%; box-sizing:border-box; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.88rem;">
              </div>
              <div>
                <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
                  SHORT TITLE / SLUG
                </label>
                <input type="text" id="new-project-short-title" placeholder="e.g. Chronometric Crypt"
                       style="width:100%; box-sizing:border-box; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.88rem;">
              </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <div>
                <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
                  GENRE & AESTHETIC
                </label>
                <input type="text" id="new-project-genre" placeholder="e.g. Victorian Steampunk"
                       style="width:100%; box-sizing:border-box; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.88rem;">
              </div>
              <div>
                <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
                  BASE AESTHETIC THEME
                </label>
                <select id="new-project-theme-base" style="width:100%; box-sizing:border-box; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.88rem;">
                  <option value="book01">Book 01: Cormac Vane (Cinzel & Garamond / Cyanotype)</option>
                  <option value="book02">Book 02: Fourteen-Hour Barometer (Oswald & Lora / Slate)</option>
                  <option value="book03">Book 03: Dead-Room Transcripts (Mono & Source / FSK)</option>
                  <option value="book04">Book 04: Salt Orchard (Cormorant & Crimson / Ledger)</option>
                  <option value="book05">Book 05: Provenance of Ashes (Decorative & Source / Cuneiform)</option>
                </select>
              </div>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
              <button type="button" class="btn-secondary-action" onclick="closeModal()">
                Cancel
              </button>
              <button type="submit" id="btn-submit-new-project" class="btn-wizard-primary" style="font-weight:700;">
                🚀 Create Project
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
}

function closeCreateProjectModal(event) {
  closeModal(event);
}

async function submitCreateProject(event) {
  event.preventDefault();
  const btn = document.getElementById("btn-submit-new-project");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Creating Project...";
  }

  const title = document.getElementById("new-project-title")?.value.trim();
  const author = document.getElementById("new-project-author")?.value.trim() || "Anonymous";
  const shortTitle = document.getElementById("new-project-short-title")?.value.trim() || title;
  const genre = document.getElementById("new-project-genre")?.value.trim() || "Literary Fiction";
  const themeBase = document.getElementById("new-project-theme-base")?.value || "book01";

  if (!title) {
    showToast("Please enter a book title", "warning");
    if (btn) { btn.disabled = false; btn.innerText = "🚀 Create Project"; }
    return;
  }

  showToast(`Creating custom project: "${title}"...`, "info");

  try {
    const res = await fetch("/api/projects/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        author: author,
        short_title: shortTitle,
        genre: genre,
        theme_base: themeBase
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Project creation failed" }));
      throw new Error(err.detail || "Project creation failed");
    }

    const data = await res.json();
    showToast(`✓ Custom project "${title}" created successfully!`, "success");

    closeModal();

    // Reload books list
    const booksRes = await fetchAPI("/api/books");
    state.books = booksRes.books;

    // Load newly created book
    await loadBook(data.book_id);

    // Refresh UI
    renderHeader();
    renderStep1();
    goToStep(1);
  } catch (err) {
    console.error("Create project error:", err);
    showToast(`Failed to create project: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🚀 Create Project";
    }
  }
}

async function handleWizardManuscriptUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  showToast(`Parsing manuscript: ${file.name}...`, "info");

  const formData = new FormData();
  formData.append("book_id", state.activeBookId);
  formData.append("file", file);

  try {
    const res = await fetch("/api/manuscript/upload", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    state.manuscript = data.parsed;
    state.pagination = data.pagination;
    state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 2);
    showToast(`✓ Parsed ${data.parsed.chapters?.length || 0} chapters and ${data.parsed.total_words || 0} words!`, "success");
    await loadBook(state.activeBookId);
    goToStep(2);
  } catch (err) {
    console.error(err);
    showToast(`Error parsing manuscript: ${err.message}`, "error");
  }
}

async function useSampleManuscriptForActiveBook() {
  showToast(`Loading built-in sample manuscript for ${state.activeBookId.toUpperCase()}...`, "info");
  await loadBook(state.activeBookId);
  state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 2);
  showToast("✓ Built-in sample manuscript loaded!", "success");
  goToStep(2);
}

// --- STEP 2: AUTO-STYLE & BLUEPRINT ---
function updateTargetPlatesBadge(val) {
  const badge = document.getElementById("target-plates-badge");
  if (badge) badge.innerText = `${val} Plates`;
  const btn = document.getElementById("btn-auto-plan-manifest");
  if (btn) btn.innerText = `🧠 AI Auto-Plan All ${val} Book Illustrations (Qwen 2.5:14b)`;
}

function renderStep2() {
  if (!state.manuscript) return;
  checkLocalAIStatus();

  const chCount = state.manuscript.chapters?.length || 0;
  const wordCount = state.manuscript.total_words || 0;
  const slotCount = state.manifest.assets?.length || 16;

  document.getElementById("step2-diag-chapters").innerText = chCount;
  document.getElementById("step2-diag-words").innerText = wordCount.toLocaleString();
  document.getElementById("step2-diag-slots").innerText = slotCount;

  const anchorBadge = document.getElementById("step2-anchor-badge");
  if (anchorBadge) {
    anchorBadge.innerText = `✓ ${slotCount} Illustration Slots Anchored`;
  }

  const slider = document.getElementById("target-plates-slider");
  if (slider && !slider.matches(":active")) {
    slider.value = slotCount;
    updateTargetPlatesBadge(slotCount);
  }

  const containerCounts = {
    inworld_writ: 0,
    welsh_slate: 0,
    audio_transcript: 0,
    archival_journal: 0,
    scientific_formula: 0,
    cuneiform_clause: 0,
    sensory_draw: 0
  };

  (state.manuscript.chapters || []).forEach(ch => {
    (ch.elements || []).forEach(el => {
      const btype = el.block_type || (el.type === "container" ? el.tag : null);
      if (el.tag === "sensory-draw" || btype === "sensory_draw") {
        containerCounts.sensory_draw++;
      } else if (btype && containerCounts[btype] !== undefined) {
        containerCounts[btype]++;
      }
    });
  });

  const chipsContainer = document.getElementById("step2-container-chips");
  if (chipsContainer) {
    const labels = {
      inworld_writ: "Inquest Writs / Warrants",
      sensory_draw: "Vesper Sensory Draws",
      welsh_slate: "Welsh Slate Blocks",
      audio_transcript: "DAW Audio Transcripts",
      archival_journal: "Pelham Archival Ledgers",
      scientific_formula: "Telemetry Equations",
      cuneiform_clause: "Cuneiform Clauses"
    };

    let chipsHtml = "";
    Object.keys(containerCounts).forEach(key => {
      const count = containerCounts[key];
      chipsHtml += `
        <span class="diag-chip ${count > 0 ? 'active' : ''}">
          <strong>${count}</strong> ${labels[key] || key}
        </span>
      `;
    });
    chipsContainer.innerHTML = chipsHtml;
  }
}

async function useBuiltinBlueprint() {
  showToast("Anchoring built-in blueprint to manuscript...", "info");
  try {
    const res = await fetch(`/api/manifest/${state.activeBookId}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ use_builtin: true })
    });
    if (!res.ok) throw new Error("Failed to anchor blueprint");
    const data = await res.json();
    state.manifest = data.manifest;
    state.pagination = data.pagination;
    const count = state.manifest?.assets?.length || 16;
    showToast(`✓ ${count} illustration slots anchored to manuscript paragraphs!`, "success");
    renderStep2();
  } catch (err) {
    showToast(`Error anchoring blueprint: ${err.message}`, "error");
  }
}

async function handleWizardManifestUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  await importManifestFile(file);
  event.target.value = "";
  renderStep2();
}

async function handleStudioManifestUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  await importManifestFile(file);
  event.target.value = "";
}

async function runAutoStyle() {
  const btn = document.getElementById("step2-autostyle-btn");
  if (btn) btn.disabled = true;
  showToast("Running 1-Click Auto-Styler & locking blueprint...", "info");

  try {
    const res = await fetch(`/api/manuscript/${state.activeBookId}/auto-style`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("Auto-styler request failed");
    const data = await res.json();

    state.manuscript = data.manuscript;
    state.pagination = data.pagination;
    state.frontMatter = data.front_matter;
    state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 3);

    const banner = document.getElementById("step2-autostyle-result");
    if (banner) {
      banner.style.display = "block";
      banner.innerHTML = `
        <strong>✓ Auto-Style Successfully Applied:</strong><br>
        • Merged consecutive multi-line containers into unified blocks.<br>
        • Styled Vesper sensory draws and formatted in-world containers.<br>
        • Enforced flush-left indents on chapter opening paragraphs & scene breaks.<br>
        • Initialized front and back matter defaults.
      `;
    }

    showToast("✓ Auto-Style Locked! Advancing to Step 3...", "success");
    setTimeout(() => {
      goToStep(3);
    }, 900);
  } catch (err) {
    console.error(err);
    showToast(`Auto-style error: ${err.message}`, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// --- STEP 3: ILLUSTRATION PRODUCTION QUEUE ---
function setQueueFilter(filter) {
  state.queueFilter = filter;
  ["all", "ready", "pending"].forEach(f => {
    document.getElementById(`filter-chip-${f}`)?.classList.toggle("active", f === filter);
  });
  renderStep3();
}

function renderStep3() {
  const assets = state.manifest.assets || [];
  const isReady = (a) => a.filter_applied || a.raw_image_path || (a.image_url && !a.image_url.includes("placeholder"));

  const readyCount = assets.filter(isReady).length;
  const totalCount = assets.length;
  const pct = totalCount > 0 ? Math.round((readyCount / totalCount) * 100) : 0;

  document.getElementById("step3-ready-label").innerText = `${readyCount} of ${totalCount} Illustrations Ready`;
  document.getElementById("step3-pct-label").innerText = `${pct}%`;
  document.getElementById("step3-progress-bar").style.width = `${pct}%`;

  document.getElementById("filter-chip-all").innerText = `All Slots (${totalCount})`;
  document.getElementById("filter-chip-ready").innerText = `✓ Ready & Filtered (${readyCount})`;
  document.getElementById("filter-chip-pending").innerText = `⏳ Needs Artwork (${totalCount - readyCount})`;

  const rewriteBtn = document.getElementById("btn-rewrite-all-prompts");
  if (rewriteBtn) {
    rewriteBtn.innerText = `🧠 Rewrite All ${totalCount} Prompts (Qwen 2.5)`;
  }

  const filtered = assets.filter(a => {
    if (state.queueFilter === "ready") return isReady(a);
    if (state.queueFilter === "pending") return !isReady(a);
    return true;
  });

  const grid = document.getElementById("step3-cards-grid");
  if (!grid) return;

  grid.innerHTML = filtered.map((asset, idx) => {
    const ready = isReady(asset);
    const pinCount = (asset.vector_callouts || []).length;

    return `
      <div class="queue-card" 
           ondragover="handleDragOver(event)" 
           ondragleave="handleDragLeave(event)" 
           ondrop="handleDropQueueImage(event, '${asset.id}')">
        <div class="queue-card-header">
          <div class="queue-card-loc">
            Slot #${idx + 1} • ${asset.anchor} • ${asset.placement}
          </div>
          <div class="queue-card-status ${ready ? 'ready' : 'pending'}">
            ${ready ? '✓ 300 DPI Filtered' : '⏳ Needs Artwork'}
          </div>
        </div>

        <div style="font-size:0.82rem; font-weight:700; color:#FFF;">${asset.title || 'Illustration Plate'}</div>

        <div style="display:flex; gap:6px; flex-wrap:wrap; margin:4px 0;">
          ${asset.featured_character ? `<span class="badge-char">👤 ${asset.featured_character}</span>` : ''}
          <span class="badge-res">📐 ${asset.aspect_ratio || '2:3'} • ${asset.target_resolution_px || '1875×2775 px (300 DPI)'}</span>
        </div>

        <div class="queue-prompt-box">
          <div class="queue-prompt-text">${asset.prompt || 'No prompt specified.'}</div>
          <button class="btn-copy-prompt" onclick="copyPromptFromBox(this)">
            📋 Copy Prompt
          </button>
        </div>

        <div class="queue-thumb-row">
          <img src="${asset.image_url}" class="queue-thumb-img" alt="Artwork Preview" onclick="openPlateInspector('${asset.id}')">
          <div class="queue-actions-col">
            <button class="btn-queue-action" style="background:rgba(217,119,6,0.18); border-color:#D97706; color:#FBBF24; font-weight:600;" onclick="enhanceSlotPrompt('${asset.id}', this)">
              ✨ Rewrite Prompt with Qwen 2.5
            </button>
            <button class="btn-queue-action" style="background:rgba(16,185,129,0.18); border-color:#10B981; color:#34D399; font-weight:600;" onclick="generateSlotWithFlux('${asset.id}', this)">
              ⚡ Generate with Local Flux
            </button>
            <input type="file" id="queue-file-${asset.id}" style="display:none;" accept="image/*" onchange="uploadQueueImage('${asset.id}', this.files[0])">
            <button class="btn-queue-action" onclick="document.getElementById('queue-file-${asset.id}').click()">
              📤 Drop / Upload Image
            </button>
            <button class="btn-queue-action" onclick="openFilterLab('${asset.id}')">
              🔍 Preview / Adjust Filter
            </button>
            <button class="btn-queue-action" onclick="openPinStudio('${asset.id}')">
              📍 Adjust Map Pins (${pinCount})
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 4);
}

async function handleDropQueueImage(event, assetId) {
  event.preventDefault();
  event.currentTarget.classList.remove("dragover");

  if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0];
    await uploadQueueImage(assetId, file);
  }
}

async function uploadQueueImage(assetId, file) {
  if (!file) return;
  await uploadImageFile(assetId, file);
  renderStep3();
}

async function handleStep3BatchUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  showToast(`Uploading & processing ${files.length} images at 300 DPI...`, "info");
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  try {
    const res = await fetch(`/api/assets/batch-upload/${state.activeBookId}`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`Batch processed: ${data.processed_count} artwork files filtered at 300 DPI!`, "success");
      if (data.manifest) {
        state.manifest = data.manifest;
      }
      if (data.pagination) {
        state.pagination = data.pagination;
      }
      renderAll();
      if (state.currentStep === 3) {
        renderStep3();
      }
    } else {
      showToast(`Batch upload error: ${data.detail || "Failed to process images"}`, "error");
    }
  } catch (err) {
    showToast(`Batch upload failed: ${err.message}`, "error");
  } finally {
    event.target.value = "";
  }
}

async function copyTextToClipboard(text, btn) {
  if (!text) {
    showToast("No prompt to copy", "warning");
    return false;
  }

  let copied = false;

  // 1. Try modern navigator.clipboard API if available and permitted
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (e) {
      console.warn("navigator.clipboard.writeText blocked or failed, using textarea fallback:", e);
    }
  }

  // 2. Robust fallback using a temporary hidden textarea + execCommand('copy')
  if (!copied) {
    try {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.top = "0";
      textarea.style.left = "0";
      textarea.style.width = "2em";
      textarea.style.height = "2em";
      textarea.style.padding = "0";
      textarea.style.border = "none";
      textarea.style.outline = "none";
      textarea.style.boxShadow = "none";
      textarea.style.background = "transparent";
      textarea.setAttribute("readonly", "");
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);
      copied = document.execCommand("copy");
      document.body.removeChild(textarea);
    } catch (err) {
      console.warn("document.execCommand copy fallback failed:", err);
    }
  }

  // 3. Last-resort fallback prompt
  if (!copied) {
    try {
      window.prompt("Press Ctrl+C, Enter to copy prompt:", text);
      copied = true;
    } catch (e) {
      copied = false;
    }
  }

  if (copied) {
    showToast("✓ Copied prompt to clipboard!", "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "✓ Copied!";
      btn.style.color = "#10B981";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.color = "";
      }, 1600);
    }
    return true;
  } else {
    showToast("Failed to copy to clipboard", "error");
    return false;
  }
}

function copyPromptText(text, btn) {
  return copyTextToClipboard(text, btn);
}

function copyPromptFromBox(btn) {
  if (!btn) return;
  const box = btn.closest(".queue-prompt-box");
  const textEl = box ? box.querySelector(".queue-prompt-text") : null;
  const text = textEl ? (textEl.innerText || textEl.textContent || "").trim() : "";
  copyTextToClipboard(text, btn);
}

function copyAnchorFromCard(btn) {
  if (!btn) return;
  const card = btn.closest(".char-dossier-card");
  const codeEl = card ? card.querySelector(".char-anchor-code") : null;
  const text = codeEl ? (codeEl.innerText || codeEl.textContent || "").trim() : "";
  copyTextToClipboard(text, btn);
}

function copyTurnaroundFromCard(btn, charIdx) {
  let text = "";
  if (state.lastAIBlueprint && state.lastAIBlueprint.character_dossiers && state.lastAIBlueprint.character_dossiers[charIdx]) {
    text = state.lastAIBlueprint.character_dossiers[charIdx].turnaround_sheet_prompt || "";
  }
  if (!text && btn) {
    const card = btn.closest(".char-dossier-card");
    const codeEl = card ? card.querySelector(".char-anchor-code") : null;
    const anchor = codeEl ? (codeEl.innerText || codeEl.textContent || "").trim() : "";
    text = `Master 5-angle turnaround model sheet of ${anchor}, front view, 3/4 left, side profile, 3/4 right, back view. Neutral lighting, clean neutral studio gray background, ultra-consistent facial architecture, full body character sheet, line art drawing style.`;
  }
  copyTextToClipboard(text, btn);
}

function copyPlatePromptFromCard(btn, plateIdx) {
  let text = "";
  if (state.lastAIBlueprint && state.lastAIBlueprint.assets && state.lastAIBlueprint.assets[plateIdx]) {
    text = state.lastAIBlueprint.assets[plateIdx].prompt || "";
  }
  if (!text && btn) {
    const card = btn.closest(".ai-plate-card");
    const promptEl = card ? card.querySelector(".ai-plate-prompt") : null;
    if (promptEl) {
      text = (promptEl.innerText || promptEl.textContent || "").trim();
      if (text.startsWith('"') && text.endsWith('"')) {
        text = text.substring(1, text.length - 1);
      }
    }
  }
  copyTextToClipboard(text, btn);
}

// ======================================================================
// AI FLUX PROMPT ARCHITECT & LOCAL FLUX BRIDGE HANDLERS
// ======================================================================

async function enhanceSlotPrompt(assetId, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Enhancing...";
  }
  showToast(`Rewriting prompt for ${assetId} with Qwen 2.5:14b...`, "info");
  
  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/enhance-prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_id: assetId, all_slots: false })
    });
    const data = await res.json();
    if (data.status === "success" && data.manifest) {
      state.manifest = data.manifest;
      renderStep3();
      showToast("✓ Rewrote 5-layer Flux prompt with Qwen 2.5!", "success");
    } else {
      showToast(data.detail || "Failed to rewrite prompt", "error");
    }
  } catch (err) {
    showToast(`AI prompt rewrite failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "✨ Rewrite Prompt with Qwen 2.5";
    }
  }
}

async function enhanceAllPromptsWithQwen(btn) {
  const count = state.manifest?.assets?.length || 16;
  if (btn) {
    btn.disabled = true;
    btn.innerText = `⏳ Rewriting ${count} Prompts...`;
  }
  showToast(`Rewriting all ${count} illustration prompts with Qwen 2.5:14b...`, "info");

  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/enhance-prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ all_slots: true })
    });
    const data = await res.json();
    if (data.status === "success" && data.manifest) {
      state.manifest = data.manifest;
      renderStep3();
      showToast(`✓ Rewrote ${data.enhanced_count || count} prompts into 5-layer Flux T5 prose!`, "success");
    } else {
      showToast(data.detail || "Failed to enhance all prompts", "error");
    }
  } catch (err) {
    showToast(`Batch prompt rewrite failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      const finalCount = state.manifest?.assets?.length || count;
      btn.innerText = `🧠 Rewrite All ${finalCount} Prompts (Qwen 2.5)`;
    }
  }
}

async function generateSlotWithFlux(assetId, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⚡ Generating...";
  }
  showToast(`Generating plate for ${assetId} with local Flux...`, "info");

  try {
    const res = await fetch(`/api/flux/${state.activeBookId}/generate/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.status === "success" && data.asset) {
      const idx = state.manifest.assets.findIndex(a => a.id === assetId);
      if (idx !== -1) {
        state.manifest.assets[idx] = data.asset;
      }
      renderStep3();
      showToast("✓ Flux plate generated & 300 DPI filtered!", "success");
    } else {
      showToast(data.detail || "Failed to generate image with Flux", "error");
    }
  } catch (err) {
    showToast(`Flux generation failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "⚡ Generate with Local Flux";
    }
  }
}

async function batchGeneratePendingFlux(btn) {
  const assets = state.manifest?.assets || [];
  const pending = assets.filter(a => !a.filter_applied || (a.image_url && a.image_url.includes("placeholder")));

  if (pending.length === 0) {
    showToast("All illustration plates are already filtered and ready!", "info");
    return;
  }

  const pWrap = document.getElementById("flux-batch-progress-wrap");
  const pFill = document.getElementById("flux-batch-progress-fill");
  const pPct = document.getElementById("flux-batch-pct");
  const pText = document.getElementById("flux-batch-status-text");

  if (pWrap) pWrap.style.display = "block";
  if (btn) btn.disabled = true;

  let completed = 0;
  for (let i = 0; i < pending.length; i++) {
    const asset = pending[i];
    const pct = Math.round((i / pending.length) * 100);
    if (pFill) pFill.style.width = `${pct}%`;
    if (pPct) pPct.innerText = `${pct}%`;
    if (pText) pText.innerText = `⚡ Generating slot #${i + 1}/${pending.length}: ${asset.title || asset.id}...`;

    try {
      const res = await fetch(`/api/flux/${state.activeBookId}/generate/${asset.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.status === "success" && data.asset) {
        const aIdx = state.manifest.assets.findIndex(a => a.id === asset.id);
        if (aIdx !== -1) {
          state.manifest.assets[aIdx] = data.asset;
        }
        completed++;
      }
    } catch (e) {
      console.warn(`Error generating plate ${asset.id}:`, e);
    }
  }

  if (pFill) pFill.style.width = "100%";
  if (pPct) pPct.innerText = "100%";
  if (pText) pText.innerText = `✓ Complete: Generated ${completed} plates with Local Flux!`;

  setTimeout(() => {
    if (pWrap) pWrap.style.display = "none";
    if (btn) btn.disabled = false;
  }, 2500);

  renderStep3();
  renderAll();
  showToast(`✓ Batch complete: ${completed} plates generated with Local Flux!`, "success");
}

async function autoPlanFullBookManifestAI(btn) {
  const targetCount = parseInt(document.getElementById("target-plates-slider")?.value || "16", 10);
  if (btn) {
    btn.disabled = true;
    btn.innerText = `⏳ Planning ${targetCount} Assets with Qwen 2.5...`;
  }
  showToast(`Autonomous Art Director (Qwen 2.5:14b) planning ${targetCount}-asset pacing rhythm...`, "info");

  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/auto-plan-manifest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_count: targetCount })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (data.manifest) state.manifest = data.manifest;
      if (data.pagination) state.pagination = data.pagination;
      const count = state.manifest?.assets?.length || targetCount;
      showToast(`✓ AI Auto-Planned ${count} visual assets with Qwen 2.5:14b!`, "success");
      renderAll();
      if (state.currentStep === 2) renderStep2();
      if (state.currentStep === 3) renderStep3();
    } else {
      showToast(data.detail || "Auto-planning failed", "error");
    }
  } catch (err) {
    showToast(`AI Auto-plan failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      const curCount = parseInt(document.getElementById("target-plates-slider")?.value || "16", 10);
      btn.innerText = `🧠 AI Auto-Plan All ${curCount} Book Illustrations (Qwen 2.5:14b)`;
    }
  }
}

// ======================================================================
// AI INTERIOR DESIGN STUDIO MODAL
// ======================================================================

function openAiDesignStudioModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const interior = state.settings?.interior_design || {};
  const currentOpener = interior.chapter_opener_layout || "classic_centered";
  const currentBorder = interior.page_border_style || "none";
  const currentFolio = interior.folio_style || "classic_centered";
  const bible = state.settings?.visual_bible || {};
  const chars = bible.characters || {};

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:780px; max-width:94vw; max-height:88vh; display:flex; flex-direction:column; padding:0; overflow:hidden;" onclick="event.stopPropagation()">
        
        <!-- Header -->
        <div style="padding:16px 20px; background:#0F172A; border-bottom:1px solid #334155; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h3 style="margin:0; font-size:1.05rem; color:#38BDF8; display:flex; align-items:center; gap:8px;">
              🎨 AI Interior Book Design & Visual Architecture Studio
            </h3>
            <div style="font-size:0.75rem; color:#94A3B8; margin-top:2px;">
              Powered by Local Ollama (Qwen 2.5:14b) • Geometry, Ornaments & Visual Continuity
            </div>
          </div>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.4rem; cursor:pointer;">&times;</button>
        </div>

        <!-- Tab Strip -->
        <div style="display:flex; gap:2px; background:#1E293B; border-bottom:1px solid #334155; padding:4px 16px 0 16px;">
          <button class="ai-studio-tab active" id="tab-btn-ornaments" onclick="switchAiDesignTab('ornaments')">✨ SVG Ornaments</button>
          <button class="ai-studio-tab" id="tab-btn-containers" onclick="switchAiDesignTab('containers')">📜 Custom Artifact Boxes</button>
          <button class="ai-studio-tab" id="tab-btn-bible" onclick="switchAiDesignTab('bible')">👤 Visual Continuity Bible</button>
          <button class="ai-studio-tab" id="tab-btn-architecture" onclick="switchAiDesignTab('architecture')">🏛️ Interior Architecture & Framing</button>
        </div>

        <!-- Body Area -->
        <div style="padding:20px; overflow-y:auto; flex:1; background:#0B1329;">
          
          <!-- TAB 1: SVG ORNAMENTS -->
          <div id="ai-tab-ornaments" class="ai-studio-pane" style="display:block;">
            <div style="font-size:0.82rem; color:#94A3B8; margin-bottom:12px;">
              Generate bespoke Victorian vector ornaments (dividers and chapter end tailpieces) matching any thematic motif via Qwen 2.5:14b.
            </div>
            
            <div style="margin-bottom:12px;">
              <label style="font-size:0.75rem; color:#FBBF24; font-weight:700; text-transform:uppercase;">Describe Desired Ornament Motif</label>
              <input type="text" id="ai-ornament-motif-input" class="studio-input" style="width:100%; margin-top:4px;" value="An antique brass sextant crossed with an eagle quill pen and nautical caliper">
            </div>

            <div style="margin-bottom:16px;">
              <button class="btn-secondary-action" style="background:#0F766E; border-color:#0D9488; color:#FFF; font-weight:700;" onclick="generateAiSvgOrnament(this)">
                ✨ Generate Vector Ornament (Qwen 2.5)
              </button>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
              <div style="background:#020617; border:1px solid #1E293B; border-radius:6px; padding:12px; text-align:center;">
                <div style="font-size:0.72rem; color:#64748B; text-transform:uppercase; margin-bottom:8px;">Live Scene-Break Divider Preview (240 × 32)</div>
                <div id="ai-svg-scene-preview" style="background:#FFF; padding:12px; border-radius:4px; min-height:48px; display:flex; align-items:center; justify-content:center;">
                  ${state.settings?.interior_design?.custom_svg_scene_break || state.currentProfile?.scene_break_svg || 'No custom SVG loaded.'}
                </div>
              </div>
              <div style="background:#020617; border:1px solid #1E293B; border-radius:6px; padding:12px; text-align:center;">
                <div style="font-size:0.72rem; color:#64748B; text-transform:uppercase; margin-bottom:8px;">Live Chapter Tailpiece Preview (160 × 80)</div>
                <div id="ai-svg-tail-preview" style="background:#FFF; padding:12px; border-radius:4px; min-height:48px; display:flex; align-items:center; justify-content:center;">
                  ${state.settings?.interior_design?.custom_svg_tailpiece || state.currentProfile?.tailpiece_svg || 'No custom tailpiece loaded.'}
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: CUSTOM CONTAINERS -->
          <div id="ai-tab-containers" class="ai-studio-pane" style="display:none;">
            <div style="font-size:0.82rem; color:#94A3B8; margin-bottom:12px;">
              Describe any in-world document type, telegram, or laboratory log. Qwen 2.5:14b will generate the CSS typography rules and register it into the Paragraph Inspector.
            </div>

            <div style="margin-bottom:12px;">
              <label style="font-size:0.75rem; color:#FBBF24; font-weight:700; text-transform:uppercase;">Describe In-World Artifact Box</label>
              <input type="text" id="ai-container-motif-input" class="studio-input" style="width:100%; margin-top:4px;" value="1960s cold-war redacted intelligence cable with classified stamp and typewriter font">
            </div>

            <div style="margin-bottom:16px;">
              <button class="btn-secondary-action" style="background:#0F766E; border-color:#0D9488; color:#FFF; font-weight:700;" onclick="generateAiContainerCss(this)">
                ✨ Design Custom Container (Qwen 2.5)
              </button>
            </div>

            <div id="ai-container-preview-box" style="margin-bottom:12px; padding:12px; background:#020617; border:1px solid #1E293B; border-radius:6px;">
              <div style="font-size:0.72rem; color:#64748B; text-transform:uppercase; margin-bottom:8px;">Live Rendered Artifact Preview:</div>
              <div id="ai-container-rendered" style="background:#FFF; padding:12px; border-radius:4px; color:#000;">
                <div style="font-family:'JetBrains Mono', monospace; font-size:0.8rem; border-left:4px solid #1E293B; padding-left:8px;">
                  [SAMPLE TELEMETRY RECORD // DEEP-BRINE GRID LEVEL IV]
                </div>
              </div>
              <pre id="ai-container-css-code" style="margin-top:10px; font-size:0.72rem; color:#38BDF8; background:#0F172A; padding:8px; border-radius:4px; max-height:100px; overflow-y:auto;"></pre>
            </div>
          </div>

          <!-- TAB 3: VISUAL CONTINUITY BIBLE -->
          <div id="ai-tab-bible" class="ai-studio-pane" style="display:none;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <div style="font-size:0.82rem; color:#94A3B8;">
                Locked character physical constants and period architecture injected into every Flux.1 prompt.
              </div>
              <button class="btn-secondary-action" style="font-size:0.75rem; padding:4px 10px;" onclick="reExtractVisualBible(this)">
                🧠 Re-Extract from Manuscript (Qwen 2.5)
              </button>
            </div>

            <div style="margin-bottom:12px;">
              <label style="font-size:0.75rem; color:#38BDF8; font-weight:700; text-transform:uppercase;">Art Medium Lock Prefix (FLUX.1)</label>
              <input type="text" id="ai-bible-medium-input" class="studio-input" style="width:100%; margin-top:4px;" value="${bible.art_medium_lock || '19th-century Victorian cyanotype and copperplate intaglio engraving on heavy cotton rag paper'}">
            </div>

            <div style="margin-bottom:16px;">
              <label style="font-size:0.75rem; color:#38BDF8; font-weight:700; text-transform:uppercase;">Setting Architecture & Lighting Physics</label>
              <textarea id="ai-bible-setting-input" class="studio-input" style="width:100%; height:60px; margin-top:4px; font-size:0.8rem;">${bible.setting_architecture || '1890s sub-polar basalt cliff port, riveted iron diving bells, gasoliers, frost-rimmed quartz'}</textarea>
            </div>

            <div style="font-size:0.75rem; color:#FBBF24; font-weight:700; text-transform:uppercase; margin-bottom:6px;">Locked Characters (${Object.keys(chars).length})</div>
            <div style="display:flex; flex-direction:column; gap:8px; max-height:200px; overflow-y:auto;">
              ${Object.entries(chars).map(([name, c]) => `
                <div style="background:#0F172A; border:1px solid #1E293B; border-radius:4px; padding:8px 12px; font-size:0.78rem;">
                  <strong style="color:#FFF;">👤 ${name} (${c.age || 'Adult'} yo)</strong>
                  <div style="color:#94A3B8; font-size:0.72rem; margin-top:2px;"><strong>Features:</strong> ${c.facial_features}</div>
                  <div style="color:#94A3B8; font-size:0.72rem;"><strong>Attire:</strong> ${c.signature_clothing}</div>
                  <div style="color:#94A3B8; font-size:0.72rem;"><strong>Tools/Marks:</strong> ${c.distinguishing_marks_or_tools}</div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- TAB 4: INTERIOR ARCHITECTURE & FRAMING -->
          <div id="ai-tab-architecture" class="ai-studio-pane" style="display:none;">
            <div style="font-size:0.82rem; color:#94A3B8; margin-bottom:14px;">
              Select the chapter opening architectural layout, page border margin framing, and running folio style applied across the entire book.
            </div>

            <div style="display:grid; grid-template-columns:1fr; gap:14px;">
              
              <!-- Chapter Opener Layout -->
              <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:12px;">
                <label style="font-size:0.75rem; color:#FBBF24; font-weight:700; text-transform:uppercase;">1. Chapter-Opener Architectural Layout</label>
                <select id="interior-opener-select" class="studio-input" style="width:100%; margin-top:6px;">
                  <option value="classic_centered" ${currentOpener === 'classic_centered' ? 'selected' : ''}>Classic Centered — Small caps chapter numeral, display title & centered ornament</option>
                  <option value="asymmetric_ledger" ${currentOpener === 'asymmetric_ledger' ? 'selected' : ''}>Asymmetric Ledger Rail — Large 42pt outer numeral rail, left-aligned title & double rule</option>
                  <option value="framed_cartouche" ${currentOpener === 'framed_cartouche' ? 'selected' : ''}>Framed Cartouche — Enclosed double-brass/ink architectural box framing chapter title</option>
                  <option value="botanical_sinkage" ${currentOpener === 'botanical_sinkage' ? 'selected' : ''}>Botanical Sinkage — Deep 2.2-inch sinkage with ornate top decorative border</option>
                  <option value="technical_dossier" ${currentOpener === 'technical_dossier' ? 'selected' : ''}>Technical Dossier — Monospace classification bar, hairline grid table header</option>
                </select>
              </div>

              <!-- Page Border Style -->
              <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:12px;">
                <label style="font-size:0.75rem; color:#38BDF8; font-weight:700; text-transform:uppercase;">2. Page Border & Margin Framing Style</label>
                <select id="interior-border-select" class="studio-input" style="width:100%; margin-top:6px;">
                  <option value="none" ${currentBorder === 'none' ? 'selected' : ''}>None — Clean, open traditional trade book margins</option>
                  <option value="hairline_margin_box" ${currentBorder === 'hairline_margin_box' ? 'selected' : ''}>Delicate 0.5pt Hairline Margin Box — Classic 19th-century Admiralty/ledger edition</option>
                  <option value="corner_registration_ticks" ${currentBorder === 'corner_registration_ticks' ? 'selected' : ''}>Corner Registration Ticks — Technical blueprint crosshairs at four corners</option>
                  <option value="double_victorian_frame" ${currentBorder === 'double_victorian_frame' ? 'selected' : ''}>Double Victorian Frame — Outer 1pt rule + inner 0.5pt rule with corner diamond accents</option>
                </select>
              </div>

              <!-- Folio Style -->
              <div style="background:#0F172A; border:1px solid #1E293B; border-radius:6px; padding:12px;">
                <label style="font-size:0.75rem; color:#34D399; font-weight:700; text-transform:uppercase;">3. Running Page Number / Folio Style</label>
                <select id="interior-folio-select" class="studio-input" style="width:100%; margin-top:6px;">
                  <option value="classic_centered" ${currentFolio === 'classic_centered' ? 'selected' : ''}>Classic Centered — Centered old-style figure (14)</option>
                  <option value="outer_brackets" ${currentFolio === 'outer_brackets' ? 'selected' : ''}>Outer Tracked Brackets — Outer margin bracketed folio ([ 14 ])</option>
                  <option value="fleuron_flanked" ${currentFolio === 'fleuron_flanked' ? 'selected' : ''}>Fleuron Flanked — Centered folio flanked by decorative fleuron (— ❖ 14 ❖ —)</option>
                  <option value="imperial_roman_chapter" ${currentFolio === 'imperial_roman_chapter' ? 'selected' : ''}>Imperial Roman Chapter — Chapter Roman Numeral + Page Number (I · 14)</option>
                </select>
              </div>

            </div>

            <div style="margin-top:16px;">
              <button class="btn-wizard-primary" style="padding:8px 18px;" onclick="saveAiInteriorArchitecture(this)">
                💾 Save & Apply Interior Architecture
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  `;
}

function switchAiDesignTab(tabId) {
  const tabs = ["ornaments", "containers", "bible", "architecture"];
  tabs.forEach(t => {
    const pane = document.getElementById(`ai-tab-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (pane) pane.style.display = (t === tabId) ? "block" : "none";
    if (btn) btn.classList.toggle("active", t === tabId);
  });
}

async function generateAiSvgOrnament(btn) {
  const motifInput = document.getElementById("ai-ornament-motif-input");
  const motif = motifInput ? motifInput.value : "antique brass sextant and quill";

  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Generating SVG with Qwen 2.5...";
  }

  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/generate-svg`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: motif, apply_to_book: true })
    });
    const data = await res.json();
    if (data.status === "success" && data.result) {
      const sceneEl = document.getElementById("ai-svg-scene-preview");
      const tailEl = document.getElementById("ai-svg-tail-preview");
      if (sceneEl) sceneEl.innerHTML = data.result.scene_break_svg;
      if (tailEl) tailEl.innerHTML = data.result.tailpiece_svg;
      showToast("✓ Generated & applied vector ornaments!", "success");
      renderAll();
    } else {
      showToast(data.detail || "SVG generation failed", "error");
    }
  } catch (err) {
    showToast(`SVG generation error: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "✨ Generate Vector Ornament (Qwen 2.5)";
    }
  }
}

async function generateAiContainerCss(btn) {
  const motifInput = document.getElementById("ai-container-motif-input");
  const motif = motifInput ? motifInput.value : "1960s cold-war redacted cable";

  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Designing Container with Qwen 2.5...";
  }

  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/generate-container-css`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: motif })
    });
    const data = await res.json();
    if (data.status === "success") {
      const codeEl = document.getElementById("ai-container-css-code");
      if (codeEl) codeEl.innerText = data.container_css;
      showToast(`✓ Registered custom container: ${data.container_label}!`, "success");
      renderAll();
    } else {
      showToast(data.detail || "Container generation failed", "error");
    }
  } catch (err) {
    showToast(`Container error: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "✨ Design Custom Container (Qwen 2.5)";
    }
  }
}

async function reExtractVisualBible(btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Extracting...";
  }

  try {
    const res = await fetch(`/api/ai/${state.activeBookId}/extract-bible`, { method: "POST" });
    const data = await res.json();
    if (data.status === "success" && data.visual_bible) {
      if (!state.settings) state.settings = {};
      state.settings.visual_bible = data.visual_bible;
      showToast("✓ Visual Continuity Bible extracted & locked!", "success");
      openAiDesignStudioModal();
      switchAiDesignTab('bible');
    } else {
      showToast(data.detail || "Visual bible extraction failed", "error");
    }
  } catch (err) {
    showToast(`Extraction failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🧠 Re-Extract from Manuscript (Qwen 2.5)";
    }
  }
}

async function saveAiInteriorArchitecture(btn) {
  const opener = document.getElementById("interior-opener-select")?.value || "classic_centered";
  const border = document.getElementById("interior-border-select")?.value || "none";
  const folio = document.getElementById("interior-folio-select")?.value || "classic_centered";

  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Applying...";
  }

  try {
    const res = await fetch(`/api/interior/${state.activeBookId}/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chapter_opener_layout: opener,
        page_border_style: border,
        folio_style: folio
      })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (!state.settings) state.settings = {};
      state.settings.interior_design = data.interior_design;
      if (data.pagination) state.pagination = data.pagination;
      showToast("✓ Applied interior architecture & repaginated!", "success");
      renderAll();
      closeModal();
    } else {
      showToast(data.detail || "Failed to update interior design", "error");
    }
  } catch (err) {
    showToast(`Interior design update failed: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "💾 Save & Apply Interior Architecture";
    }
  }
}

// --- STEP 4: SPREAD REVIEW & POLISH ---
function renderStep4() {
  renderSpreadCanvas();
  renderFilmstrip();

  const shortCount = (state.pagination.short_endings || []).length;
  const countSpan = document.getElementById("polish-short-count");
  if (countSpan) countSpan.innerText = shortCount;

  state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 5);
}

async function autoBalanceAllShortEndings() {
  showToast("Auto-balancing all short chapter endings...", "info");
  try {
    const res = await fetch("/api/tailpiece/auto-balance-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ book_id: state.activeBookId })
    });
    if (!res.ok) throw new Error("Auto-balance request failed");
    const data = await res.json();
    state.pagination = data.pagination;
    showToast(`✓ Balanced ${data.balanced_count} short endings with thematic tailpieces!`, "success");
    renderSpreadCanvas();
    renderFilmstrip();
    const countSpan = document.getElementById("polish-short-count");
    if (countSpan) countSpan.innerText = (data.pagination.short_endings || []).length;
  } catch (err) {
    console.error(err);
    showToast(`Error balancing endings: ${err.message}`, "error");
  }
}

function toggleTypographyDrawer() {
  state.isDrawerOpen = !state.isDrawerOpen;
  const drawer = document.getElementById("typography-drawer");
  if (!drawer) return;
  drawer.style.display = state.isDrawerOpen ? "flex" : "none";
  if (state.isDrawerOpen) {
    renderTypographyDrawer();
  }
}

function switchDrawerTab(tab) {
  state.drawerTab = tab;
  document.getElementById("dtab-geom-btn")?.classList.toggle("active", tab === "geometry");
  document.getElementById("dtab-matter-btn")?.classList.toggle("active", tab === "matter");
  renderTypographyDrawer();
}

function renderTypographyDrawer() {
  const content = document.getElementById("typography-drawer-content");
  if (!content) return;
  if (state.drawerTab === "geometry") {
    renderGeometryTab(content);
  } else {
    renderFrontMatterTab(content);
  }
}

// --- STEP 5: PRE-FLIGHT & EXPORTS ---
function renderStep5() {
  if (!state.settings || !state.activeBook) return;
  const s = state.settings;
  const typo = s.typography || {};
  const assets = state.manifest.assets || [];
  const readyCount = assets.filter(a => a.filter_applied || a.raw_image_path || (a.image_url && !a.image_url.includes("placeholder"))).length;
  const totalPages = state.pagination.total_pages || (state.pagination.pages?.length || 0);
  const signaturePages = Math.ceil(Math.max(1, totalPages) / 4) * 4;

  document.getElementById("preflight-geometry-val").innerText = 
    `${parseFloat(s.trim_width_in).toFixed(2)}" × ${parseFloat(s.trim_height_in).toFixed(2)}" Mirrored Gutters (${parseFloat(s.margin_inside_in).toFixed(3)}" Inside / ${parseFloat(s.margin_outside_in).toFixed(3)}" Outside)`;

  document.getElementById("preflight-typo-val").innerText = 
    `${typo.body_font_name || 'EB Garamond'} (${parseFloat(typo.body_font_size_pt || 11).toFixed(1)}pt / ${parseFloat(typo.body_leading_pt || 15).toFixed(1)}pt) & In-World Boxes Verified`;

  document.getElementById("preflight-artwork-val").innerText = 
    `${readyCount} of ${assets.length} Visual Plates Filtered at 300 DPI`;

  document.getElementById("preflight-pagination-val").innerText = 
    `${totalPages} Total Pages (${signaturePages} Pages in 4-Page Standard Signature Count)`;
}

async function importManifestFile(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    showToast("Importing manifest JSON...", "info");
    const res = await fetch(`/api/manifest/${state.activeBookId}/import`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Manifest import failed" }));
      throw new Error(err.detail || "Manifest import failed");
    }
    const data = await res.json();
    showToast("Manifest imported successfully!", "success");
    await loadBook(state.activeBookId);
  } catch (err) {
    console.error("Error importing manifest:", err);
    showToast(err.message, "error");
  }
}

function exportManifest() {
  showToast("Downloading manifest JSON...", "info");
  window.location.href = `/api/manifest/${state.activeBookId}/export`;
}

function setViewMode(mode) {
  state.viewMode = mode;
  document.getElementById("view-mode-html-btn")?.classList.toggle("active", mode === "html");
  document.getElementById("view-mode-pdf-btn")?.classList.toggle("active", mode === "pdf");
  document.getElementById("wview-mode-html-btn")?.classList.toggle("active", mode === "html");
  document.getElementById("wview-mode-pdf-btn")?.classList.toggle("active", mode === "pdf");
  renderSpreadCanvas();
}

// Wrapper aliases for backward compatibility and step-3 action triggers
function openPlateInspector(assetId) {
  openAssetInspector(assetId);
}

function openFilterLab(assetId) {
  openImageLabModal(assetId);
}

function openPinStudio(assetId) {
  openVisualPinStudio(assetId);
}

// ======================================================================
// 2. LEFT PANEL: SLOTS & MANUSCRIPT TREE
// ======================================================================
function renderLeftPanel() {
  const tabManifestBtn = document.getElementById("tab-manifest-btn");
  const tabTreeBtn = document.getElementById("tab-tree-btn");
  const contentArea = document.getElementById("left-panel-content");
  if (!contentArea) return;

  if (tabManifestBtn && tabTreeBtn) {
    tabManifestBtn.classList.toggle("active", state.activeLeftTab === "manifest");
    tabTreeBtn.classList.toggle("active", state.activeLeftTab === "tree");
  }

  if (state.activeLeftTab === "manifest") {
    renderManifestTab(contentArea);
  } else {
    renderTreeTab(contentArea);
  }
}

function renderManifestTab(container) {
  const assets = state.manifest.assets || [];
  let html = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <span style="font-size:0.72rem; color:var(--text-muted); font-weight:700;">${assets.length} PLANNED ILLUSTRATION SLOTS</span>
      <button onclick="openAddSlotModal()" style="background:var(--accent-gold); color:#000; border:none; padding:3px 8px; border-radius:4px; font-size:0.7rem; font-weight:700; cursor:pointer;">
        + Add Slot
      </button>
    </div>
  `;

  if (assets.length === 0) {
    html += `<div style="text-align:center; padding:30px 10px; color:var(--text-dim); font-size:0.82rem;">No illustration slots planned yet. Click "+ Add Slot" or drop an image.</div>`;
  } else {
    assets.forEach(asset => {
      const badgeCls = getPlacementBadgeClass(asset.placement);
      const calloutCount = (asset.vector_callouts || []).length;
      const frameLabel = (asset.frame_style || "none").replace(/_/g, " ");

      html += `
        <div class="asset-card" draggable="true" data-asset-id="${asset.id}" ondragstart="handleAssetDragStart(event, '${asset.id}')">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <span class="asset-badge ${badgeCls}">${asset.placement}</span>
            <span class="asset-anchor-chip" title="Anchored to Paragraph">⚓ ${asset.anchor}</span>
          </div>
          <div class="asset-title">${asset.title}</div>
          
          <div class="asset-thumbnail-row">
            <img src="${asset.image_url}" class="asset-thumb frame-${asset.frame_style || 'none'}" alt="${asset.title}" onerror="this.src='/static/assets/placeholders/book01_vignette.png'">
            <div style="flex:1; font-size:0.72rem;">
              <div style="margin-bottom:6px; display:flex; flex-wrap:wrap; gap:4px;">
                <button onclick="openAssetInspector('${asset.id}')" style="background:rgba(217,119,6,0.15); border:1px solid var(--accent-gold); color:var(--accent-gold); font-size:0.68rem; padding:3px 6px; border-radius:4px; cursor:pointer; font-weight:700;" title="Granular Sizing, Frames & Placement">
                  ⚙️ Frame & Size
                </button>
                <button onclick="openVisualPinStudio('${asset.id}')" style="background:rgba(56,189,248,0.12); border:1px solid var(--accent-cyan); color:var(--accent-cyan); font-size:0.68rem; padding:3px 6px; border-radius:4px; cursor:pointer; font-weight:600;">
                  📍 Pins (${calloutCount})
                </button>
                <button onclick="openImageLabModal('${asset.id}')" style="background:rgba(148,163,184,0.12); border:1px solid #64748B; color:#CBD5E1; font-size:0.68rem; padding:3px 6px; border-radius:4px; cursor:pointer; font-weight:600;">
                  🔬 Lab
                </button>
              </div>
              <div style="color:var(--text-dim); font-size:0.67rem;">Frame: <strong style="color:#FFF;">${frameLabel}</strong> • Width: ${asset.width_pct || 100}%</div>
            </div>
          </div>

          <div class="asset-prompt-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-size:0.65rem; text-transform:uppercase; color:var(--accent-gold); font-weight:700;">AI Generation Prompt</span>
              <button onclick="copyPrompt('${asset.id}', this)" style="background:none; border:none; color:var(--accent-cyan); font-size:0.68rem; cursor:pointer; font-weight:600;">
                📋 Copy
              </button>
            </div>
            <span>${asset.prompt}</span>
          </div>

          <div class="drop-zone" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDropImage(event, '${asset.id}')" onclick="triggerFileInput('${asset.id}')">
            📁 Drop Image Here or Click to Upload
          </div>
          <input type="file" id="file-input-${asset.id}" style="display:none;" accept="image/*" onchange="uploadImageFile('${asset.id}', this.files[0])">
        </div>
      `;
    });
  }

  container.innerHTML = html;
}

function renderTreeTab(container) {
  const chapters = state.manuscript?.chapters || [];
  let html = `<div style="font-size:0.73rem; color:var(--text-dim); margin-bottom:10px;">Click any paragraph to open the Semantic Block & Flow Inspector. Drag slots to anchor.</div>`;

  chapters.forEach(ch => {
    html += `
      <div class="manuscript-ch-header">
        Chapter ${ch.chapter_number}: ${ch.title}
      </div>
    `;

    (ch.elements || []).forEach(el => {
      const isAnchored = (state.manifest.assets || []).some(a => a.anchor === el.id);
      const blockType = el.block_type || (el.type === "container" ? el.tag : el.type);
      const textPreview = el.type === "paragraph"
        ? (el.text || "").substring(0, 60) + "..."
        : el.type === "container"
        ? `[${(el.tag || blockType).toUpperCase()}: ${(el.content || '').substring(0, 35)}]`
        : "— Scene Break Divider —";

      const badgeColor = blockType === "inworld_writ" || blockType === "inquest-writ" ? "#F59E0B"
        : blockType === "welsh_slate" || blockType === "welsh-slate" ? "#38BDF8"
        : blockType === "audio_transcript" || blockType === "audio-transcript" ? "#10B981"
        : blockType === "archival_journal" || blockType === "pelham-journal" ? "#A78BFA"
        : blockType === "scientific_formula" ? "#F43F5E"
        : blockType === "cuneiform_clause" ? "#FB923C"
        : "#64748B";

      html += `
        <div class="manuscript-p-row ${isAnchored ? 'drop-target' : ''}" 
             data-anchor-id="${el.id}"
             ondragover="handleDragOver(event)" 
             ondragleave="handleDragLeave(event)" 
             ondrop="handleDropAnchor(event, '${el.id}')"
             onclick="focusParagraphOnCanvas('${el.id}')">
          <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
            <span class="p-id-tag">${el.id}</span>
            <span style="flex:1; margin:0 6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${textPreview}</span>
            <div style="display:flex; align-items:center; gap:4px;">
              ${blockType !== 'body' ? `<span style="font-size:0.62rem; padding:1px 4px; border-radius:3px; background:${badgeColor}22; color:${badgeColor}; font-weight:700;">${blockType}</span>` : ''}
              ${isAnchored ? '<span style="color:var(--accent-gold); font-size:0.75rem;">⚓</span>' : ''}
              <button onclick="event.stopPropagation(); openParagraphInspector('${el.id}')" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:0.75rem; padding:1px 3px;" title="Block Inspector">⚙️</button>
            </div>
          </div>
        </div>
      `;
    });
  });

  container.innerHTML = html;
}

function getPlacementBadgeClass(placement) {
  switch (placement) {
    case "Full-Page Recto Plate": return "badge-full-plate";
    case "Full-Page Verso Plate": return "badge-full-plate";
    case "Full Bleed Plate": return "badge-full-plate";
    case "Half-Page Top": return "badge-half-top";
    case "Half-Page Bottom": return "badge-half-top";
    case "Inline Archival Insert": return "badge-inline";
    case "Chapter Opener Vignette": return "badge-opener";
    case "Chapter End Tailpiece": return "badge-tailpiece";
    default: return "badge-inline";
  }
}

function switchTab(tabName) {
  state.activeLeftTab = tabName;
  renderLeftPanel();
}

function switchRightTab(tabName) {
  state.activeRightTab = tabName;
  document.getElementById("rtab-geom-btn")?.classList.toggle("active", tabName === "geometry");
  document.getElementById("rtab-matter-btn")?.classList.toggle("active", tabName === "matter");
  document.getElementById("rtab-export-btn")?.classList.toggle("active", tabName === "export");
  renderRightPanel();
}

// ======================================================================
// 3. CENTER SPREAD CANVAS (HTML SPREAD & TRUE PRINT PDF SPREAD)
// ======================================================================
function renderSpreadCanvas() {
  const viewports = [
    document.getElementById("spread-viewport"),
    document.getElementById("wspread-viewport")
  ].filter(Boolean);
  if (viewports.length === 0) return;

  const spreads = state.pagination.spreads || [];
  if (spreads.length === 0) {
    viewports.forEach(vp => {
      vp.innerHTML = `<div style="color:var(--text-dim); text-align:center; padding:50px;">No pages to display in this edition.</div>`;
    });
    return;
  }

  if (state.currentSpreadIndex < 0) state.currentSpreadIndex = 0;
  if (state.currentSpreadIndex >= spreads.length) state.currentSpreadIndex = spreads.length - 1;

  const currentSpread = spreads[state.currentSpreadIndex];

  const spreadIndicators = [
    document.getElementById("spread-indicator"),
    document.getElementById("wspread-indicator")
  ].filter(Boolean);

  const prevBtns = [
    document.getElementById("spread-prev-btn")
  ].filter(Boolean);

  const nextBtns = [
    document.getElementById("spread-next-btn")
  ].filter(Boolean);

  const versoPage = currentSpread.verso?.page_number;
  const rectoPage = currentSpread.recto?.page_number;
  const pageLabel = versoPage && rectoPage ? `Pages ${versoPage}–${rectoPage}` : rectoPage ? `Page ${rectoPage}` : `Page ${versoPage}`;

  spreadIndicators.forEach(ind => {
    ind.innerText = `Spread ${state.currentSpreadIndex + 1} of ${spreads.length} (${pageLabel})`;
  });

  prevBtns.forEach(btn => btn.disabled = state.currentSpreadIndex === 0);
  nextBtns.forEach(btn => btn.disabled = state.currentSpreadIndex === spreads.length - 1);

  // Branch: TRUE PRINT PDF VIEW vs INTERACTIVE HTML VIEW
  viewports.forEach(vp => {
    if (state.viewMode === "pdf") {
      renderPdfSpread(vp, currentSpread);
    } else {
      renderHtmlSpread(vp, currentSpread);
    }
  });

  // Short Chapter Ending Detection Banner
  const bannerContainers = [
    document.getElementById("short-ending-banner-wrap"),
    document.getElementById("wshort-ending-banner-wrap")
  ].filter(Boolean);

  const hasShortVerso = currentSpread.verso?.short_ending && !currentSpread.verso?.has_tailpiece;
  const hasShortRecto = currentSpread.recto?.short_ending && !currentSpread.recto?.has_tailpiece;
  const shortPageNum = hasShortVerso ? currentSpread.verso.page_number : (hasShortRecto ? currentSpread.recto.page_number : null);

  bannerContainers.forEach(bc => {
    if (shortPageNum) {
      bc.innerHTML = `
        <div class="short-ending-banner">
          <div style="font-size:1.1rem;">⚠️</div>
          <div>
            <div style="font-size:0.8rem; font-weight:700; color:#FDE68A;">Short Chapter Ending Detected (Page ${shortPageNum})</div>
            <div style="font-size:0.72rem; color:#E0E7FF;">Page content has &lt; 18 lines of text. Whitespace is unbalanced.</div>
          </div>
          <button class="btn-tailpiece" onclick="autoInsertTailpiece(${shortPageNum})">
            ✨ Auto-Insert Tailpiece Ornament
          </button>
        </div>
      `;
    } else {
      bc.innerHTML = "";
    }
  });
}

function renderPdfSpread(viewport, currentSpread) {
  const versoNum = currentSpread.verso?.page_number;
  const rectoNum = currentSpread.recto?.page_number;

  let spreadHTML = `
    <div class="pdf-spread-container" style="transform: scale(${state.zoomLevel});">
  `;

  // Verso PDF page
  if (versoNum) {
    spreadHTML += `
      <div class="pdf-spread-page verso">
        <img class="pdf-page-img" src="/api/pdf-preview/${state.activeBookId}/${versoNum}?dpi=150" alt="Verso PDF Page ${versoNum}" onerror="this.onerror=null; this.src='/api/pdf-page/${state.activeBookId}/${versoNum}';">
        <div class="pdf-page-num-badge">Verso • Page ${versoNum}</div>
      </div>
    `;
  } else {
    spreadHTML += `
      <div class="pdf-spread-page verso empty-placeholder">
        <span>[VERSO BLANK / COVER REVERSE]</span>
      </div>
    `;
  }

  // Recto PDF page
  if (rectoNum) {
    spreadHTML += `
      <div class="pdf-spread-page recto">
        <img class="pdf-page-img" src="/api/pdf-preview/${state.activeBookId}/${rectoNum}?dpi=150" alt="Recto PDF Page ${rectoNum}" onerror="this.onerror=null; this.src='/api/pdf-page/${state.activeBookId}/${rectoNum}';">
        <div class="pdf-page-num-badge">Recto • Page ${rectoNum}</div>
      </div>
    `;
  } else {
    spreadHTML += `
      <div class="pdf-spread-page recto empty-placeholder">
        <span>[BLANK ENDPAGE]</span>
      </div>
    `;
  }

  spreadHTML += `</div>`;
  viewport.innerHTML = spreadHTML;
}

function renderHtmlSpread(viewport, currentSpread) {
  let spreadHTML = `<div class="book-spread-container" style="transform: scale(${state.zoomLevel});">`;

  // VERSO
  if (currentSpread.verso) {
    spreadHTML += renderSinglePageHTML(currentSpread.verso, "page-verso");
  } else {
    spreadHTML += `
      <div class="spread-page empty-placeholder" style="border-right:1px solid #222;">
        <span style="font-size:0.75rem; letter-spacing:0.1em;">[VERSO BLANK / COVER REVERSE]</span>
      </div>
    `;
  }

  // RECTO
  if (currentSpread.recto) {
    spreadHTML += renderSinglePageHTML(currentSpread.recto, "page-recto");
  } else {
    spreadHTML += `
      <div class="spread-page empty-placeholder">
        <span style="font-size:0.75rem; letter-spacing:0.1em;">[BLANK ENDPAGE]</span>
      </div>
    `;
  }

  spreadHTML += `</div>`;
  viewport.innerHTML = spreadHTML;

  setupInlineEditListeners();
}

function renderSinglePageHTML(page, sideClass) {
  const profile = state.activeBook || state.profiles["book01"];
  const s = state.settings || { typography: {}, margins: {} };
  const isVerso = sideClass === "page-verso";

  const fontName = s.typography.body_font_name || s.body_font || profile.body_font_name;
  const displayFont = s.typography.display_font_name || s.heading_font || profile.display_font_name;
  const accentColor = s.typography.accent_color || profile.accent_color;
  const brassAccent = profile.brass_accent || "#B8860B";
  const paperTint = s.typography.paper_tint || profile.paper_tint || "#FBF8F1";
  const fontSize = s.typography.body_font_size_pt || s.font_size_pt || 11;
  const lineHeightVal = s.line_height || 1.36;
  const leading = s.typography.body_leading_pt || (fontSize * lineHeightVal);
  const indent = s.para_indent_in !== undefined ? s.para_indent_in : (s.typography.subsequent_p_indent_in || 0.25);
  const sinkage = s.chapter_sinkage_in !== undefined ? s.chapter_sinkage_in : (s.typography.chapter_sinkage_in || 1.75);
  const runningHeaderStyle = s.running_header_style || "Small Caps Centered";

  let runningHeader = "";
  if (!page.suppress_header && runningHeaderStyle !== "Hidden") {
    if (isVerso) {
      runningHeader = s.typography.running_header_override || profile.short_title.toUpperCase();
    } else {
      runningHeader = `CHAPTER ${page.chapter_number} • ${page.chapter_title.toUpperCase()}`;
    }
  }

  let elementsHTML = "";

  (page.elements || []).forEach(elem => {
    if (elem.type === "half_title") {
      elementsHTML += `
        <div style="text-align:center; margin-top:140px;">
          <h2 style="font-family:${displayFont}; font-size:13pt; letter-spacing:0.14em; text-transform:uppercase;">${elem.title}</h2>
        </div>
      `;
    } else if (elem.type === "frontispiece") {
      elementsHTML += `
        <div style="text-align:center; margin-top:160px;">
          <div style="margin-bottom:16px;">${elem.ornament_svg}</div>
          <div style="font-style:italic; font-size:8pt; color:#666;">${elem.subtitle}</div>
        </div>
      `;
    } else if (elem.type === "title_page") {
      elementsHTML += `
        <div style="text-align:center; margin-top:70px;">
          <h1 style="font-family:${displayFont}; font-size:15pt; margin-bottom:6px; color:${accentColor};">${elem.title}</h1>
          <div style="font-style:italic; font-size:8.5pt; margin-bottom:20px;">${elem.subtitle}</div>
          <div style="margin-bottom:20px;">${profile.scene_break_svg}</div>
          <div style="font-family:${displayFont}; font-size:9.5pt; font-weight:700; letter-spacing:0.1em; text-transform:uppercase;">${elem.author}</div>
          <div style="margin-top:100px; font-size:6.8pt; letter-spacing:0.16em; color:#888;">${elem.imprint}</div>
        </div>
      `;
    } else if (elem.type === "copyright_page") {
      elementsHTML += `
        <div style="margin-top:260px; font-size:6.5pt; line-height:9.5pt; color:#666;">
          <strong>${elem.title}</strong><br>
          Copyright © ${elem.year} by ${elem.author}<br>
          All rights reserved. First Illustrated Collector's Edition.<br>
          ISBN ${elem.isbn}<br><br>
          ${elem.colophon_summary}
        </div>
      `;
    } else if (elem.type === "dedication") {
      elementsHTML += `
        <div style="text-align:center; margin-top:180px; font-style:italic; font-size:9.5pt; color:#333;">
          <p class="indent-zero">${elem.text}</p>
        </div>
      `;
    } else if (elem.type === "epigraph") {
      elementsHTML += `
        <div style="text-align:center; margin-top:180px;">
          <p class="indent-zero" style="font-style:italic; font-size:9.5pt; color:#333;">"${elem.text}"</p>
          <p class="indent-zero" style="font-size:7.5pt; color:#666; margin-top:8px;">${elem.source}</p>
        </div>
      `;
    } else if (elem.type === "map_plate") {
      elementsHTML += `
        <div style="text-align:center; margin-top:60px;">
          <h2 style="font-family:${displayFont}; font-size:11pt; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:12px; color:${accentColor};">${elem.title}</h2>
          <div style="border:2px solid #333; padding:4px; display:inline-block; max-width:92%;">
            <img src="${elem.image_url}" style="max-height:280px; width:100%; object-fit:contain; display:block;" onerror="this.src='/static/assets/placeholders/book01_vignette.png'">
          </div>
          <div style="font-style:italic; font-size:7.5pt; color:#666; margin-top:8px;">${elem.caption}</div>
        </div>
      `;
    } else if (elem.type === "table_of_contents") {
      elementsHTML += `
        <div style="margin-top:70px;">
          <h2 style="font-family:${displayFont}; font-size:11pt; letter-spacing:0.16em; text-align:center; text-transform:uppercase; margin-bottom:18px;">Contents</h2>
          ${(elem.chapters || []).map(ch => `
            <div style="display:flex; justify-content:space-between; font-size:8.2pt; margin-bottom:8px; border-bottom:1px dotted #ccc; padding-bottom:2px;">
              <span>Chapter ${ch.number} — ${ch.title}</span>
            </div>
          `).join("")}
        </div>
      `;
    } else if (elem.type === "chapter_header") {
      const openerLayout = page.chapter_opener_layout || state.settings?.interior_design?.chapter_opener_layout || "classic_centered";
      const ornamentSvg = state.settings?.interior_design?.custom_svg_scene_break || elem.ornament_svg;

      if (openerLayout === "asymmetric_ledger") {
        elementsHTML += `
          <div class="chapter-sinkage-box layout-asymmetric-ledger" style="padding-top:${sinkage * 36}px; margin-bottom:20px;">
            <div style="display:flex; align-items:flex-end; gap:14px; border-bottom:2px solid ${accentColor}; padding-bottom:6px;">
              <div style="font-family:'JetBrains Mono',monospace; font-size:2.4rem; font-weight:800; line-height:1; color:${brassAccent};">${elem.chapter_number}</div>
              <div style="flex:1;">
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.18em; text-transform:uppercase; color:#64748B;">ARCHIVE RECORD // CHAPTER ${elem.chapter_number}</div>
                <h1 class="ch-title" style="margin:0; text-align:left; font-size:1.15rem; font-family:${displayFont}; color:${accentColor};">${elem.title}</h1>
              </div>
            </div>
            <div style="height:1px; background:${accentColor}; margin-top:2px; margin-bottom:12px;"></div>
          </div>
        `;
      } else if (openerLayout === "framed_cartouche") {
        elementsHTML += `
          <div class="chapter-sinkage-box layout-framed-cartouche" style="padding-top:${sinkage * 28}px; margin-bottom:16px;">
            <div style="border:1.5px solid ${accentColor}; outline:1px solid ${brassAccent}; outline-offset:3px; padding:10px 14px; text-align:center; background:rgba(0,0,0,0.02);">
              <div class="ch-label" style="letter-spacing:0.2em; font-weight:700;">— CHAPTER ${elem.chapter_number} —</div>
              <h1 class="ch-title" style="margin:4px 0; font-family:${displayFont}; color:${accentColor};">${elem.title}</h1>
              <div class="ornament-wrap" style="margin-top:4px;">${ornamentSvg}</div>
            </div>
          </div>
        `;
      } else if (openerLayout === "botanical_sinkage") {
        elementsHTML += `
          <div class="chapter-sinkage-box layout-botanical-sinkage" style="padding-top:${Math.max(120, sinkage * 60)}px; text-align:center;">
            <div style="border-top:1px solid ${brassAccent}; border-bottom:1px solid ${brassAccent}; padding:3px 14px; display:inline-block; margin-bottom:8px;">
              <div class="ch-label" style="letter-spacing:0.18em;">CHAPTER ${elem.chapter_number}</div>
            </div>
            <h1 class="ch-title" style="margin:6px 0 10px 0; font-family:${displayFont}; color:${accentColor};">${elem.title}</h1>
            <div class="ornament-wrap">${ornamentSvg}</div>
          </div>
        `;
      } else if (openerLayout === "technical_dossier") {
        elementsHTML += `
          <div class="chapter-sinkage-box layout-technical-dossier" style="padding-top:${sinkage * 28}px; margin-bottom:16px;">
            <div style="background:${accentColor}; color:#FFF; font-family:'JetBrains Mono',monospace; font-size:0.65rem; padding:3px 8px; letter-spacing:0.14em; text-transform:uppercase; font-weight:700;">
              SECTION // ARCHIVE LOG ${elem.chapter_number} • COURT OF RESIDUAL CLAIMS
            </div>
            <div style="border:1px solid #CBD5E1; border-top:none; padding:10px 12px; background:#F8FAFC;">
              <h1 class="ch-title" style="text-align:left; margin:0; font-size:1.15rem; font-family:${displayFont}; color:#0F172A;">${elem.title}</h1>
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.62rem; color:#64748B; margin-top:4px;">RECORD CLASSIFICATION: LEVEL-IV FORENSIC • LOG #${elem.chapter_number}</div>
            </div>
          </div>
        `;
      } else {
        elementsHTML += `
          <div class="chapter-sinkage-box layout-classic-centered" style="height:${sinkage * 48}px;">
            <div class="ch-label">Chapter ${elem.chapter_number}</div>
            <h1 class="ch-title" style="font-family:${displayFont}; color:${accentColor};">${elem.title}</h1>
            <div class="ornament-wrap">${ornamentSvg}</div>
          </div>
        `;
      }
    } else if (elem.type === "chapter_subtitle" || elem.block_type === "chapter_subtitle") {
      elementsHTML += `
        <div class="chapter-subtitle" data-p-id="${elem.id}" ondblclick="openParagraphInspector('${elem.id}')">
          ${elem.text || elem.content}
        </div>
      `;
    } else if (elem.type === "paragraph") {
      const isFirst = elem.is_first_after_break;
      const isDrop = isFirst && page.page_type === "chapter_opener" && s.drop_cap_enabled !== false;
      const dropClass = isDrop ? (s.drop_cap_style === "Boxed Rule" ? "has-dropcap dropcap-boxed" : "has-dropcap") : "";
      const textStyle = `font-family:${fontName}; font-size:${fontSize}pt; line-height:${leading}pt; text-indent:${isFirst ? '0' : indent * 72 + 'px'}; text-align:${s.justify_text !== false ? 'justify' : 'left'};`;

      elementsHTML += `
        <p class="${isFirst ? 'indent-zero' : ''} ${dropClass}" 
           style="${textStyle}" 
           data-p-id="${elem.id}"
           contenteditable="true"
           ondblclick="openParagraphInspector('${elem.id}')"
           title="Click to inline-edit • Double-click for Block Inspector">
          ${elem.text}
        </p>
      `;
    } else if (elem.type === "container" || ["inworld_writ", "welsh_slate", "audio_transcript", "archival_journal", "scientific_formula", "cuneiform_clause"].includes(elem.block_type)) {
      const tagClass = elem.block_type ? elem.block_type.replace(/_/g, "-") : elem.tag;
      elementsHTML += `
        <div class="container-box ${tagClass}" 
             data-p-id="${elem.id}"
             contenteditable="true"
             ondblclick="openParagraphInspector('${elem.id}')"
             title="Click to inline-edit • Double-click for Block Inspector">
          ${(elem.content || elem.text || '').replace(/\n/g, "<br>")}
        </div>
      `;
    } else if (elem.type === "scene_break") {
      elementsHTML += `
        <div class="spread-scene-break">${elem.svg || profile.scene_break_svg}</div>
      `;
    } else if (elem.type === "illustration") {
      const asset = elem.asset;
      const isFull = elem.placement && elem.placement.startsWith("Full");
      const frameCls = `frame-${asset.frame_style || 'none'}`;
      const widthPct = asset.width_pct || 100;
      const maxH = asset.max_height_in ? `${asset.max_height_in}in` : "7.0in";
      const marginT = asset.margin_top_pt !== undefined ? `${asset.margin_top_pt}pt` : "8pt";
      const marginB = asset.margin_bottom_pt !== undefined ? `${asset.margin_bottom_pt}pt` : "8pt";

      elementsHTML += `
        <div class="spread-plate-wrapper ${isFull ? 'full-page' : ''}" 
             draggable="true" 
             ondragstart="handleAssetDragStart(event, '${asset.id}')"
             ondblclick="openAssetInspector('${asset.id}')"
             style="text-align:center; margin-top:${marginT}; margin-bottom:${marginB};"
             title="Double-click to open Plate Inspector">
          <img src="${asset.image_url}" class="${frameCls}" style="width:${widthPct}%; max-height:${maxH}; object-fit:contain; display:inline-block;" alt="${asset.title}">
          ${asset.caption_position !== 'hidden' ? `<div class="spread-plate-caption">${asset.caption || asset.title}</div>` : ''}
        </div>
      `;
    } else if (elem.type === "tailpiece_ornament") {
      elementsHTML += `
        <div class="spread-tailpiece">${elem.svg}</div>
      `;
    } else if (elem.type === "appendix") {
      elementsHTML += `
        <div style="margin-top:60px;">
          <h2 style="font-family:${displayFont}; font-size:11pt; letter-spacing:0.12em; text-align:center; text-transform:uppercase; margin-bottom:14px; color:${accentColor};">${elem.title}</h2>
          <div style="font-family:${fontName}; font-size:8.2pt; line-height:12pt; text-align:justify;">
            ${(elem.text || '').replace(/\n\n/g, "</p><p style='text-indent:14px;'>").replace(/\n/g, "<br>")}
          </div>
        </div>
      `;
    } else if (elem.type === "glossary") {
      elementsHTML += `
        <div style="margin-top:60px;">
          <h2 style="font-family:${displayFont}; font-size:11pt; letter-spacing:0.12em; text-align:center; text-transform:uppercase; margin-bottom:14px; color:${accentColor};">${elem.title}</h2>
          <div style="font-family:${fontName}; font-size:8pt; line-height:11.5pt;">
            ${(elem.terms || []).map(t => `
              <div style="margin-bottom:8px;">
                <strong style="color:#000;">${t.term}</strong> — <span style="color:#444;">${t.definition}</span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    } else if (elem.type === "acknowledgements" || elem.type === "about_author") {
      elementsHTML += `
        <div style="text-align:center; margin-top:140px; font-size:8pt; line-height:12pt; color:#444;">
          <h3 style="font-family:${displayFont}; font-size:10pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:12px;">${elem.title}</h3>
          <p class="indent-zero" style="text-align:justify; margin:0 20px;">${elem.text}</p>
        </div>
      `;
    } else if (elem.type === "colophon") {
      elementsHTML += `
        <div style="text-align:center; margin-top:140px; font-size:7.2pt; line-height:11pt; color:#555;">
          <h3 style="font-family:${displayFont}; font-size:9pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:10px; color:${accentColor};">Colophon</h3>
          <p class="indent-zero" style="text-align:center;">
            Typeset using the Argon Universal Publishing Engine.<br>
            Body text set in ${elem.body_font}. Display headers set in ${elem.display_font}.<br>
            ${elem.specs}
          </p>
          <div style="margin-top:20px;">${profile.tailpiece_svg}</div>
        </div>
      `;
    }
  });

  const borderStyle = page.page_border_style || state.settings?.interior_design?.page_border_style || "none";
  let borderClass = "";
  if (page.page_type === "body") {
    if (borderStyle === "hairline_margin_box") borderClass = " page-border-hairline";
    else if (borderStyle === "double_victorian_frame") borderClass = " page-border-double";
    else if (borderStyle === "corner_registration_ticks") borderClass = " page-border-ticks";
  }

  const folioText = page.folio_text || page.page_number;
  const folioStyle = page.folio_style || state.settings?.interior_design?.folio_style || "classic_centered";
  let folioAlign = "center";
  if (folioStyle === "outer_brackets") {
    folioAlign = (sideClass === "page-verso" || isVerso) ? "left" : "right";
  }

  return `
    <div class="spread-page ${sideClass}${borderClass}" style="background-color:${paperTint};">
      ${state.showMargins ? '<div class="margin-guide-overlay"></div>' : ''}
      ${state.showBleed ? '<div class="bleed-guide-line"></div>' : ''}
      
      <div class="page-header-running" style="font-family:${fontName};">${runningHeader}</div>
      
      <div class="page-body-content">
        ${elementsHTML}
      </div>
      
      ${!page.suppress_footer ? `<div class="page-footer-running" style="font-family:${fontName}; text-align:${folioAlign};">${folioText}</div>` : ''}
    </div>
  `;
}

// ======================================================================
// 4. INLINE EDITING & PARAGRAPH INSPECTOR
// ======================================================================
function setupInlineEditListeners() {
  const editableElems = document.querySelectorAll("[contenteditable='true']");
  
  editableElems.forEach(el => {
    let saveTimeout = null;
    const elemId = el.getAttribute("data-p-id");

    el.addEventListener("focus", () => {
      el.classList.add("inline-editing");
      showInlineActionToolbar(el, elemId);
    });

    el.addEventListener("blur", () => {
      el.classList.remove("inline-editing");
      setTimeout(() => removeInlineActionToolbar(), 250);
      saveInlineEdit(elemId, el.innerText);
    });

    el.addEventListener("input", () => {
      clearTimeout(saveTimeout);
      saveTimeout = setTimeout(() => {
        saveInlineEdit(elemId, el.innerText);
      }, 1200);
    });
  });
}

function showInlineActionToolbar(targetEl, elemId) {
  removeInlineActionToolbar();
  const toolbar = document.createElement("div");
  toolbar.id = "active-inline-toolbar";
  toolbar.className = "inline-edit-toolbar";
  
  toolbar.innerHTML = `
    <button onclick="saveInlineEdit('${elemId}', document.querySelector('[data-p-id=\\'${elemId}\\']').innerText)">✓ Save</button>
    <button onclick="openParagraphInspector('${elemId}')" style="background:#0284C7; color:#FFF;">⚙️ Block</button>
    <button onclick="insertSceneBreakAfter('${elemId}')">❖ Break</button>
    <button onclick="wrapInContainerPrompt('${elemId}')">📦 Box</button>
  `;
  
  targetEl.style.position = "relative";
  targetEl.appendChild(toolbar);
}

function removeInlineActionToolbar() {
  const tb = document.getElementById("active-inline-toolbar");
  if (tb) tb.remove();
}

async function saveInlineEdit(elemId, newText) {
  if (!elemId) return;
  try {
    const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/edit-element`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ element_id: elemId, text: newText })
    });
    if (res.status === "success") {
      state.pagination = res.pagination;
      renderFilmstrip();
    }
  } catch (err) {
    console.error("Save inline edit failed:", err);
  }
}

function openParagraphInspector(elementId) {
  let targetElem = null;
  let chNum = 1;
  const chapters = state.manuscript?.chapters || [];
  for (const ch of chapters) {
    for (const el of ch.elements || []) {
      if (el.id === elementId) {
        targetElem = el;
        chNum = ch.chapter_number;
        break;
      }
    }
    if (targetElem) break;
  }

  if (!targetElem) {
    showToast("Element not found", "error");
    return;
  }

  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const currentText = targetElem.text || targetElem.content || "";
  const wordCount = (currentText.trim().split(/\s+/).filter(Boolean)).length;
  const blockType = targetElem.block_type || (targetElem.type === "container" ? targetElem.tag.replace(/-/g, "_") : "body");
  const breakBefore = !!targetElem.page_break_before;
  const keepNext = !!targetElem.keep_with_next;
  const breakAfter = targetElem.scene_break_after || "none";

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:680px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-gold); display:flex; align-items:center; gap:8px;">
            <span>⚙️ Paragraph & In-World Block Inspector</span>
            <span style="font-family:monospace; font-size:0.75rem; color:var(--accent-cyan); background:rgba(56,189,248,0.1); padding:2px 6px; border-radius:4px;">${elementId}</span>
          </h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>

        <div class="modal-body" style="padding:16px; display:flex; flex-direction:column; gap:14px;">
          <!-- Paragraph Text Editor -->
          <div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <label style="font-size:0.72rem; color:var(--text-muted); font-weight:700;">PARAGRAPH / BLOCK TEXT CONTENT</label>
              <span style="font-size:0.7rem; color:var(--text-dim);">${wordCount} words • ~${Math.ceil(wordCount / 200)} min read</span>
            </div>
            <textarea id="p-inspector-text" rows="5" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.82rem; padding:8px; border-radius:4px; resize:vertical; font-family:inherit;">${currentText}</textarea>
          </div>

          <!-- Semantic Block Type Selector -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle);">
            <div style="font-size:0.75rem; color:var(--accent-gold); font-weight:700; margin-bottom:6px;">
              SEMANTIC BLOCK TYPE & THEME CONTAINER
            </div>
            <select id="p-inspector-block-type" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.8rem; padding:6px; border-radius:4px;">
              <option value="body" ${blockType === 'body' ? 'selected' : ''}>Body: Standard Indented Paragraph</option>
              <option value="body_first" ${blockType === 'body_first' ? 'selected' : ''}>Body First: Flush-Left Opener (Indent: 0)</option>
              <option value="chapter_subtitle" ${blockType === 'chapter_subtitle' ? 'selected' : ''}>Chapter Subtitle: Telemetry / Timestamp Header</option>
              <option value="inworld_writ" ${blockType === 'inworld_writ' ? 'selected' : ''}>In-World Writ: Parchment Legal Box (Book 01)</option>
              <option value="welsh_slate" ${blockType === 'welsh_slate' ? 'selected' : ''}>Welsh Slate: Dark Basalt & Chalk White Box (Book 02)</option>
              <option value="audio_transcript" ${blockType === 'audio_transcript' ? 'selected' : ''}>Audio Transcript: Monospace DAW Log & Ruler (Book 03)</option>
              <option value="archival_journal" ${blockType === 'archival_journal' ? 'selected' : ''}>Archival Journal: 1928 Ledger & Letter Box (Book 04)</option>
              <option value="scientific_formula" ${blockType === 'scientific_formula' ? 'selected' : ''}>Scientific Formula: Centered Equation Callout (Books 02/03/04)</option>
              <option value="cuneiform_clause" ${blockType === 'cuneiform_clause' ? 'selected' : ''}>Cuneiform Clause: Epigraphic Transliteration Table (Book 05)</option>
            </select>
          </div>

          <!-- Page Flow & Pagination Toggles -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle); display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <div style="font-size:0.75rem; color:var(--accent-cyan); font-weight:700; margin-bottom:8px;">
                PAGE FLOW CONTROLS
              </div>
              <label style="display:flex; align-items:center; gap:6px; font-size:0.75rem; color:var(--text-main); margin-bottom:6px; cursor:pointer;">
                <input type="checkbox" id="p-inspector-break-before" ${breakBefore ? 'checked' : ''}>
                <span>Force Page Break Before (Top of Next Page)</span>
              </label>
              <label style="display:flex; align-items:center; gap:6px; font-size:0.75rem; color:var(--text-main); cursor:pointer;">
                <input type="checkbox" id="p-inspector-keep-next" ${keepNext ? 'checked' : ''}>
                <span>Keep With Next Paragraph (No Page Break)</span>
              </label>
            </div>

            <div>
              <div style="font-size:0.75rem; color:var(--accent-cyan); font-weight:700; margin-bottom:8px;">
                SCENE BREAK AFTER BLOCK
              </div>
              <select id="p-inspector-break-after" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:5px; border-radius:4px;">
                <option value="none" ${breakAfter === 'none' ? 'selected' : ''}>None (Standard Flow)</option>
                <option value="book_svg" ${breakAfter === 'book_svg' ? 'selected' : ''}>Thematic Ornament SVG</option>
                <option value="asterisks" ${breakAfter === 'asterisks' ? 'selected' : ''}>Centered Asterisks (* * *)</option>
                <option value="custom_svg" ${breakAfter === 'custom_svg' ? 'selected' : ''}>Cuneiform / Wedge Divider</option>
              </select>
            </div>
          </div>
        </div>

        <div class="modal-footer" style="padding:12px 16px; background:rgba(0,0,0,0.3); border-top:1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div style="display:flex; gap:8px;">
            <button onclick="mergeElement('${elementId}')" style="background:rgba(56,189,248,0.15); border:1px solid var(--accent-cyan); color:var(--accent-cyan); padding:6px 12px; border-radius:4px; cursor:pointer; font-size:0.75rem; font-weight:600;">⫘ Merge With Previous Block</button>
            <button onclick="deleteElement('${elementId}')" style="background:rgba(239,68,68,0.15); border:1px solid #EF4444; color:#EF4444; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:0.75rem; font-weight:600;">🗑 Delete Element</button>
          </div>
          <div style="display:flex; gap:8px;">
            <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 14px; border-radius:4px; cursor:pointer; font-size:0.75rem;">Cancel</button>
            <button onclick="saveParagraphInspector('${elementId}')" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 18px; border-radius:4px; cursor:pointer; font-size:0.78rem;">Save & Re-Paginate</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function mergeElement(elementId) {
  if (!confirm("Are you sure you want to merge this block with the previous block?")) return;
  try {
    showToast("Merging with previous block...", "info");
    const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/merge-element`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ element_id: elementId })
    });
    if (res.status === "success") {
      showToast("Block merged successfully!", "success");
      closeModal();
      await loadBook(state.activeBookId);
    }
  } catch (err) {
    console.error("Error merging block:", err);
  }
}

async function deleteElement(elementId) {
  if (!confirm("Are you sure you want to delete this element from the manuscript?")) return;
  try {
    showToast("Deleting element...", "info");
    const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/delete-element/${elementId}`, {
      method: "DELETE"
    });
    if (res.status === "success") {
      showToast("Element deleted successfully!", "success");
      closeModal();
      await loadBook(state.activeBookId);
    }
  } catch (err) {
    console.error("Error deleting element:", err);
  }
}

async function saveParagraphInspector(elementId) {
  const newText = document.getElementById("p-inspector-text").value;
  const blockType = document.getElementById("p-inspector-block-type").value;
  const breakBefore = document.getElementById("p-inspector-break-before").checked;
  const keepNext = document.getElementById("p-inspector-keep-next").checked;
  const breakAfter = document.getElementById("p-inspector-break-after").value;

  showToast(`Updating paragraph ${elementId}...`, "info");
  const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/update-paragraph`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      element_id: elementId,
      text: newText,
      block_type: blockType,
      page_break_before: breakBefore,
      keep_with_next: keepNext,
      scene_break_after: breakAfter
    })
  });

  if (res.status === "success") {
    showToast("Paragraph updated and spread paginated!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

async function insertSceneBreakAfter(targetId) {
  showToast("Inserting thematic scene break...", "info");
  const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/insert-element`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_id: targetId,
      element_type: "scene_break",
      content: "***"
    })
  });
  if (res.status === "success") {
    showToast("Scene break inserted! Pagination updated.", "success");
    await loadBook(state.activeBookId);
  }
}

async function wrapInContainerPrompt(targetId) {
  const profile = state.activeBook || state.profiles["book01"];
  const availableContainers = profile.containers || [];
  const tag = availableContainers.length > 0 ? availableContainers[0].tag : "inquest-writ";
  
  showToast(`Wrapping element into .${tag}...`, "info");
  const res = await fetchAPI(`/api/manuscript/${state.activeBookId}/wrap-container`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      element_id: targetId,
      container_tag: tag
    })
  });
  if (res.status === "success") {
    showToast(`Element wrapped in .${tag}!`, "success");
    await loadBook(state.activeBookId);
  }
}

function focusParagraphOnCanvas(elemId) {
  const spreads = state.pagination.spreads || [];
  for (let sIdx = 0; sIdx < spreads.length; sIdx++) {
    const sp = spreads[sIdx];
    const inVerso = sp.verso?.elements?.some(e => e.id === elemId);
    const inRecto = sp.recto?.elements?.some(e => e.id === elemId);
    if (inVerso || inRecto) {
      state.currentSpreadIndex = sIdx;
      renderSpreadCanvas();
      renderFilmstrip();
      setTimeout(() => {
        const el = document.querySelector(`[data-p-id='${elemId}']`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.focus();
        }
      }, 100);
      break;
    }
  }
}

// ======================================================================
// 5. GRANULAR IMAGE & PLATE INSPECTOR MODAL
// ======================================================================
function openAssetInspector(assetId) {
  const asset = state.manifest.assets.find(a => a.id === assetId);
  if (!asset) {
    showToast("Asset not found", "error");
    return;
  }

  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const currentPlacement = asset.placement || "Half-Page Top";
  const currentFrame = asset.frame_style || "none";
  const widthPct = asset.width_pct || 100;
  const maxH = asset.max_height_in || 7.0;
  const marginT = asset.margin_top_pt !== undefined ? asset.margin_top_pt : 8;
  const marginB = asset.margin_bottom_pt !== undefined ? asset.margin_bottom_pt : 8;
  const captionPos = asset.caption_position || "below";
  const captionText = asset.caption || "";

  // Resolve target chapter paragraphs for Anchor Paragraph selector
  let targetChapter = null;
  const chapters = state.manuscript?.chapters || [];
  if (asset.chapter !== undefined && asset.chapter !== null && asset.chapter !== "") {
    targetChapter = chapters.find(ch => String(ch.chapter_number) === String(asset.chapter));
  }
  if (!targetChapter && asset.anchor) {
    targetChapter = chapters.find(ch => (ch.elements || []).some(el => el.id === asset.anchor));
  }
  if (!targetChapter && chapters.length > 0) {
    targetChapter = chapters[0];
  }

  const pElements = (targetChapter?.elements || []).filter(el => el.type === "paragraph" || el.type === "container" || (el.id && el.id.startsWith("ch")));
  let anchorOptionsHtml = "";
  let currentAnchorIncluded = false;

  pElements.forEach(el => {
    const rawText = (el.text || el.content || "").replace(/<[^>]*>/g, "").trim();
    const preview = rawText ? (rawText.length > 60 ? rawText.substring(0, 60) + "..." : rawText) : `[Empty Block]`;
    const isSel = asset.anchor === el.id;
    if (isSel) currentAnchorIncluded = true;
    anchorOptionsHtml += `<option value="${el.id}" ${isSel ? 'selected' : ''}>${el.id}: "${preview}"</option>`;
  });

  if (!currentAnchorIncluded && asset.anchor) {
    anchorOptionsHtml = `<option value="${asset.anchor}" selected>${asset.anchor} (Current Anchor)</option>` + anchorOptionsHtml;
  }
  if (!anchorOptionsHtml) {
    anchorOptionsHtml = `<option value="ch01_p01" selected>ch01_p01</option>`;
  }

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:720px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-gold); display:flex; align-items:center; gap:8px;">
            <span>📐 Granular Plate & Frame Inspector</span>
            <span style="font-family:monospace; font-size:0.75rem; color:var(--accent-cyan); background:rgba(56,189,248,0.1); padding:2px 6px; border-radius:4px;">${asset.id}</span>
          </h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>

        <div class="modal-body" style="padding:16px; display:flex; flex-direction:column; gap:14px;">
          <!-- Preview & Sizing -->
          <div style="display:flex; gap:14px; background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle); align-items:center;">
            <div style="width:140px; text-align:center;">
              <img id="asset-inspect-img-preview" src="${asset.image_url}" class="frame-${currentFrame}" style="max-height:120px; max-width:100%; object-fit:contain;" alt="${asset.title}">
            </div>
            <div style="flex:1;">
              <div style="font-size:0.85rem; font-weight:700; color:#FFF; margin-bottom:4px;">${asset.title}</div>
              <div style="font-size:0.72rem; color:var(--text-muted); margin-bottom:8px;">Anchored to Paragraph: <strong style="color:var(--accent-gold);">${asset.anchor}</strong></div>
              
              <div style="display:flex; gap:8px;">
                <button onclick="openVisualPinStudio('${asset.id}')" style="background:rgba(56,189,248,0.15); border:1px solid var(--accent-cyan); color:var(--accent-cyan); font-size:0.72rem; padding:4px 8px; border-radius:4px; cursor:pointer; font-weight:600;">
                  📍 Open Visual Pin Studio
                </button>
                <button onclick="openImageLabModal('${asset.id}')" style="background:rgba(217,119,6,0.15); border:1px solid var(--accent-gold); color:var(--accent-gold); font-size:0.72rem; padding:4px 8px; border-radius:4px; cursor:pointer; font-weight:600;">
                  🔬 Open 300 DPI Texture Lab
                </button>
              </div>
            </div>
          </div>

          <!-- Anchor Paragraph & Placement -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle); display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label style="font-size:0.72rem; color:var(--accent-cyan); font-weight:700; display:block; margin-bottom:4px;">ANCHOR PARAGRAPH</label>
              <select id="asset-anchor-select" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:6px; border-radius:4px;">
                ${anchorOptionsHtml}
              </select>
            </div>

            <div>
              <label style="font-size:0.72rem; color:var(--accent-cyan); font-weight:700; display:block; margin-bottom:4px;">PAGE PLACEMENT & LOCKING</label>
              <select id="asset-placement" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:6px; border-radius:4px;">
                <option value="Full-Page Recto Plate" ${currentPlacement === 'Full-Page Recto Plate' ? 'selected' : ''}>Full-Page Recto Plate (Odd Right Page)</option>
                <option value="Full-Page Verso Plate" ${currentPlacement === 'Full-Page Verso Plate' ? 'selected' : ''}>Full-Page Verso Plate (Even Left Page)</option>
                <option value="Full Bleed Plate" ${currentPlacement === 'Full Bleed Plate' ? 'selected' : ''}>Full Bleed Plate (6.125 x 9.25")</option>
                <option value="Half-Page Top" ${currentPlacement === 'Half-Page Top' ? 'selected' : ''}>Half-Page Top (Top 45%)</option>
                <option value="Half-Page Bottom" ${currentPlacement === 'Half-Page Bottom' ? 'selected' : ''}>Half-Page Bottom (Bottom 45%)</option>
                <option value="Inline Archival Insert" ${currentPlacement === 'Inline Archival Insert' ? 'selected' : ''}>Inline Archival Insert (Centered in flow)</option>
                <option value="Chapter Opener Vignette" ${currentPlacement === 'Chapter Opener Vignette' ? 'selected' : ''}>Chapter Opener Vignette (Above Title)</option>
                <option value="Chapter End Tailpiece" ${currentPlacement === 'Chapter End Tailpiece' ? 'selected' : ''}>Chapter End Tailpiece (Bottom of Scene)</option>
              </select>
            </div>
          </div>

          <!-- Frame & Border Style -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle);">
            <label style="font-size:0.72rem; color:var(--accent-cyan); font-weight:700; display:block; margin-bottom:4px;">FRAME & BORDER STYLE</label>
            <select id="asset-frame-style" onchange="document.getElementById('asset-inspect-img-preview').className = 'frame-' + this.value" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:6px; border-radius:4px;">
              <option value="none" ${currentFrame === 'none' ? 'selected' : ''}>None (Frameless / Edge-to-Edge)</option>
              <option value="thin_ink_border" ${currentFrame === 'thin_ink_border' ? 'selected' : ''}>Thin Ink Border (0.75pt Crisp Ink)</option>
              <option value="double_brass_frame" ${currentFrame === 'double_brass_frame' ? 'selected' : ''}>Double Brass Ruled Frame (Book 01)</option>
              <option value="blueprint_grid_frame" ${currentFrame === 'blueprint_grid_frame' ? 'selected' : ''}>Blueprint Grid Frame (Book 03)</option>
              <option value="rounded_slate" ${currentFrame === 'rounded_slate' ? 'selected' : ''}>Basalt Rounded Slate (Book 02)</option>
            </select>
          </div>

          <!-- Sizing & Margins -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle); display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <div class="slider-label-wrap">
                <span style="font-size:0.72rem; color:var(--text-muted);">Width Scale %:</span>
                <span class="slider-val-tag" id="asset-val-width">${widthPct}%</span>
              </div>
              <input type="range" min="20" max="100" step="5" value="${widthPct}" oninput="document.getElementById('asset-val-width').innerText = this.value + '%'" id="asset-width-pct">
            </div>

            <div>
              <div class="slider-label-wrap">
                <span style="font-size:0.72rem; color:var(--text-muted);">Max Height (in):</span>
                <span class="slider-val-tag" id="asset-val-height">${parseFloat(maxH).toFixed(1)}"</span>
              </div>
              <input type="range" min="1.0" max="8.5" step="0.25" value="${maxH}" oninput="document.getElementById('asset-val-height').innerText = parseFloat(this.value).toFixed(2) + '\"'" id="asset-max-height">
            </div>

            <div>
              <div class="slider-label-wrap">
                <span style="font-size:0.72rem; color:var(--text-muted);">Top Margin (pt):</span>
                <span class="slider-val-tag" id="asset-val-margintop">${marginT} pt</span>
              </div>
              <input type="range" min="0" max="36" step="2" value="${marginT}" oninput="document.getElementById('asset-val-margintop').innerText = this.value + ' pt'" id="asset-margin-top">
            </div>

            <div>
              <div class="slider-label-wrap">
                <span style="font-size:0.72rem; color:var(--text-muted);">Bottom Margin (pt):</span>
                <span class="slider-val-tag" id="asset-val-marginbottom">${marginB} pt</span>
              </div>
              <input type="range" min="0" max="36" step="2" value="${marginB}" oninput="document.getElementById('asset-val-marginbottom').innerText = this.value + ' pt'" id="asset-margin-bottom">
            </div>
          </div>

          <!-- Caption & Position -->
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; border:1px solid var(--border-subtle); display:grid; grid-template-columns:2fr 1fr; gap:12px;">
            <div>
              <label style="font-size:0.72rem; color:var(--text-muted); font-weight:700; display:block; margin-bottom:4px;">CAPTION TEXT</label>
              <input type="text" id="asset-caption-text" value="${captionText}" placeholder="Plate caption..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:6px; border-radius:4px;">
            </div>

            <div>
              <label style="font-size:0.72rem; color:var(--text-muted); font-weight:700; display:block; margin-bottom:4px;">CAPTION POSITION</label>
              <select id="asset-caption-position" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:6px; border-radius:4px;">
                <option value="below" ${captionPos === 'below' ? 'selected' : ''}>Below Plate</option>
                <option value="above" ${captionPos === 'above' ? 'selected' : ''}>Above Plate</option>
                <option value="facing_verso_bottom" ${captionPos === 'facing_verso_bottom' ? 'selected' : ''}>Facing Verso Bottom</option>
                <option value="hidden" ${captionPos === 'hidden' ? 'selected' : ''}>Hidden / Silent</option>
              </select>
            </div>
          </div>
        </div>

        <div class="modal-footer" style="padding:12px 16px; background:rgba(0,0,0,0.3); border-top:1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <button onclick="deleteIllustrationSlot('${asset.id}')" style="background:rgba(239,68,68,0.15); border:1px solid #EF4444; color:#EF4444; padding:6px 14px; border-radius:4px; cursor:pointer; font-size:0.75rem; font-weight:600;">🗑 Delete Slot</button>
          <div style="display:flex; gap:8px;">
            <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 14px; border-radius:4px; cursor:pointer; font-size:0.75rem;">Cancel</button>
            <button onclick="saveAssetInspector('${asset.id}')" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 18px; border-radius:4px; cursor:pointer; font-size:0.78rem;">Save Plate Settings</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function deleteIllustrationSlot(assetId) {
  if (!confirm(`Are you sure you want to delete illustration slot "${assetId}"?`)) return;
  try {
    showToast("Deleting illustration slot...", "info");
    const res = await fetchAPI(`/api/manifest/${state.activeBookId}/delete-slot/${assetId}`, {
      method: "DELETE"
    });
    if (res.status === "success") {
      showToast("Illustration slot deleted successfully!", "success");
      closeModal();
      await loadBook(state.activeBookId);
    }
  } catch (err) {
    console.error("Error deleting slot:", err);
  }
}

async function saveAssetInspector(assetId) {
  const anchorSelect = document.getElementById("asset-anchor-select");
  const newAnchor = anchorSelect ? anchorSelect.value : null;
  const placement = document.getElementById("asset-placement").value;
  const frameStyle = document.getElementById("asset-frame-style").value;
  const widthPct = parseInt(document.getElementById("asset-width-pct").value, 10);
  const maxH = parseFloat(document.getElementById("asset-max-height").value);
  const marginT = parseInt(document.getElementById("asset-margin-top").value, 10);
  const marginB = parseInt(document.getElementById("asset-margin-bottom").value, 10);
  const captionText = document.getElementById("asset-caption-text").value;
  const captionPos = document.getElementById("asset-caption-position").value;

  const updates = {
    placement: placement,
    frame_style: frameStyle,
    width_pct: widthPct,
    max_height_in: maxH,
    margin_top_pt: marginT,
    margin_bottom_pt: marginB,
    caption: captionText,
    caption_position: captionPos
  };
  if (newAnchor) {
    updates.anchor = newAnchor;
    updates.anchor_text = newAnchor;
  }

  showToast(`Updating plate specs for ${assetId}...`, "info");
  const res = await fetchAPI(`/api/manifest/${state.activeBookId}/update-asset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      asset_id: assetId,
      updates: updates
    })
  });

  if (res.status === "success") {
    showToast("Plate specifications updated!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// ======================================================================
// 6. VISUAL PIN-DROPPER CALLOUT STUDIO WITH POINTER TARGETS
// ======================================================================
function openVisualPinStudio(assetId) {
  const asset = state.manifest.assets.find(a => a.id === assetId);
  if (!asset) return;

  state.pinStudioState.assetId = assetId;
  state.pinStudioState.callouts = JSON.parse(JSON.stringify(asset.vector_callouts || []));
  state.pinStudioState.activePinIndex = null;
  state.pinStudioState.targetMode = false;

  renderPinStudioModal();
}

function renderPinStudioModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const asset = state.manifest.assets.find(a => a.id === state.pinStudioState.assetId);
  if (!asset) return;

  const callouts = state.pinStudioState.callouts;

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:800px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-cyan); display:flex; align-items:center; gap:8px;">
            <span>📍 Visual Callout Studio — Click Canvas to Drop Pins & Targets</span>
          </h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body" style="padding:14px; display:flex; flex-direction:column; gap:12px;">
          <div style="font-size:0.75rem; color:var(--text-muted);">
            Click anywhere on the plate to place a callout label. Drag pins to reposition. Select a pin to adjust its pointer leader line to a feature target.
          </div>

          <!-- Interactive Pin Canvas -->
          <div style="text-align:center; background:#000; padding:10px; border-radius:6px; overflow:hidden;">
            <div id="pin-canvas-wrap" class="pin-canvas-container" style="position:relative; display:inline-block;" onclick="handlePinCanvasClick(event)">
              <img id="pin-target-img" src="${asset.image_url}" style="max-height:360px; max-width:100%; display:block;" alt="${asset.title}">
              
              <!-- SVG Leader Lines -->
              <svg id="pin-svg-overlay" style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none;">
                ${callouts.map((c, i) => {
                  const hasTarget = c.target_x !== undefined && c.target_y !== undefined;
                  if (!hasTarget) return '';
                  return `
                    <line x1="${c.x}%" y1="${c.y}%" x2="${c.target_x}%" y2="${c.target_y}%" stroke="#D97706" stroke-width="1.5" stroke-dasharray="3,2" />
                    <circle cx="${c.target_x}%" cy="${c.target_y}%" r="3.5" fill="#EF4444" stroke="#FFF" stroke-width="1" />
                  `;
                }).join("")}
              </svg>

              <!-- Render pins -->
              ${callouts.map((c, i) => `
                <div class="pin-marker ${state.pinStudioState.activePinIndex === i ? 'active-pin' : ''}" 
                     style="left:${c.x}%; top:${c.y}%; position:absolute;" 
                     title="${c.label}"
                     onclick="event.stopPropagation(); selectPin(${i});"
                     onmousedown="startDraggingPin(event, ${i})">
                  ${i + 1}
                  <div class="pin-label-preview">${c.label}</div>
                </div>
              `).join("")}
            </div>
          </div>

          <!-- Selected Pin Properties Editor -->
          <div id="pin-editor-panel" style="background:var(--bg-card); padding:10px; border-radius:6px; font-size:0.75rem;">
            ${renderPinEditorControls()}
          </div>
        </div>

        <div class="modal-footer" style="padding:12px 16px; background:rgba(0,0,0,0.3); border-top:1px solid var(--border-subtle); display:flex; justify-content:flex-end; gap:8px;">
          <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 12px; border-radius:4px; cursor:pointer;">Cancel</button>
          <button onclick="saveVisualPins()" style="background:var(--accent-cyan); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Save & Render Vectors</button>
        </div>
      </div>
    </div>
  `;
}

function renderPinEditorControls() {
  const idx = state.pinStudioState.activePinIndex;
  const callouts = state.pinStudioState.callouts;

  if (idx === null || !callouts[idx]) {
    return `<div style="color:var(--text-dim); text-align:center;">Click anywhere on the image above to add a pin, or click an existing pin number to edit its label and pointer target.</div>`;
  }

  const pin = callouts[idx];
  const hasTarget = pin.target_x !== undefined && pin.target_y !== undefined;

  return `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <strong style="color:var(--accent-cyan);">Editing Pin #${idx + 1}</strong>
      <div style="display:flex; gap:6px;">
        <button onclick="togglePinTargetMode(${idx})" style="background:${state.pinStudioState.targetMode ? '#D97706' : '#1E293B'}; color:#FFF; border:1px solid #D97706; padding:2px 8px; border-radius:3px; cursor:pointer; font-size:0.7rem;">
          ${state.pinStudioState.targetMode ? '🎯 Click Image to Place Target' : '🎯 Set Pointer Target'}
        </button>
        <button onclick="deletePin(${idx})" style="background:#EF4444; color:#FFF; border:none; padding:2px 8px; border-radius:3px; cursor:pointer; font-size:0.7rem;">Delete Pin</button>
      </div>
    </div>
    <div style="display:grid; grid-template-columns:2fr 1fr 1fr; gap:8px;">
      <div>
        <label style="color:var(--text-muted); font-size:0.7rem;">Label Text</label>
        <input type="text" value="${pin.label}" oninput="updateActivePinProperty('label', this.value)" style="width:100%; padding:5px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">
      </div>
      <div>
        <label style="color:var(--text-muted); font-size:0.7rem;">Style / Type</label>
        <select onchange="updateActivePinProperty('type', this.value)" style="width:100%; padding:5px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">
          <option value="badge" ${pin.type === 'badge' ? 'selected' : ''}>Pill Badge</option>
          <option value="box" ${pin.type === 'box' ? 'selected' : ''}>Technical Box</option>
          <option value="crosshair" ${pin.type === 'crosshair' ? 'selected' : ''}>Crosshair Target</option>
          <option value="callout_pointer" ${pin.type === 'callout_pointer' ? 'selected' : ''}>Callout Pointer Line</option>
          <option value="arrow_target" ${pin.type === 'arrow_target' ? 'selected' : ''}>Arrow Target</option>
        </select>
      </div>
      <div>
        <label style="color:var(--text-muted); font-size:0.7rem;">Coordinates</label>
        <div style="padding:5px; color:var(--accent-gold); font-family:monospace; font-size:0.7rem;">
          Pin: (${pin.x.toFixed(1)}%, ${pin.y.toFixed(1)}%)<br>
          Target: ${hasTarget ? `(${pin.target_x.toFixed(1)}%, ${pin.target_y.toFixed(1)}%)` : 'None'}
        </div>
      </div>
    </div>
  `;
}

function handlePinCanvasClick(event) {
  const img = document.getElementById("pin-target-img");
  if (!img) return;

  const rect = img.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const clickY = event.clientY - rect.top;

  const pctX = Math.max(2, Math.min(98, (clickX / rect.width) * 100));
  const pctY = Math.max(2, Math.min(98, (clickY / rect.height) * 100));

  if (state.pinStudioState.targetMode && state.pinStudioState.activePinIndex !== null) {
    const idx = state.pinStudioState.activePinIndex;
    state.pinStudioState.callouts[idx].target_x = parseFloat(pctX.toFixed(1));
    state.pinStudioState.callouts[idx].target_y = parseFloat(pctY.toFixed(1));
    state.pinStudioState.targetMode = false;
    renderPinStudioModal();
    return;
  }

  const newPin = {
    label: `FEATURE #${state.pinStudioState.callouts.length + 1}`,
    x: parseFloat(pctX.toFixed(1)),
    y: parseFloat(pctY.toFixed(1)),
    type: "badge"
  };

  state.pinStudioState.callouts.push(newPin);
  state.pinStudioState.activePinIndex = state.pinStudioState.callouts.length - 1;
  renderPinStudioModal();
}

function togglePinTargetMode(idx) {
  state.pinStudioState.activePinIndex = idx;
  state.pinStudioState.targetMode = !state.pinStudioState.targetMode;
  renderPinStudioModal();
}

function selectPin(index) {
  state.pinStudioState.activePinIndex = index;
  renderPinStudioModal();
}

function deletePin(index) {
  state.pinStudioState.callouts.splice(index, 1);
  state.pinStudioState.activePinIndex = null;
  renderPinStudioModal();
}

function updateActivePinProperty(key, val) {
  const idx = state.pinStudioState.activePinIndex;
  if (idx !== null && state.pinStudioState.callouts[idx]) {
    state.pinStudioState.callouts[idx][key] = val;
    const marker = document.querySelectorAll(".pin-marker")[idx];
    if (marker) {
      const preview = marker.querySelector(".pin-label-preview");
      if (preview && key === "label") preview.innerText = val;
    }
  }
}

function startDraggingPin(event, index) {
  event.stopPropagation();
  state.pinStudioState.activePinIndex = index;

  const img = document.getElementById("pin-target-img");
  if (!img) return;

  const rect = img.getBoundingClientRect();

  function onMouseMove(moveEvent) {
    const moveX = moveEvent.clientX - rect.left;
    const moveY = moveEvent.clientY - rect.top;
    const pctX = Math.max(2, Math.min(98, (moveX / rect.width) * 100));
    const pctY = Math.max(2, Math.min(98, (moveY / rect.height) * 100));

    state.pinStudioState.callouts[index].x = parseFloat(pctX.toFixed(1));
    state.pinStudioState.callouts[index].y = parseFloat(pctY.toFixed(1));

    const marker = document.querySelectorAll(".pin-marker")[index];
    if (marker) {
      marker.style.left = `${pctX}%`;
      marker.style.top = `${pctY}%`;
    }
  }

  function onMouseUp() {
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
    renderPinStudioModal();
  }

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}

async function saveVisualPins() {
  const assetId = state.pinStudioState.assetId;
  const callouts = state.pinStudioState.callouts;

  showToast("Rendering precision vector callout overlay with pointer targets...", "info");
  const res = await fetchAPI(`/api/manifest/${state.activeBookId}/update-callouts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ asset_id: assetId, callouts })
  });

  if (res.status === "success") {
    showToast("Vector callout overlay rendered and saved!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// ======================================================================
// 7. BIRD'S-EYE FILMSTRIP DOCK (BOTTOM)
// ======================================================================
function renderFilmstrip() {
  const docks = [
    document.getElementById("filmstrip-dock"),
    document.getElementById("wfilmstrip-dock")
  ].filter(Boolean);
  if (docks.length === 0) return;

  docks.forEach(dock => {
    if (!state.showFilmstrip) {
      dock.classList.add("collapsed");
      dock.innerHTML = `
        <button onclick="toggleFilmstrip()" style="background:none; border:none; color:var(--text-muted); font-size:0.75rem; cursor:pointer; width:100%;">
          ▲ Expand Filmstrip (${state.pagination.total_spreads || 0} Spreads)
        </button>
      `;
      return;
    }

    dock.classList.remove("collapsed");
    const items = state.pagination.filmstrip || [];

    let html = `
      <div style="font-size:0.68rem; color:var(--accent-gold); font-weight:700; writing-mode:vertical-lr; transform:rotate(180deg); flex-shrink:0;">
        FILMSTRIP
      </div>
    `;

    items.forEach(item => {
      const isActive = item.spread_index === state.currentSpreadIndex;
      const vLabel = item.verso_num || "-";
      const rLabel = item.recto_num || "-";

      html += `
        <div class="filmstrip-card ${isActive ? 'active' : ''}" onclick="jumpToSpread(${item.spread_index})">
          <div class="filmstrip-badge-row">
            ${item.has_opener ? '<span class="f-badge f-opener" title="Chapter Opener">Ch</span>' : ''}
            ${item.has_plate ? '<span class="f-badge f-plate" title="Illustration Plate">Pl</span>' : ''}
            ${item.has_short ? '<span class="f-badge f-short" title="Short Ending">⚠️</span>' : ''}
            ${item.is_front ? '<span class="f-badge f-front" title="Front Matter">Fm</span>' : ''}
          </div>
          <div class="filmstrip-pages-preview">
            <div class="mini-page-box">${vLabel}</div>
            <div class="mini-page-box">${rLabel}</div>
          </div>
          <div style="font-size:0.62rem; color:var(--text-dim); font-family:monospace;">
            Spread ${item.display_num}
          </div>
        </div>
      `;
    });

    dock.innerHTML = html;
  });
}

function jumpToSpread(index) {
  state.currentSpreadIndex = index;
  renderSpreadCanvas();
  renderFilmstrip();
}

function toggleFilmstrip() {
  state.showFilmstrip = !state.showFilmstrip;
  renderFilmstrip();
}

// ======================================================================
// 8. RIGHT PANEL: DESIGN & TYPOGRAPHY INSPECTOR (TAB 1)
// ======================================================================
function renderRightPanel() {
  const container = document.getElementById("right-panel-content");
  if (!container) return;

  if (state.activeRightTab === "geometry") {
    renderGeometryTab(container);
  } else if (state.activeRightTab === "matter") {
    renderFrontMatterTab(container);
  } else {
    renderExportTab(container);
  }
}

function renderGeometryTab(container) {
  const s = state.settings || { margins: {}, typography: {} };
  const p = state.activeBook || state.profiles["book01"];

  const trimW = s.trim_width_in || 6.0;
  const trimH = s.trim_height_in || 9.0;
  const gutter = s.margin_inside_in !== undefined ? s.margin_inside_in : (s.margins.inside_gutter_in || 0.875);
  const outside = s.margin_outside_in !== undefined ? s.margin_outside_in : (s.margins.outside_margin_in || 0.625);
  const top = s.margin_top_in !== undefined ? s.margin_top_in : (s.margins.top_margin_in || 0.75);
  const bottom = s.margin_bottom_in !== undefined ? s.margin_bottom_in : (s.margins.bottom_margin_in || 0.875);

  const bodyFont = s.body_font || s.typography.body_font_name || p.body_font_name || "EB Garamond";
  const headingFont = s.heading_font || s.typography.display_font_name || p.display_font_name || "Cinzel";
  const monoFont = s.mono_font || s.typography.mono_font_name || p.mono_font_name || "JetBrains Mono";

  const bodySize = s.font_size_pt !== undefined ? s.font_size_pt : (s.typography.body_font_size_pt || 11.0);
  const lineHeightVal = s.line_height !== undefined ? s.line_height : 1.36;
  const indent = s.para_indent_in !== undefined ? s.para_indent_in : (s.typography.subsequent_p_indent_in || 0.25);
  const paraSpacing = s.para_spacing_pt !== undefined ? s.para_spacing_pt : 0.0;
  const letterSpacing = s.letter_spacing_em !== undefined ? s.letter_spacing_em : 0.0;
  const justifyText = s.justify_text !== false;
  const hyphenation = s.hyphenation !== false;

  const sinkage = s.chapter_sinkage_in !== undefined ? s.chapter_sinkage_in : (s.typography.chapter_sinkage_in || 1.75);
  const dropCapEnabled = s.drop_cap_enabled !== false;
  const dropCapLines = s.drop_cap_lines || 3;
  const dropCapStyle = s.drop_cap_style || "Plain Serif";
  const runningHeaderStyle = s.running_header_style || "Small Caps Centered";
  const headerText = s.typography.running_header_override || "";

  container.innerHTML = `
    <!-- Section 1: Typography Controls -->
    <div class="section-block">
      <div class="section-title">
        <span>🔤 Typography & Grid</span>
        <button onclick="resetTypographyToDefaults()" style="background:none; border:none; color:var(--accent-gold); font-size:0.68rem; cursor:pointer;">Defaults</button>
      </div>

      <div style="margin-bottom:8px;">
        <label style="font-size:0.7rem; color:var(--text-muted);">Body Font:</label>
        <select onchange="handleSettingsUpdate({ body_font: this.value, typography: { body_font_name: this.value } })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
          <option value="EB Garamond" ${bodyFont === 'EB Garamond' ? 'selected' : ''}>EB Garamond (Gaslamp / Classic)</option>
          <option value="Lora" ${bodyFont === 'Lora' ? 'selected' : ''}>Lora (Barometer / Chronometric)</option>
          <option value="Source Serif 4" ${bodyFont === 'Source Serif 4' ? 'selected' : ''}>Source Serif 4 (Acoustic / Cold)</option>
          <option value="Cormorant Garamond" ${bodyFont === 'Cormorant Garamond' ? 'selected' : ''}>Cormorant Garamond (Salt Orchard)</option>
          <option value="Crimson Pro" ${bodyFont === 'Crimson Pro' ? 'selected' : ''}>Crimson Pro (Archaeometric)</option>
          <option value="Baskerville" ${bodyFont === 'Baskerville' ? 'selected' : ''}>Baskerville (Transitional)</option>
          <option value="Georgia" ${bodyFont === 'Georgia' ? 'selected' : ''}>Georgia (Editorial)</option>
          <option value="Palatino" ${bodyFont === 'Palatino' ? 'selected' : ''}>Palatino (Renaissance)</option>
        </select>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
        <div>
          <label style="font-size:0.7rem; color:var(--text-muted);">Heading Font:</label>
          <select onchange="handleSettingsUpdate({ heading_font: this.value, typography: { display_font_name: this.value } })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.72rem; padding:4px; border-radius:3px;">
            <option value="Cinzel" ${headingFont === 'Cinzel' ? 'selected' : ''}>Cinzel</option>
            <option value="Oswald" ${headingFont === 'Oswald' ? 'selected' : ''}>Oswald</option>
            <option value="JetBrains Mono" ${headingFont === 'JetBrains Mono' ? 'selected' : ''}>JetBrains Mono</option>
            <option value="Cormorant Garamond" ${headingFont === 'Cormorant Garamond' ? 'selected' : ''}>Cormorant</option>
            <option value="Crimson Pro" ${headingFont === 'Crimson Pro' ? 'selected' : ''}>Crimson Pro</option>
          </select>
        </div>

        <div>
          <label style="font-size:0.7rem; color:var(--text-muted);">Monospace Font:</label>
          <select onchange="handleSettingsUpdate({ mono_font: this.value, typography: { mono_font_name: this.value } })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.72rem; padding:4px; border-radius:3px;">
            <option value="JetBrains Mono" ${monoFont === 'JetBrains Mono' ? 'selected' : ''}>JetBrains Mono</option>
            <option value="IBM Plex Mono" ${monoFont === 'IBM Plex Mono' ? 'selected' : ''}>IBM Plex Mono</option>
            <option value="Courier Prime" ${monoFont === 'Courier Prime' ? 'selected' : ''}>Courier Prime</option>
          </select>
        </div>
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Body Font Size:</span>
          <span class="slider-val-tag" id="val-font-size">${parseFloat(bodySize).toFixed(2)} pt</span>
        </div>
        <input type="range" min="9.0" max="13.5" step="0.25" value="${bodySize}" oninput="handleDebouncedSlider('font_size_pt', parseFloat(this.value), 'val-font-size', ' pt')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Leading / Line Height:</span>
          <span class="slider-val-tag" id="val-leading">${parseFloat(lineHeightVal).toFixed(2)}x</span>
        </div>
        <input type="range" min="1.15" max="1.65" step="0.02" value="${lineHeightVal}" oninput="handleDebouncedSlider('line_height', parseFloat(this.value), 'val-leading', 'x')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>First-Line Indent:</span>
          <span class="slider-val-tag" id="val-indent">${parseFloat(indent).toFixed(2)}"</span>
        </div>
        <input type="range" min="0.0" max="0.5" step="0.025" value="${indent}" oninput="handleDebouncedSlider('para_indent_in', parseFloat(this.value), 'val-indent', '\"')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Paragraph Spacing:</span>
          <span class="slider-val-tag" id="val-para-spacing">${parseFloat(paraSpacing).toFixed(1)} pt</span>
        </div>
        <input type="range" min="0.0" max="12.0" step="0.5" value="${paraSpacing}" oninput="handleDebouncedSlider('para_spacing_pt', parseFloat(this.value), 'val-para-spacing', ' pt')">
      </div>

      <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:0.75rem; color:var(--text-muted);">
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
          <input type="checkbox" ${justifyText ? 'checked' : ''} onchange="handleSettingsUpdate({ justify_text: this.checked })"> Justify Text
        </label>
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
          <input type="checkbox" ${hyphenation ? 'checked' : ''} onchange="handleSettingsUpdate({ hyphenation: this.checked })"> Hyphenation
        </label>
      </div>
    </div>

    <!-- Section 2: Page Geometry & Margins -->
    <div class="section-block">
      <div class="section-title">
        <span>📐 Page Geometry & Bleed</span>
        <span class="slider-val-tag">${trimW}" × ${trimH}"</span>
      </div>
      <div class="trim-preset-grid">
        <button class="btn-trim-preset ${trimW === 6.0 && trimH === 9.0 ? 'active' : ''}" onclick="updateTrimPreset(6.0, 9.0)">6.0 × 9.0" Trade</button>
        <button class="btn-trim-preset ${trimW === 5.5 && trimH === 8.5 ? 'active' : ''}" onclick="updateTrimPreset(5.5, 8.5)">5.5 × 8.5" Digest</button>
        <button class="btn-trim-preset ${trimW === 5.0 && trimH === 8.0 ? 'active' : ''}" onclick="updateTrimPreset(5.0, 8.0)">5.0 × 8.0" Pocket</button>
        <button class="btn-trim-preset ${trimW === 7.0 && trimH === 10.0 ? 'active' : ''}" onclick="updateTrimPreset(7.0, 10.0)">7.0 × 10.0" Royal</button>
      </div>

      <div class="inspector-slider-row" style="margin-top:10px;">
        <div class="slider-label-wrap">
          <span>Inside Gutter (Spine Fold):</span>
          <span class="slider-val-tag" id="val-gutter">${gutter.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.5" step="0.025" value="${gutter}" oninput="handleDebouncedMargin('margin_inside_in', parseFloat(this.value), 'val-gutter')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Outside Margin:</span>
          <span class="slider-val-tag" id="val-outside">${outside.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.375" max="1.25" step="0.025" value="${outside}" oninput="handleDebouncedMargin('margin_outside_in', parseFloat(this.value), 'val-outside')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Top Margin:</span>
          <span class="slider-val-tag" id="val-top">${top.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.25" step="0.025" value="${top}" oninput="handleDebouncedMargin('margin_top_in', parseFloat(this.value), 'val-top')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Bottom Margin:</span>
          <span class="slider-val-tag" id="val-bottom">${bottom.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.25" step="0.025" value="${bottom}" oninput="handleDebouncedMargin('margin_bottom_in', parseFloat(this.value), 'val-bottom')">
      </div>
    </div>

    <!-- Section 3: Chapter Opener & Drop-Caps -->
    <div class="section-block">
      <div class="section-title">
        <span>📖 Chapter Openers & Headers</span>
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Chapter Top Sinkage:</span>
          <span class="slider-val-tag" id="val-sinkage">${sinkage.toFixed(2)}"</span>
        </div>
        <input type="range" min="0.5" max="2.5" step="0.125" value="${sinkage}" oninput="handleDebouncedSlider('chapter_sinkage_in', parseFloat(this.value), 'val-sinkage', '\"')">
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
        <div>
          <label style="font-size:0.7rem; color:var(--text-muted);">Drop-Cap Style:</label>
          <select onchange="handleSettingsUpdate({ drop_cap_style: this.value })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.72rem; padding:4px; border-radius:3px;">
            <option value="Plain Serif" ${dropCapStyle === 'Plain Serif' ? 'selected' : ''}>Plain Serif</option>
            <option value="Boxed Rule" ${dropCapStyle === 'Boxed Rule' ? 'selected' : ''}>Boxed Rule</option>
            <option value="Botanical/Ornate" ${dropCapStyle === 'Botanical/Ornate' ? 'selected' : ''}>Botanical / Ornate</option>
            <option value="None" ${dropCapStyle === 'None' ? 'selected' : ''}>None</option>
          </select>
        </div>

        <div>
          <label style="font-size:0.7rem; color:var(--text-muted);">Drop-Cap Lines:</label>
          <select onchange="handleSettingsUpdate({ drop_cap_lines: parseInt(this.value, 10) })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.72rem; padding:4px; border-radius:3px;">
            <option value="2" ${dropCapLines === 2 ? 'selected' : ''}>2 Lines</option>
            <option value="3" ${dropCapLines === 3 ? 'selected' : ''}>3 Lines</option>
            <option value="4" ${dropCapLines === 4 ? 'selected' : ''}>4 Lines</option>
            <option value="5" ${dropCapLines === 5 ? 'selected' : ''}>5 Lines</option>
          </select>
        </div>
      </div>

      <div style="margin-bottom:8px;">
        <label style="font-size:0.7rem; color:var(--text-muted);">Running Header Style:</label>
        <select onchange="handleSettingsUpdate({ running_header_style: this.value })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.72rem; padding:4px; border-radius:3px;">
          <option value="Small Caps Centered" ${runningHeaderStyle === 'Small Caps Centered' ? 'selected' : ''}>Small Caps Centered</option>
          <option value="Small Caps Outer" ${runningHeaderStyle === 'Small Caps Outer' ? 'selected' : ''}>Small Caps Outer Margins</option>
          <option value="Rule Underlined" ${runningHeaderStyle === 'Rule Underlined' ? 'selected' : ''}>Rule Underlined Header</option>
          <option value="Hidden" ${runningHeaderStyle === 'Hidden' ? 'selected' : ''}>Hidden / Suppressed</option>
        </select>
      </div>

      <div>
        <label style="font-size:0.7rem; color:var(--text-muted);">Custom Verso Header Text:</label>
        <input type="text" value="${headerText}" placeholder="${p.short_title.toUpperCase()}" onchange="handleSettingsUpdate({ typography: { running_header_override: this.value } })" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:5px; border-radius:4px; margin-top:2px;">
      </div>
    </div>

    <!-- Section 4: Paper Tint -->
    <div class="section-block">
      <div class="section-title">
        <span>📜 Paper Tint & Texture</span>
      </div>
      <div style="display:flex; gap:6px; margin-top:4px;">
        <button onclick="updatePaperTint('#FBF8F1')" style="flex:1; height:24px; background:#FBF8F1; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Antique Cream"></button>
        <button onclick="updatePaperTint('#FAF6EE')" style="flex:1; height:24px; background:#FAF6EE; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Ochre Vellum"></button>
        <button onclick="updatePaperTint('#F5F6F8')" style="flex:1; height:24px; background:#F5F6F8; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Slate Crisp"></button>
        <button onclick="updatePaperTint('#FFFFFF')" style="flex:1; height:24px; background:#FFFFFF; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Pure White"></button>
      </div>
    </div>
  `;
}

// Debounced settings dispatchers
let settingsDebounce = null;
function handleDebouncedSlider(field, val, labelId, suffix = '') {
  document.getElementById(labelId).innerText = val + suffix;
  clearTimeout(settingsDebounce);
  settingsDebounce = setTimeout(async () => {
    const updates = {};
    updates[field] = val;
    await dispatchSettingsUpdate(updates);
  }, 250);
}

function handleDebouncedMargin(field, val, labelId) {
  document.getElementById(labelId).innerText = val.toFixed(3) + '"';
  clearTimeout(settingsDebounce);
  settingsDebounce = setTimeout(async () => {
    const updates = {};
    updates[field] = val;
    await dispatchSettingsUpdate(updates);
  }, 250);
}

function handleSettingsUpdate(updates) {
  dispatchSettingsUpdate(updates);
}

function updateTrimPreset(w, h) {
  dispatchSettingsUpdate({ trim_width_in: w, trim_height_in: h });
}

function updatePaperTint(hex) {
  dispatchSettingsUpdate({ typography: { paper_tint: hex } });
}

async function resetTypographyToDefaults() {
  await dispatchSettingsUpdate({
    font_size_pt: 11.0,
    line_height: 1.36,
    para_indent_in: 0.25,
    para_spacing_pt: 0.0,
    letter_spacing_em: 0.0,
    justify_text: true,
    hyphenation: true
  });
}

// ======================================================================
// 9. FRONT & BACK MATTER EDITOR (TAB 2)
// ======================================================================
function renderFrontMatterTab(container) {
  const fm = state.settings?.front_back_matter || {};

  const glossaryRaw = typeof fm.glossary_terms === "string"
    ? fm.glossary_terms
    : (Array.isArray(fm.glossary_terms) ? fm.glossary_terms.map(g => (g.term + ": " + g.definition)).join("\n") : "");

  container.innerHTML = `
    <div class="section-block">
      <div class="section-title">
        <span>📖 Front & Back Matter Suite</span>
        <button onclick="saveMatterSettings()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:3px 8px; border-radius:4px; font-size:0.68rem; cursor:pointer;">Save Matter</button>
      </div>

      <div style="display:flex; flex-direction:column; gap:10px; font-size:0.75rem; color:var(--text-muted);">
        <!-- Half Title -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-half-title" ${fm.include_half_title !== false ? 'checked' : ''}> Half-Title Page
          </label>
          <input type="text" id="fm-half-title-text" value="${fm.half_title_text || ''}" placeholder="Half-title text..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
        </div>

        <!-- Frontispiece -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-frontispiece" ${fm.include_frontispiece !== false ? 'checked' : ''}> Frontispiece Ornament Plate
          </label>
          <input type="text" id="fm-frontispiece-subtitle" value="${fm.frontispiece_subtitle || ''}" placeholder="Frontispiece subtitle..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:6px;">
          <input type="file" id="fm-frontispiece-file" style="display:none;" accept="image/*" onchange="uploadMatterImage('frontispiece', this.files[0])">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
            <button type="button" onclick="document.getElementById('fm-frontispiece-file').click()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:var(--accent-gold); font-size:0.7rem; font-weight:600; padding:3px 8px; border-radius:3px; cursor:pointer;">
              🖼️ Upload Frontispiece Art
            </button>
            ${fm.frontispiece_image_url ? `<span style="font-size:0.68rem; color:var(--accent-cyan); display:flex; align-items:center; gap:4px;"><img src="${fm.frontispiece_image_url}" style="height:22px; border-radius:2px; border:1px solid #555;"> Active</span>` : '<span style="font-size:0.68rem; color:#666;">Procedural SVG Ornament</span>'}
          </div>
        </div>

        <!-- Title Page -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-title-page" ${fm.include_title_page !== false ? 'checked' : ''}> Title Page (Imprint)
          </label>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
            <input type="text" id="fm-book-title" value="${fm.book_title || ''}" placeholder="Book title..." style="background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
            <input type="text" id="fm-author-name" value="${fm.author_name || ''}" placeholder="Author name..." style="background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
          </div>
        </div>

        <!-- Copyright -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-copyright" ${fm.include_copyright !== false ? 'checked' : ''}> Copyright & ISBN Page
          </label>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
            <input type="text" id="fm-copyright-year" value="${fm.copyright_year || ''}" placeholder="Year (e.g. 2026)" style="background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
            <input type="text" id="fm-isbn" value="${fm.isbn || ''}" placeholder="ISBN (e.g. 978-1-958823-01-4)" style="background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
          </div>
        </div>

        <!-- Dedication -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-dedication" ${fm.include_dedication ? 'checked' : ''}> Dedication Page
          </label>
          <input type="text" id="fm-dedication-text" value="${fm.dedication_text || ''}" placeholder="Dedication text..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
        </div>

        <!-- Epigraph -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-epigraph" ${fm.include_epigraph ? 'checked' : ''}> Epigraph Page
          </label>
          <input type="text" id="fm-epigraph-text" value="${fm.epigraph_text || ''}" placeholder="Epigraph quote..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:4px;">
          <input type="text" id="fm-epigraph-source" value="${fm.epigraph_source || ''}" placeholder="Source attribution..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">
        </div>

        <!-- TOC -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; cursor:pointer;">
            <input type="checkbox" id="fm-toc" ${fm.include_toc !== false ? 'checked' : ''}> Auto-Calculated Contents (TOC)
          </label>
        </div>

        <!-- Pre-Book Map Plate -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-map" ${fm.include_map ? 'checked' : ''}> Pre-Book Map / Territory Plate
          </label>
          <input type="text" id="fm-map-title" value="${fm.map_title || ''}" placeholder="Map Title..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:4px;">
          <input type="text" id="fm-map-caption" value="${fm.map_caption || ''}" placeholder="Map Caption..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:6px;">
          <input type="file" id="fm-map-file" style="display:none;" accept="image/*" onchange="uploadMatterImage('map', this.files[0])">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
            <button type="button" onclick="document.getElementById('fm-map-file').click()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:var(--accent-cyan); font-size:0.7rem; font-weight:600; padding:3px 8px; border-radius:3px; cursor:pointer;">
              🗺️ Upload Territory Map Art
            </button>
            ${fm.map_image_url ? `<span style="font-size:0.68rem; color:var(--accent-cyan); display:flex; align-items:center; gap:4px;"><img src="${fm.map_image_url}" style="height:22px; border-radius:2px; border:1px solid #555;"> Active</span>` : '<span style="font-size:0.68rem; color:#666;">Procedural Cartography Grid</span>'}
          </div>
        </div>

        <!-- Post-Book Appendix -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-appendix" ${fm.include_appendix ? 'checked' : ''}> Post-Book Historical Appendix
          </label>
          <input type="text" id="fm-appendix-title" value="${fm.appendix_title || ''}" placeholder="Appendix Title..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:4px;">
          <textarea id="fm-appendix-text" rows="3" placeholder="Appendix text content..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">${fm.appendix_text || ''}</textarea>
        </div>

        <!-- Post-Book Glossary -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-glossary" ${fm.include_glossary ? 'checked' : ''}> Post-Book Lexicon / Glossary
          </label>
          <input type="text" id="fm-glossary-title" value="${fm.glossary_title || ''}" placeholder="Glossary Title..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:4px;">
          <textarea id="fm-glossary-terms" rows="4" placeholder="Term: Definition (one per line)..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">${glossaryRaw}</textarea>
        </div>

        <!-- Acknowledgements -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-acknowledgements" ${fm.include_acknowledgements ? 'checked' : ''}> Acknowledgements
          </label>
          <textarea id="fm-acknowledgements-text" rows="3" placeholder="Acknowledgements text..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">${fm.acknowledgements_text || ''}</textarea>
        </div>

        <!-- About the Author -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-about-author" ${fm.include_about_author ? 'checked' : ''}> About the Author
          </label>
          <textarea id="fm-about-author-text" rows="3" placeholder="Author biography..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">${fm.about_author_text || ''}</textarea>
        </div>

        <!-- Typesetting Colophon -->
        <div class="matter-card">
          <label style="display:flex; align-items:center; gap:6px; font-weight:700; color:#FFF; margin-bottom:4px; cursor:pointer;">
            <input type="checkbox" id="fm-colophon" ${fm.include_colophon !== false ? 'checked' : ''}> Typesetting Colophon
          </label>
          <textarea id="fm-colophon-text" rows="3" placeholder="Colophon text..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">${fm.colophon_text || ''}</textarea>
        </div>
      </div>
    </div>
  `;
}

async function uploadMatterImage(imageType, file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    showToast(`Uploading ${imageType} artwork...`, "info");
    const res = await fetch(`/api/matter/upload-image/${state.activeBookId}/${imageType}`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    const data = await res.json();
    showToast(`${imageType.toUpperCase()} artwork uploaded and wired!`, "success");
    await loadBook(state.activeBookId);
  } catch (err) {
    console.error(`Error uploading ${imageType}:`, err);
    showToast(err.message, "error");
  }
}

async function saveMatterSettings() {
  const fmCurrent = state.settings?.front_back_matter || {};
  const updates = {
    front_back_matter: {
      include_half_title: document.getElementById("fm-half-title").checked,
      half_title_text: document.getElementById("fm-half-title-text").value,
      include_frontispiece: document.getElementById("fm-frontispiece").checked,
      frontispiece_subtitle: document.getElementById("fm-frontispiece-subtitle").value,
      frontispiece_image_url: fmCurrent.frontispiece_image_url || "",
      include_title_page: document.getElementById("fm-title-page").checked,
      book_title: document.getElementById("fm-book-title").value,
      author_name: document.getElementById("fm-author-name").value,
      include_copyright: document.getElementById("fm-copyright").checked,
      copyright_year: document.getElementById("fm-copyright-year").value,
      isbn: document.getElementById("fm-isbn").value,
      include_dedication: document.getElementById("fm-dedication").checked,
      dedication_text: document.getElementById("fm-dedication-text").value,
      include_epigraph: document.getElementById("fm-epigraph").checked,
      epigraph_text: document.getElementById("fm-epigraph-text").value,
      epigraph_source: document.getElementById("fm-epigraph-source").value,
      include_toc: document.getElementById("fm-toc").checked,
      include_map: document.getElementById("fm-map").checked,
      map_title: document.getElementById("fm-map-title").value,
      map_caption: document.getElementById("fm-map-caption").value,
      map_image_url: fmCurrent.map_image_url || "",
      include_appendix: document.getElementById("fm-appendix").checked,
      appendix_title: document.getElementById("fm-appendix-title").value,
      appendix_text: document.getElementById("fm-appendix-text").value,
      include_glossary: document.getElementById("fm-glossary").checked,
      glossary_title: document.getElementById("fm-glossary-title").value,
      glossary_terms: document.getElementById("fm-glossary-terms").value,
      include_acknowledgements: document.getElementById("fm-acknowledgements").checked,
      acknowledgements_text: document.getElementById("fm-acknowledgements-text").value,
      include_about_author: document.getElementById("fm-about-author").checked,
      about_author_text: document.getElementById("fm-about-author-text").value,
      include_colophon: document.getElementById("fm-colophon").checked,
      colophon_text: document.getElementById("fm-colophon-text").value,
    }
  };
  showToast("Updating front & back matter...", "info");
  await dispatchSettingsUpdate(updates);
  showToast("Front & back matter updated and paginated!", "success");
}

async function dispatchSettingsUpdate(updates) {
  const res = await fetchAPI(`/api/project/${state.activeBookId}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates)
  });
  if (res.status === "success") {
    state.settings = res.settings;
    state.pagination = res.pagination;
    renderSpreadCanvas();
    renderFilmstrip();
    renderHeader();
  }
}

// ======================================================================
// 10. RELEASE & EXPORT SUITE (TAB 3)
// ======================================================================
function renderExportTab(container) {
  const s = state.settings || { typography: {}, margins: {} };

  container.innerHTML = `
    <div class="section-block" style="border-color:var(--accent-gold);">
      <div class="section-title">
        <span>🚀 One-Click Export Suite</span>
        <label style="font-size:0.68rem; display:flex; align-items:center; gap:4px; text-transform:none; color:var(--text-main); cursor:pointer;">
          <input type="checkbox" id="export-bleed-toggle" ${state.showBleed ? "checked" : ""} onchange="state.showBleed = this.checked; renderSpreadCanvas();">
          +0.125" Bleed
        </label>
      </div>

      <div style="font-size:0.73rem; color:var(--text-muted); margin-bottom:12px; background:rgba(0,0,0,0.3); padding:8px; border-radius:4px;">
        <strong>Active Release Specifications:</strong><br>
        • Trim: ${s.trim_width_in || 6.0}" × ${s.trim_height_in || 9.0}"<br>
        • Margins: Gutter ${s.margin_inside_in || 0.875}", Outside ${s.margin_outside_in || 0.625}"<br>
        • Typography: ${s.body_font || 'EB Garamond'} (${s.font_size_pt || 11}pt)<br>
        • Real-time synchronization active across all formats!
      </div>

      <button class="btn-export" onclick="exportDocument('pdf')">
        <span>📄 Print-Ready PDF</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">6x9" Mirrored</span>
      </button>

      <button class="btn-export" onclick="exportDocument('docx')">
        <span>📝 Styled Word DOCX</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">Editable</span>
      </button>

      <button class="btn-export" onclick="exportDocument('epub')">
        <span>📱 Reflowable EPUB 3</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">e-Readers</span>
      </button>

      <div style="margin-top:10px;">
        <button class="btn-export btn-export-all" onclick="exportDocument('all')">
          <span>📦 Export Release Bundle (.ZIP)</span>
          <span>PDF + DOCX + EPUB</span>
        </button>
      </div>
    </div>
  `;
}

async function exportDocument(format) {
  const bleed = state.showBleed;
  showToast(`Compiling ${format.toUpperCase()} with live typography & publishing rules...`, "info");

  const endpoint = `/api/export/${format}`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: state.activeBookId, bleed: bleed })
  });

  if (!res.ok) {
    showToast(`Failed to export ${format.toUpperCase()}`, "error");
    return;
  }

  const blob = await res.blob();
  const filename = format === "all"
    ? `${state.activeBookId}_ArgonPublishingPackage.zip`
    : format === "pdf"
    ? `${state.activeBookId}_print_edition.pdf`
    : format === "docx"
    ? `${state.activeBookId}_styled_edition.docx`
    : `${state.activeBookId}_reflowable_edition.epub`;

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  showToast(`${filename} compiled & downloaded successfully!`, "success");
}

// ======================================================================
// 11. IMAGE PRINT LAB (SPLIT BEFORE/AFTER COMPARISON)
// ======================================================================
function openImageLabModal(assetId) {
  const asset = state.manifest.assets.find(a => a.id === assetId);
  if (!asset) return;

  const p = state.activeBook || state.profiles["book01"];
  state.imageLabState.assetId = assetId;
  state.imageLabState.filter_preset = p.filter_preset;
  state.imageLabState.grain = 0.08;
  state.imageLabState.contrast = 1.35;
  state.imageLabState.vignette = 0.38;
  state.imageLabState.brightness = 1.0;
  state.imageLabState.splitPercent = 50;

  renderImageLabModal();
  triggerImageLabPreview();
}

function renderImageLabModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const asset = state.manifest.assets.find(a => a.id === state.imageLabState.assetId);
  if (!asset) return;

  const lab = state.imageLabState;

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:780px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-gold);">
            🔬 Print Texture Lab — Interactive Split Before/After
          </h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body" style="padding:14px; display:flex; flex-direction:column; gap:12px;">
          
          <!-- Split Before / After Slider Canvas -->
          <div id="split-slider-container" class="split-slider-wrap" onmousedown="startDraggingSplit(event)">
            <!-- Before Image (Left / Raw) -->
            <img class="split-img-before" src="${asset.image_url}" alt="Before">
            
            <!-- After Filtered Image (Right) -->
            <div id="split-after-wrap" class="split-img-after-wrap" style="width:${lab.splitPercent}%;">
              <img id="split-after-img" class="split-img-after" src="${asset.image_url}" alt="After">
            </div>

            <!-- Divider Line & Knob -->
            <div id="split-handle" class="split-handle-bar" style="left:${lab.splitPercent}%;">
              <div class="split-handle-knob">⇄</div>
            </div>

            <!-- Labels -->
            <div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.6); padding:2px 6px; border-radius:3px; font-size:0.65rem; color:#FFF; pointer-events:none;">BEFORE (RAW)</div>
            <div style="position:absolute; top:8px; right:8px; background:rgba(217,119,6,0.8); padding:2px 6px; border-radius:3px; font-size:0.65rem; color:#000; font-weight:700; pointer-events:none;">AFTER (300 DPI FILTER)</div>
          </div>

          <!-- Parameter Sliders -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; background:var(--bg-card); padding:12px; border-radius:6px;">
            <div>
              <div class="slider-label-wrap">
                <span>Filter Medium:</span>
              </div>
              <select onchange="updateImageLabParam('filter_preset', this.value)" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:5px; border-radius:3px; margin-bottom:8px;">
                <option value="cyanotype_silver_plate" ${lab.filter_preset === 'cyanotype_silver_plate' ? 'selected' : ''}>Cyanotype / 19th-C Silver Plate</option>
                <option value="charcoal_lithograph" ${lab.filter_preset === 'charcoal_lithograph' ? 'selected' : ''}>Charcoal & Hebridean Lithograph</option>
                <option value="blueprint_halftone" ${lab.filter_preset === 'blueprint_halftone' ? 'selected' : ''}>Blueprint Halftone & Oscilloscope</option>
                <option value="sepia_bioluminescent_amber" ${lab.filter_preset === 'sepia_bioluminescent_amber' ? 'selected' : ''}>1928 Sepia & Bioluminescent Amber</option>
                <option value="desert_ochre_uv" ${lab.filter_preset === 'desert_ochre_uv' ? 'selected' : ''}>Desert Ochre & UV Fluorescence</option>
              </select>

              <div class="inspector-slider-row">
                <div class="slider-label-wrap">
                  <span>Grain Intensity:</span>
                  <span class="slider-val-tag" id="lab-val-grain">${(lab.grain * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0.0" max="0.22" step="0.01" value="${lab.grain}" oninput="updateImageLabParam('grain', parseFloat(this.value)); document.getElementById('lab-val-grain').innerText = (this.value * 100).toFixed(0) + '%'">
              </div>
            </div>

            <div>
              <div class="inspector-slider-row">
                <div class="slider-label-wrap">
                  <span>Contrast & Shadow Depth:</span>
                  <span class="slider-val-tag" id="lab-val-contrast">${lab.contrast.toFixed(2)}x</span>
                </div>
                <input type="range" min="0.7" max="2.2" step="0.05" value="${lab.contrast}" oninput="updateImageLabParam('contrast', parseFloat(this.value)); document.getElementById('lab-val-contrast').innerText = parseFloat(this.value).toFixed(2) + 'x'">
              </div>

              <div class="inspector-slider-row">
                <div class="slider-label-wrap">
                  <span>Edge Vignette Falloff:</span>
                  <span class="slider-val-tag" id="lab-val-vignette">${(lab.vignette * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0.0" max="0.75" step="0.02" value="${lab.vignette}" oninput="updateImageLabParam('vignette', parseFloat(this.value)); document.getElementById('lab-val-vignette').innerText = (this.value * 100).toFixed(0) + '%'">
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer" style="padding:12px 16px; background:rgba(0,0,0,0.3); border-top:1px solid var(--border-subtle); display:flex; justify-content:flex-end; gap:8px;">
          <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 12px; border-radius:4px; cursor:pointer;">Cancel</button>
          <button onclick="applyImageLabPermanently()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Apply & Save at 300 DPI</button>
        </div>
      </div>
    </div>
  `;
}

let labDebounce = null;
function updateImageLabParam(key, val) {
  state.imageLabState[key] = val;
  clearTimeout(labDebounce);
  labDebounce = setTimeout(triggerImageLabPreview, 250);
}

async function triggerImageLabPreview() {
  const lab = state.imageLabState;
  const res = await fetchAPI("/api/image-lab/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: state.activeBookId,
      asset_id: lab.assetId,
      filter_preset: lab.filter_preset,
      contrast: lab.contrast,
      grain: lab.grain,
      vignette: lab.vignette,
      brightness: lab.brightness
    })
  });
  if (res.status === "success" && res.preview_data_uri) {
    const afterImg = document.getElementById("split-after-img");
    if (afterImg) afterImg.src = res.preview_data_uri;
  }
}

function startDraggingSplit(event) {
  const container = document.getElementById("split-slider-container");
  if (!container) return;

  const rect = container.getBoundingClientRect();

  function onMouseMove(moveEvent) {
    const x = moveEvent.clientX - rect.left;
    const pct = Math.max(5, Math.min(95, (x / rect.width) * 100));
    state.imageLabState.splitPercent = pct;

    const afterWrap = document.getElementById("split-after-wrap");
    const handle = document.getElementById("split-handle");
    if (afterWrap) afterWrap.style.width = `${pct}%`;
    if (handle) handle.style.left = `${pct}%`;
  }

  function onMouseUp() {
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
  }

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}

async function applyImageLabPermanently() {
  const lab = state.imageLabState;
  showToast("Applying print texture filter and resampling to 300 DPI...", "info");

  const res = await fetchAPI("/api/image-lab/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: state.activeBookId,
      asset_id: lab.assetId,
      filter_preset: lab.filter_preset,
      contrast: lab.contrast,
      grain: lab.grain,
      vignette: lab.vignette,
      brightness: lab.brightness,
      target_dpi: lab.target_dpi
    })
  });

  if (res.status === "success") {
    showToast("Print texture applied at 300 DPI!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// ======================================================================
// 12. TAILPIECE BALANCING & DRAG-AND-DROP RE-ANCHORING
// ======================================================================
async function autoInsertTailpiece(pageNumber) {
  showToast(`Inserting thematic tailpiece ornament on page ${pageNumber}...`, "info");
  const res = await fetchAPI("/api/tailpiece/auto-insert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: state.activeBookId,
      page_number: pageNumber,
      enable: true
    })
  });

  if (res.status === "success") {
    showToast("Whitespace balanced with authentic tailpiece ornament!", "success");
    state.pagination = res.pagination;
    renderSpreadCanvas();
    renderFilmstrip();
  }
}

function handleAssetDragStart(event, assetId) {
  event.dataTransfer.setData("text/plain", assetId);
  event.dataTransfer.effectAllowed = "move";
}

function handleDragOver(event) {
  event.preventDefault();
  event.currentTarget.classList.add("dragover");
}

function handleDragLeave(event) {
  event.currentTarget.classList.remove("dragover");
}

async function handleDropAnchor(event, targetAnchor) {
  event.preventDefault();
  event.currentTarget.classList.remove("dragover");

  const assetId = event.dataTransfer.getData("text/plain");
  if (!assetId) return;

  showToast(`Moving ${assetId} to anchor ${targetAnchor}...`, "info");
  const res = await fetchAPI(`/api/manifest/${state.activeBookId}/update-anchor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ asset_id: assetId, new_anchor: targetAnchor })
  });

  if (res.status === "success") {
    showToast(`Slot anchored to ${targetAnchor}! Pagination updated.`, "success");
    state.pagination = res.pagination;
    const asset = state.manifest.assets.find(a => a.id === assetId);
    if (asset) asset.anchor = targetAnchor;
    renderAll();
  }
}

async function handleDropImage(event, assetId) {
  event.preventDefault();
  event.currentTarget.classList.remove("dragover");

  if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0];
    await uploadImageFile(assetId, file);
  }
}

function triggerFileInput(assetId) {
  const input = document.getElementById(`file-input-${assetId}`);
  if (input) input.click();
}

async function uploadImageFile(assetId, file) {
  if (!file) return;

  showToast(`Uploading & applying 300 DPI print filter to ${file.name}...`, "info");
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`/api/assets/upload/${state.activeBookId}/${assetId}`, {
    method: "POST",
    body: formData
  });
  const data = await res.json();
  if (data.status === "success") {
    showToast("Print texture filter applied at 300 DPI!", "success");
    state.pagination = data.pagination;
    const asset = state.manifest.assets.find(a => a.id === assetId);
    if (asset) {
      asset.image_url = data.image_url;
      asset.filter_applied = true;
    }
    renderAll();
  }
}

function copyPrompt(assetId, btn) {
  let text = "";
  if (state.manifest && Array.isArray(state.manifest.assets)) {
    const asset = state.manifest.assets.find(a => a.id === assetId);
    if (asset && asset.prompt) text = asset.prompt;
  }
  if (!text && btn) {
    const box = btn.closest(".asset-prompt-box");
    if (box) {
      const span = box.querySelector("span:last-child");
      if (span) text = (span.innerText || span.textContent || "").trim();
    }
  }
  copyTextToClipboard(text, btn);
}

function openAddSlotModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:520px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-gold);">+ Add New Illustration Slot</h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body" style="padding:14px; display:flex; flex-direction:column; gap:10px;">
          <div>
            <label style="font-size:0.72rem; color:var(--text-muted);">Title</label>
            <input type="text" id="new-slot-title" placeholder="e.g. The Autopsy Lantern" style="width:100%; padding:6px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">
          </div>
          <div>
            <label style="font-size:0.72rem; color:var(--text-muted);">Anchor Paragraph ID</label>
            <input type="text" id="new-slot-anchor" placeholder="e.g. ch01_p02" value="ch01_p02" style="width:100%; padding:6px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">
          </div>
          <div>
            <label style="font-size:0.72rem; color:var(--text-muted);">Placement</label>
            <select id="new-slot-placement" style="width:100%; padding:6px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">
              <option value="Half-Page Top">Half-Page Top</option>
              <option value="Full-Page Recto Plate">Full-Page Recto Plate</option>
              <option value="Full-Page Verso Plate">Full-Page Verso Plate</option>
              <option value="Full Bleed Plate">Full Bleed Plate</option>
              <option value="Inline Archival Insert">Inline Archival Insert</option>
              <option value="Chapter Opener Vignette">Chapter Opener Vignette</option>
              <option value="Chapter End Tailpiece">Chapter End Tailpiece</option>
            </select>
          </div>
          <div>
            <label style="font-size:0.72rem; color:var(--text-muted);">Generation Prompt</label>
            <textarea id="new-slot-prompt" rows="3" placeholder="Midjourney / DALL-E prompt..." style="width:100%; padding:6px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; border-radius:3px;">Atmospheric etching matching book theme</textarea>
          </div>
        </div>
        <div class="modal-footer" style="padding:10px 14px; background:rgba(0,0,0,0.3); border-top:1px solid var(--border-subtle); display:flex; justify-content:flex-end; gap:8px;">
          <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 12px; border-radius:4px; cursor:pointer;">Cancel</button>
          <button onclick="submitNewSlot()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Add Slot</button>
        </div>
      </div>
    </div>
  `;
}

async function submitNewSlot() {
  const title = document.getElementById("new-slot-title").value.trim() || "New Illustration";
  const anchor = document.getElementById("new-slot-anchor").value.trim() || "ch01_p01";
  const placement = document.getElementById("new-slot-placement").value;
  const prompt = document.getElementById("new-slot-prompt").value.trim() || "Etching";

  showToast("Adding new planned illustration slot...", "info");
  const res = await fetchAPI(`/api/manifest/${state.activeBookId}/add-slot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      anchor,
      placement,
      prompt,
      caption: `Plate: ${title}`
    })
  });

  if (res.status === "success") {
    showToast("Illustration slot added!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// Navigation & View Helpers
function nextSpread() {
  if (state.currentSpreadIndex < state.pagination.spreads.length - 1) {
    state.currentSpreadIndex++;
    renderSpreadCanvas();
    renderFilmstrip();
  }
}

function prevSpread() {
  if (state.currentSpreadIndex > 0) {
    state.currentSpreadIndex--;
    renderSpreadCanvas();
    renderFilmstrip();
  }
}

function setZoom(level) {
  state.zoomLevel = level;
  renderSpreadCanvas();
}

function toggleMargins() {
  state.showMargins = !state.showMargins;
  renderSpreadCanvas();
}

function toggleBleed() {
  state.showBleed = !state.showBleed;
  renderSpreadCanvas();
  renderRightPanel();
}

function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  const modal = document.getElementById("modal-container");
  if (modal) modal.innerHTML = "";
}

// ======================================================================
// LOCAL AI BOOK ART DIRECTOR & AUTONOMOUS LAYOUT SUITE
// ======================================================================

async function checkLocalAIStatus(showToastNotify = false) {
  const dot = document.getElementById("ai-status-dot");
  const text = document.getElementById("ai-status-text");

  try {
    const res = await fetch("/api/ai/status");
    const data = await res.json();
    if (data.status === "success" && data.connection) {
      const conn = data.connection;
      state.aiConnection = conn;
      state.aiConfig = data.config;

      if (conn.status === "online") {
        if (dot) dot.className = "status-dot online";
        if (text) text.innerText = `🟢 Local AI Online (${conn.selected_model})`;
        if (showToastNotify) showToast(`Connected to local LLM: ${conn.selected_model}`, "success");
      } else {
        if (dot) dot.className = "status-dot offline";
        if (text) text.innerText = `🟡 Built-in Heuristics (Click to Config)`;
        if (showToastNotify) showToast("Local LLM offline. High-Fidelity Heuristics active.", "info");
      }
    }
  } catch (err) {
    if (dot) dot.className = "status-dot offline";
    if (text) text.innerText = `🟡 Built-in Heuristics Active`;
  }
}

function openAIConfigModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const conf = state.aiConfig || { endpoint_url: "http://localhost:11434", model: "llama3.1", timeout_sec: 30 };
  const conn = state.aiConnection || {};
  const models = conn.models || ["llama3.1", "qwen2.5", "mistral", "gemma2"];

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-card" style="max-width:540px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3>⚙️ Local AI Director Configuration</h3>
          <button class="btn-close-modal" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
          <p style="font-size:0.84rem; color:var(--text-muted); margin-bottom:14px;">
            Connect Argon Studio to your local AI engine (Ollama, LM Studio, or llama.cpp) for autonomous book art direction.
          </p>

          <div style="margin-bottom:12px;">
            <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
              LOCAL SERVER ENDPOINT URL
            </label>
            <input type="text" id="ai-endpoint-input" value="${conf.endpoint_url || 'http://localhost:11434'}" 
                   style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-family:monospace; font-size:0.85rem;">
            <span style="font-size:0.72rem; color:var(--text-muted);">Default: http://localhost:11434 (Ollama) or http://localhost:1234/v1 (LM Studio)</span>
          </div>

          <div style="margin-bottom:12px;">
            <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
              MODEL NAME
            </label>
            <input type="text" id="ai-model-input" value="${conf.model || 'llama3.1'}" list="ai-models-datalist"
                   style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; padding:8px 10px; border-radius:4px; font-size:0.85rem;">
            <datalist id="ai-models-datalist">
              ${models.map(m => `<option value="${m}"></option>`).join('')}
            </datalist>
          </div>

          <div style="margin-bottom:16px;">
            <label style="font-size:0.75rem; color:#AAA; font-weight:700; display:block; margin-bottom:4px;">
              INSPECTION STATUS
            </label>
            <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border-subtle); border-radius:4px; padding:10px; font-size:0.8rem; color:${conn.status === 'online' ? '#10B981' : '#F59E0B'};">
              ${conn.message || 'Status check pending.'}
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; gap:10px;">
            <button class="btn-secondary-action" onclick="testAIConnection()">
              🔌 Test Connection
            </button>
            <button class="btn-wizard-primary" onclick="saveAIConfig()">
              💾 Save & Connect
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function testAIConnection() {
  const endpoint = document.getElementById("ai-endpoint-input").value.trim();
  const model = document.getElementById("ai-model-input").value.trim();
  showToast("Testing local AI connection...", "info");

  try {
    const res = await fetch("/api/ai/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint_url: endpoint, model: model })
    });
    const data = await res.json();
    if (data.status === "success") {
      state.aiConnection = data.connection;
      state.aiConfig = data.config;
      checkLocalAIStatus(false);
      openAIConfigModal();
      if (data.connection.status === "online") {
        showToast("Connected to local AI successfully!", "success");
      } else {
        showToast("Server offline. Built-in heuristics active.", "info");
      }
    }
  } catch (err) {
    showToast(`Connection failed: ${err.message}`, "error");
  }
}

async function saveAIConfig() {
  const endpoint = document.getElementById("ai-endpoint-input").value.trim();
  const model = document.getElementById("ai-model-input").value.trim();

  try {
    const res = await fetch("/api/ai/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint_url: endpoint, model: model })
    });
    const data = await res.json();
    state.aiConnection = data.connection;
    state.aiConfig = data.config;
    checkLocalAIStatus(false);
    closeModal();
    showToast("AI Director settings saved!", "success");
  } catch (err) {
    showToast(`Error saving settings: ${err.message}`, "error");
  }
}

async function runAIDirector() {
  const btn = document.getElementById("btn-run-ai-director");
  const origText = btn.innerHTML;
  btn.innerHTML = "⏳ AI Director Reading Manuscript...";
  btn.disabled = true;

  const targetCount = parseInt(document.getElementById("target-plates-slider")?.value || "16", 10);
  showToast(`Local AI Art Director analyzing manuscript & generating ${targetCount}-slot blueprint...`, "info");

  try {
    const res = await fetch(`/api/ai/analyze/${state.activeBookId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_illustrations: targetCount })
    });
    const data = await res.json();

    if (data.status === "success" && data.blueprint) {
      state.lastAIBlueprint = data.blueprint;
      renderAIReview(data.blueprint);
      showToast("✨ AI Art Director proposal ready for review!", "success");
    } else {
      showToast(`AI Director error: ${data.detail || "Analysis failed"}`, "error");
    }
  } catch (err) {
    showToast(`AI Director failed: ${err.message}`, "error");
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

function renderAIReview(blueprint) {
  const reviewCard = document.getElementById("ai-director-review");
  if (!reviewCard) return;

  reviewCard.style.display = "block";
  document.getElementById("ai-review-genre").innerText = blueprint.genre_style || "Historical Speculative Fiction";
  document.getElementById("ai-review-engine").innerText = blueprint.engine || "Generated by Argon Local AI Suite";
  document.getElementById("ai-plates-count").innerText = (blueprint.assets || []).length;

  const typo = blueprint.typography_overrides || {};
  const matter = blueprint.front_back_matter || {};
  const assets = blueprint.assets || [];

  // 1. Typography Pane
  const typoPane = document.getElementById("ai-tab-pane-typo");
  typoPane.innerHTML = `
    <div class="ai-spec-grid">
      <div class="ai-spec-box">
        <div class="ai-spec-label">Body Typography</div>
        <div class="ai-spec-value">${typo.body_font_name || 'Cormorant Garamond'} (${typo.font_size_pt || 10.5}pt / ${typo.line_height || 1.38})</div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Chapter Heading Font</div>
        <div class="ai-spec-value">${typo.heading_font_name || 'Cinzel'}</div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Print Texture Filter</div>
        <div class="ai-spec-value">${(typo.filter_preset || 'cyanotype_silver_plate').replace(/_/g, ' ')}</div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Drop Cap Initial</div>
        <div class="ai-spec-value">${typo.drop_cap_style || 'Engraved Gothic Initial'} (${typo.drop_cap_lines || 3} lines)</div>
      </div>
    </div>
  `;

  // 2. Mandatory Pages Pane
  const matterPane = document.getElementById("ai-tab-pane-matter");
  matterPane.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:8px;">
      <div class="ai-spec-box">
        <div class="ai-spec-label">Title Page Draft</div>
        <div class="ai-spec-value" style="font-size:0.85rem;">
          "${matter.title_page?.title || 'Book Title'}" — ${matter.title_page?.subtitle || ''} by ${matter.title_page?.author || 'Author'}
        </div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Proposed Epigraph</div>
        <div style="font-style:italic; color:#EEE;">"${matter.epigraph_text || ''}"</div>
        <div style="font-size:0.75rem; color:#38BDF8; margin-top:2px;">${matter.epigraph_source || ''}</div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Dedication</div>
        <div style="font-style:italic; color:#EEE;">"${matter.dedication_text || ''}"</div>
      </div>
      <div class="ai-spec-box">
        <div class="ai-spec-label">Colophon & Production Note</div>
        <div style="font-size:0.78rem; color:#BBB;">${matter.colophon_text || ''}</div>
      </div>
    </div>
  `;

  // 3. Character Consistency Bible Pane
  const characters = blueprint.character_dossiers || [];
  const charCountEl = document.getElementById("ai-characters-count");
  if (charCountEl) charCountEl.textContent = characters.length;

  const charPane = document.getElementById("ai-tab-pane-characters");
  if (charPane) {
    charPane.innerHTML = `
      <div style="margin-bottom:12px; color:#94A3B8; font-size:0.8rem; line-height:1.4;">
        <strong style="color:#38BDF8;">Locked Character Identity System:</strong> To keep character faces, hair, and clothing 100% identical across all illustrations, copy the <em>Locked Prompt Anchor</em> into your image prompts, or generate the <em>Master Turnaround Sheet</em> first to use as a Midjourney <code style="color:#FBBF24;">--cref</code> character reference.
      </div>
      <div class="ai-characters-grid">
        ${characters.map((c, idx) => {
          return `
            <div class="char-dossier-card">
              <div class="char-dossier-header">
                <div>
                  <span class="char-avatar-badge">${c.gender === 'Female' ? '👩' : '👨'}</span>
                  <strong style="font-size:0.95rem; color:#FFF; margin-left:6px;">${c.name}</strong>
                </div>
                <span class="char-role-pill">${c.age} yo • ${c.gender}</span>
              </div>
              <div class="char-role-sub">${c.role}</div>

              <div class="char-traits-grid">
                <div class="char-trait-item"><strong>Complexion:</strong> ${c.complexion}</div>
                <div class="char-trait-item"><strong>Face Architecture:</strong> ${c.face_architecture}</div>
                <div class="char-trait-item"><strong>Eyes & Gaze:</strong> ${c.eyes}</div>
                <div class="char-trait-item"><strong>Hair & Parting:</strong> ${c.hair}</div>
                <div class="char-trait-item"><strong>Distinctive Marks:</strong> ${c.distinguishing_marks}</div>
                <div class="char-trait-item"><strong>Signature Attire:</strong> ${c.signature_wardrobe}</div>
                <div class="char-trait-item"><strong>Posture / Demeanor:</strong> ${c.resting_expression}</div>
              </div>

              <div class="char-anchor-box">
                <div class="char-anchor-title">🔒 Locked Prompt Anchor (Paste into every scene prompt):</div>
                <div class="char-anchor-code">${c.locked_prompt_anchor}</div>
                <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap;">
                  <button class="btn-copy-anchor" onclick="copyAnchorFromCard(this)">
                    📋 Copy Locked Anchor
                  </button>
                  <button class="btn-copy-turnaround" onclick="copyTurnaroundFromCard(this, ${idx})">
                    🖼️ Copy Turnaround Sheet Prompt
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // 4. Visual Plates Pane
  const platesPane = document.getElementById("ai-tab-pane-illustrations");
  if (platesPane) {
    platesPane.innerHTML = `
      <div class="ai-plate-grid">
        ${assets.map((a, i) => {
          return `
            <div class="ai-plate-card">
              <div class="ai-plate-header">
                <span>Slot #${i + 1} • Ch ${a.chapter}</span>
                <span>${a.placement}</span>
              </div>
              <div style="font-weight:700; color:#FFF; margin-bottom:4px;">${a.title}</div>
              <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                ${a.featured_character ? `<span class="badge-char">👤 ${a.featured_character}</span>` : ''}
                <span class="badge-res">📐 ${a.aspect_ratio || '2:3'} • ${a.target_resolution_px || '1875×2775'}</span>
              </div>
              <div class="ai-plate-prompt">"${a.prompt}"</div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; flex-wrap:wrap; gap:6px;">
                <span class="ai-plate-anchor">📍 Anchor: ${a.anchor}</span>
                <button class="btn-copy-prompt" style="padding:3px 8px; font-size:0.75rem;" onclick="copyPlatePromptFromCard(this, ${i})">
                  📋 Copy Prompt
                </button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }
}

function switchAITab(tabName) {
  const tabs = ["typo", "matter", "characters", "illustrations"];
  tabs.forEach(t => {
    const btn = document.getElementById(`ai-tab-btn-${t}`);
    const pane = document.getElementById(`ai-tab-pane-${t}`);
    if (btn) btn.classList.toggle("active", t === tabName);
    if (pane) pane.style.display = t === tabName ? "block" : "none";
  });
}

async function applyAIDirectorBlueprint() {
  if (!state.lastAIBlueprint) return;

  showToast("Applying AI Blueprint & typesetting manuscript...", "info");

  try {
    const res = await fetch(`/api/ai/apply/${state.activeBookId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ blueprint: state.lastAIBlueprint })
    });
    const data = await res.json();

    if (data.status === "success") {
      state.manifest = data.manifest;
      state.pagination = data.pagination;
      state.settings = data.settings;

      const plateCount = state.manifest?.assets?.length || (state.lastAIBlueprint?.assets || []).length;
      showToast(`🚀 AI Blueprint applied! Typography, ${plateCount} illustration slots & front matter locked.`, "success");
      renderAll();

      // Unlock Step 3
      state.maxUnlockedStep = Math.max(state.maxUnlockedStep, 3);
      updateStepperUI();
    } else {
      showToast(`Error applying blueprint: ${data.detail || 'Failed'}`, "error");
    }
  } catch (err) {
    showToast(`Failed to apply blueprint: ${err.message}`, "error");
  }
}

// Window Load Trigger
window.addEventListener("DOMContentLoaded", initStudio);
