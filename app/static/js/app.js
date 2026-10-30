/**
 * Argon Book Studio Pro - Master Typesetting & Publishing Frontend.
 * Powers:
 * 1. Live Geometry & Margin Inspector (trim, margins, fonts, leading, paper tint)
 * 2. Click-to-Edit Inline Manuscript Studio (in-spread editing, splitting, containers)
 * 3. Visual Pin-Dropper Callout Studio (click & drag pins directly on plates)
 * 4. Image Print Lab with Split Before/After comparison slider
 * 5. Bird's-Eye Thumbnail Filmstrip (instant spread navigation)
 * 6. Extended Front & Back Matter Customizer (dedications, epigraphs, bio)
 * 7. Multi-Format Export Sync (PDF, DOCX, EPUB, ZIP)
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
  activeEditingId: null,
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
    activePinIndex: null
  }
};

// API Helpers
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

// Studio Initialization
async function initStudio() {
  try {
    const profilesRes = await fetchAPI("/api/profiles");
    state.profiles = profilesRes.profiles;

    const booksRes = await fetchAPI("/api/books");
    state.books = booksRes.books;
    state.activeBookId = booksRes.active_book_id || "book01";

    await loadBook(state.activeBookId);
    setupHeaderListeners();
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
  state.currentSpreadIndex = 1;

  renderAll();
}

function renderAll() {
  renderHeader();
  renderLeftPanel();
  renderSpreadCanvas();
  renderFilmstrip();
  renderRightPanel();
}

// -------------------------------------------------------------
// 1. TOP HEADER
// -------------------------------------------------------------
function renderHeader() {
  const selector = document.getElementById("book-profile-select");
  if (selector) {
    selector.innerHTML = state.books.map(b => `
      <option value="${b.id}" ${b.id === state.activeBookId ? "selected" : ""}>
        ${b.short_title} (${b.genre.split("/")[0].trim()})
      </option>
    `).join("");
  }

  const indicator = document.getElementById("active-profile-indicator");
  if (indicator && state.activeBook && state.settings) {
    const s = state.settings;
    indicator.innerHTML = `
      <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${s.typography.accent_color};"></span>
      <span style="font-weight:600;">${state.activeBook.short_title}</span>
      <span style="color:var(--text-dim); font-size:0.75rem;">${s.trim_width_in}×${s.trim_height_in}" • ${s.typography.body_font_name} ${s.typography.body_font_size_pt}pt/${s.typography.body_leading_pt}pt</span>
    `;
  }
}

function setupHeaderListeners() {
  const profileSelect = document.getElementById("book-profile-select");
  if (profileSelect) {
    profileSelect.addEventListener("change", (e) => loadBook(e.target.value));
  }

  const uploadInput = document.getElementById("manuscript-file-input");
  if (uploadInput) {
    uploadInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("book_id", state.activeBookId);
      formData.append("file", file);

      showToast(`Parsing manuscript: ${file.name}...`, "info");
      const res = await fetch("/api/manuscript/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (data.status === "success") {
        showToast("Manuscript deconstructed into chapters & paragraphs!", "success");
        await loadBook(state.activeBookId);
      }
    });
  }
}

// -------------------------------------------------------------
// 2. LEFT PANEL (SLOTS & MANUSCRIPT TREE)
// -------------------------------------------------------------
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

      html += `
        <div class="asset-card" draggable="true" data-asset-id="${asset.id}" ondragstart="handleAssetDragStart(event, '${asset.id}')">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <span class="asset-badge ${badgeCls}">${asset.placement}</span>
            <span class="asset-anchor-chip" title="Anchored to Paragraph">⚓ ${asset.anchor}</span>
          </div>
          <div class="asset-title">${asset.title}</div>
          
          <div class="asset-thumbnail-row">
            <img src="${asset.image_url}" class="asset-thumb" alt="${asset.title}" onerror="this.src='/static/assets/placeholders/book01_vignette.png'">
            <div style="flex:1; font-size:0.72rem;">
              <div style="margin-bottom:6px; display:flex; gap:4px;">
                <button onclick="openVisualPinStudio('${asset.id}')" style="background:rgba(56,189,248,0.12); border:1px solid var(--accent-cyan); color:var(--accent-cyan); font-size:0.68rem; padding:3px 6px; border-radius:4px; cursor:pointer; font-weight:600;">
                  📍 Pins (${calloutCount})
                </button>
                <button onclick="openImageLabModal('${asset.id}')" style="background:rgba(217,119,6,0.12); border:1px solid var(--accent-gold); color:var(--accent-gold); font-size:0.68rem; padding:3px 6px; border-radius:4px; cursor:pointer; font-weight:600;">
                  🔬 Print Lab
                </button>
              </div>
              <div style="color:var(--text-dim);">300 DPI Texture Filter: <strong style="color:var(--accent-cyan);">${asset.filter_applied ? "Active" : "Standard"}</strong></div>
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
  let html = `<div style="font-size:0.73rem; color:var(--text-dim); margin-bottom:10px;">Drag an illustration card here to anchor it to any paragraph. Click paragraph to edit.</div>`;

  chapters.forEach(ch => {
    html += `
      <div class="manuscript-ch-header">
        Chapter ${ch.chapter_number}: ${ch.title}
      </div>
    `;

    (ch.elements || []).forEach(el => {
      const isAnchored = (state.manifest.assets || []).some(a => a.anchor === el.id);
      const textPreview = el.type === "paragraph"
        ? (el.text || "").substring(0, 65) + "..."
        : el.type === "container"
        ? `[${el.tag.toUpperCase()}: ${(el.content || '').substring(0, 40)}]`
        : "— Scene Break Divider —";

      html += `
        <div class="manuscript-p-row ${isAnchored ? 'drop-target' : ''}" 
             data-anchor-id="${el.id}"
             ondragover="handleDragOver(event)" 
             ondragleave="handleDragLeave(event)" 
             ondrop="handleDropAnchor(event, '${el.id}')"
             onclick="focusParagraphOnCanvas('${el.id}')">
          <span class="p-id-tag">${el.id}</span>
          <span style="flex:1;">${textPreview}</span>
          ${isAnchored ? '<span style="color:var(--accent-gold); font-size:0.8rem;">⚓</span>' : ''}
        </div>
      `;
    });
  });

  container.innerHTML = html;
}

function getPlacementBadgeClass(placement) {
  switch (placement) {
    case "Full-Page Recto Plate": return "badge-full-plate";
    case "Half-Page Top": return "badge-half-top";
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

// -------------------------------------------------------------
// 3. CENTER SPREAD CANVAS & INLINE EDITING
// -------------------------------------------------------------
function renderSpreadCanvas() {
  const viewport = document.getElementById("spread-viewport");
  const spreadIndicator = document.getElementById("spread-indicator");
  const prevBtn = document.getElementById("spread-prev-btn");
  const nextBtn = document.getElementById("spread-next-btn");
  const bannerContainer = document.getElementById("short-ending-banner-wrap");
  if (!viewport) return;

  const spreads = state.pagination.spreads || [];
  if (spreads.length === 0) {
    viewport.innerHTML = `<div style="color:var(--text-dim);">No pages to display.</div>`;
    return;
  }

  if (state.currentSpreadIndex < 0) state.currentSpreadIndex = 0;
  if (state.currentSpreadIndex >= spreads.length) state.currentSpreadIndex = spreads.length - 1;

  const currentSpread = spreads[state.currentSpreadIndex];

  if (spreadIndicator) {
    const versoPage = currentSpread.verso?.page_number;
    const rectoPage = currentSpread.recto?.page_number;
    const pageLabel = versoPage && rectoPage ? `Pages ${versoPage}–${rectoPage}` : rectoPage ? `Page ${rectoPage}` : `Page ${versoPage}`;
    spreadIndicator.innerText = `Spread ${state.currentSpreadIndex + 1} of ${spreads.length} (${pageLabel})`;
  }
  if (prevBtn) prevBtn.disabled = state.currentSpreadIndex === 0;
  if (nextBtn) nextBtn.disabled = state.currentSpreadIndex === spreads.length - 1;

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

  // Short Chapter Ending Detection Banner
  if (bannerContainer) {
    const hasShortVerso = currentSpread.verso?.short_ending && !currentSpread.verso?.has_tailpiece;
    const hasShortRecto = currentSpread.recto?.short_ending && !currentSpread.recto?.has_tailpiece;
    const shortPageNum = hasShortVerso ? currentSpread.verso.page_number : (hasShortRecto ? currentSpread.recto.page_number : null);

    if (shortPageNum) {
      bannerContainer.innerHTML = `
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
      bannerContainer.innerHTML = "";
    }
  }

  setupInlineEditListeners();
}

function renderSinglePageHTML(page, sideClass) {
  const profile = state.activeBook || state.profiles["book01"];
  const s = state.settings || { typography: {} };
  const isVerso = sideClass === "page-verso";

  const fontName = s.typography.body_font_name || profile.body_font_name;
  const displayFont = s.typography.display_font_name || profile.display_font_name;
  const accentColor = s.typography.accent_color || profile.accent_color;
  const paperTint = s.typography.paper_tint || profile.paper_tint;
  const fontSize = s.typography.body_font_size_pt || 11;
  const leading = s.typography.body_leading_pt || 15;
  const indent = s.typography.subsequent_p_indent_in || 0.25;
  const sinkage = s.typography.chapter_sinkage_in || 1.75;

  const runningHeader = !page.suppress_header ? (
    isVerso ? (s.typography.running_header_override || profile.short_title.toUpperCase()) : `CHAPTER ${page.chapter_number} • ${page.chapter_title.toUpperCase()}`
  ) : "";

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
      elementsHTML += `
        <div class="chapter-sinkage-box" style="height:${sinkage * 48}px;">
          <div class="ch-label">Chapter ${elem.chapter_number}</div>
          <h1 class="ch-title" style="font-family:${displayFont}; color:${accentColor};">${elem.title}</h1>
          <div class="ornament-wrap">${elem.ornament_svg}</div>
        </div>
      `;
    } else if (elem.type === "paragraph") {
      const isFirst = elem.is_first_after_break;
      const isDrop = isFirst && page.page_type === "chapter_opener";
      elementsHTML += `
        <p class="${isFirst ? 'indent-zero' : ''} ${isDrop ? 'has-dropcap' : ''}" 
           style="font-family:${fontName}; font-size:${fontSize}pt; line-height:${leading}pt; text-indent:${isFirst ? '0' : indent * 72 + 'px'};" 
           data-p-id="${elem.id}"
           contenteditable="true"
           title="Click to inline-edit text">
          ${elem.text}
        </p>
      `;
    } else if (elem.type === "container") {
      elementsHTML += `
        <div class="container-box ${elem.tag}" 
             data-p-id="${elem.id}"
             contenteditable="true"
             title="Click to inline-edit container content">
          ${elem.content.replace(/\n/g, "<br>")}
        </div>
      `;
    } else if (elem.type === "scene_break") {
      elementsHTML += `
        <div class="spread-scene-break">${elem.svg}</div>
      `;
    } else if (elem.type === "illustration") {
      const asset = elem.asset;
      const isFull = elem.placement === "Full-Page Recto Plate";
      elementsHTML += `
        <div class="spread-plate-wrapper ${isFull ? 'full-page' : ''}" 
             draggable="true" 
             ondragstart="handleAssetDragStart(event, '${asset.id}')">
          <img src="${asset.image_url}" alt="${asset.title}">
          <div class="spread-plate-caption">${asset.caption || asset.title}</div>
        </div>
      `;
    } else if (elem.type === "tailpiece_ornament") {
      elementsHTML += `
        <div class="spread-tailpiece">${elem.svg}</div>
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

  return `
    <div class="spread-page ${sideClass}" style="background-color:${paperTint};">
      ${state.showMargins ? '<div class="margin-guide-overlay"></div>' : ''}
      ${state.showBleed ? '<div class="bleed-guide-line"></div>' : ''}
      
      <div class="page-header-running" style="font-family:${fontName};">${runningHeader}</div>
      
      <div class="page-body-content">
        ${elementsHTML}
      </div>
      
      ${!page.suppress_footer ? `<div class="page-footer-running" style="font-family:${fontName};">${page.page_number}</div>` : ''}
    </div>
  `;
}

// Inline contenteditable listeners
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
      // Do not re-render entire spread on every keystroke to maintain cursor,
      // but update indicators and filmstrip
      renderFilmstrip();
    }
  } catch (err) {
    console.error("Save inline edit failed:", err);
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
  // Find which spread holds this element
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

// -------------------------------------------------------------
// 4. BIRD'S-EYE FILMSTRIP DOCK (BOTTOM)
// -------------------------------------------------------------
function renderFilmstrip() {
  const dock = document.getElementById("filmstrip-dock");
  if (!dock) return;

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

// -------------------------------------------------------------
// 5. RIGHT PANEL: GEOMETRY INSPECTOR, MATTER, EXPORT
// -------------------------------------------------------------
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
  const gutter = s.margins.inside_gutter_in || 0.875;
  const outside = s.margins.outside_margin_in || 0.625;
  const top = s.margins.top_margin_in || 0.75;
  const bottom = s.margins.bottom_margin_in || 0.875;
  const bodySize = s.typography.body_font_size_pt || 11;
  const leading = s.typography.body_leading_pt || 15;
  const indent = s.typography.subsequent_p_indent_in || 0.25;
  const sinkage = s.typography.chapter_sinkage_in || 1.75;
  const paperTint = s.typography.paper_tint || p.paper_tint;
  const headerText = s.typography.running_header_override || "";

  container.innerHTML = `
    <!-- Section 1: Trim Size -->
    <div class="section-block">
      <div class="section-title">
        <span>📐 Trim Geometry</span>
        <span class="slider-val-tag">${trimW}" × ${trimH}"</span>
      </div>
      <div class="trim-preset-grid">
        <button class="btn-trim-preset ${trimW === 6.0 && trimH === 9.0 ? 'active' : ''}" onclick="updateTrimPreset(6.0, 9.0)">6.0 × 9.0" Trade</button>
        <button class="btn-trim-preset ${trimW === 5.5 && trimH === 8.5 ? 'active' : ''}" onclick="updateTrimPreset(5.5, 8.5)">5.5 × 8.5" Digest</button>
        <button class="btn-trim-preset ${trimW === 5.0 && trimH === 8.0 ? 'active' : ''}" onclick="updateTrimPreset(5.0, 8.0)">5.0 × 8.0" Pocket</button>
        <button class="btn-trim-preset ${trimW === 7.0 && trimH === 10.0 ? 'active' : ''}" onclick="updateTrimPreset(7.0, 10.0)">7.0 × 10.0" Royal</button>
      </div>
    </div>

    <!-- Section 2: Mirrored Margins -->
    <div class="section-block">
      <div class="section-title">
        <span>◫ Mirrored Margins</span>
        <button onclick="resetMarginsToDefaults()" style="background:none; border:none; color:var(--accent-gold); font-size:0.68rem; cursor:pointer;">Reset</button>
      </div>
      
      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Inside Gutter (Spine Fold):</span>
          <span class="slider-val-tag" id="val-gutter">${gutter.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.375" step="0.025" value="${gutter}" oninput="handleGeometrySlider('inside_gutter_in', this.value, 'val-gutter')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Outside Margin:</span>
          <span class="slider-val-tag" id="val-outside">${outside.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.375" max="1.125" step="0.025" value="${outside}" oninput="handleGeometrySlider('outside_margin_in', this.value, 'val-outside')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Top Margin:</span>
          <span class="slider-val-tag" id="val-top">${top.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.25" step="0.025" value="${top}" oninput="handleGeometrySlider('top_margin_in', this.value, 'val-top')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Bottom Margin:</span>
          <span class="slider-val-tag" id="val-bottom">${bottom.toFixed(3)}"</span>
        </div>
        <input type="range" min="0.5" max="1.25" step="0.025" value="${bottom}" oninput="handleGeometrySlider('bottom_margin_in', this.value, 'val-bottom')">
      </div>
    </div>

    <!-- Section 3: Typography & Leading -->
    <div class="section-block">
      <div class="section-title">
        <span>🔤 Typography & Leading</span>
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Body Font Size:</span>
          <span class="slider-val-tag" id="val-font-size">${bodySize.toFixed(1)} pt</span>
        </div>
        <input type="range" min="9.0" max="13.5" step="0.25" value="${bodySize}" oninput="handleTypographySlider('body_font_size_pt', this.value, 'val-font-size')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Leading / Line Height:</span>
          <span class="slider-val-tag" id="val-leading">${leading.toFixed(1)} pt</span>
        </div>
        <input type="range" min="12.0" max="18.5" step="0.25" value="${leading}" oninput="handleTypographySlider('body_leading_pt', this.value, 'val-leading')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>First-Line Indent:</span>
          <span class="slider-val-tag" id="val-indent">${indent.toFixed(2)}"</span>
        </div>
        <input type="range" min="0.0" max="0.5" step="0.05" value="${indent}" oninput="handleTypographySlider('subsequent_p_indent_in', this.value, 'val-indent')">
      </div>

      <div class="inspector-slider-row">
        <div class="slider-label-wrap">
          <span>Chapter Top Sinkage:</span>
          <span class="slider-val-tag" id="val-sinkage">${sinkage.toFixed(2)}"</span>
        </div>
        <input type="range" min="1.0" max="2.75" step="0.125" value="${sinkage}" oninput="handleTypographySlider('chapter_sinkage_in', this.value, 'val-sinkage')">
      </div>
    </div>

    <!-- Section 4: Paper Tint & Running Header -->
    <div class="section-block">
      <div class="section-title">
        <span>📜 Paper & Running Headers</span>
      </div>

      <div style="margin-bottom:10px;">
        <label style="font-size:0.72rem; color:var(--text-muted);">Paper Tone:</label>
        <div style="display:flex; gap:6px; margin-top:4px;">
          <button onclick="updatePaperTint('#FBF8F1')" style="flex:1; height:24px; background:#FBF8F1; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Antique Cream"></button>
          <button onclick="updatePaperTint('#FAF6EE')" style="flex:1; height:24px; background:#FAF6EE; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Ochre Vellum"></button>
          <button onclick="updatePaperTint('#F5F6F8')" style="flex:1; height:24px; background:#F5F6F8; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Slate Crisp"></button>
          <button onclick="updatePaperTint('#FFFFFF')" style="flex:1; height:24px; background:#FFFFFF; border:1px solid #CCC; border-radius:3px; cursor:pointer;" title="Pure White"></button>
        </div>
      </div>

      <div>
        <label style="font-size:0.72rem; color:var(--text-muted);">Custom Verso Header Text:</label>
        <input type="text" value="${headerText}" placeholder="${p.short_title.toUpperCase()}" onchange="handleHeaderOverride(this.value)" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:5px; border-radius:4px; margin-top:3px;">
      </div>
    </div>
  `;
}

function renderFrontMatterTab(container) {
  const fm = state.settings?.front_back_matter || {};

  container.innerHTML = `
    <div class="section-block">
      <div class="section-title">
        <span>📖 Front & Back Matter</span>
        <button onclick="saveMatterSettings()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:3px 8px; border-radius:4px; font-size:0.68rem; cursor:pointer;">Save</button>
      </div>

      <div style="display:flex; flex-direction:column; gap:10px; font-size:0.75rem; color:var(--text-muted);">
        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-half-title" ${fm.include_half_title !== false ? 'checked' : ''}> Half-Title Page
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-frontispiece" ${fm.include_frontispiece !== false ? 'checked' : ''}> Frontispiece Ornament Plate
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-title-page" ${fm.include_title_page !== false ? 'checked' : ''}> Full Title Page (Imprint)
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-copyright" ${fm.include_copyright !== false ? 'checked' : ''}> Copyright & ISBN Page
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-dedication" ${fm.include_dedication ? 'checked' : ''}> Dedication Page
        </label>
        <input type="text" id="fm-dedication-text" value="${fm.dedication_text || ''}" placeholder="Dedication text..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-epigraph" ${fm.include_epigraph ? 'checked' : ''}> Epigraph Page
        </label>
        <input type="text" id="fm-epigraph-text" value="${fm.epigraph_text || ''}" placeholder="Epigraph quote..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px; margin-bottom:4px;">
        <input type="text" id="fm-epigraph-source" value="${fm.epigraph_source || ''}" placeholder="Source attribution..." style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem; padding:4px; border-radius:3px;">

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-toc" ${fm.include_toc !== false ? 'checked' : ''}> Auto-Calculated Contents (TOC)
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-acknowledgements" ${fm.include_acknowledgements ? 'checked' : ''}> Acknowledgements
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-about-author" ${fm.include_about_author ? 'checked' : ''}> About the Author
        </label>

        <label style="display:flex; align-items:center; gap:6px;">
          <input type="checkbox" id="fm-colophon" ${fm.include_colophon !== false ? 'checked' : ''}> Typesetting Colophon
        </label>
      </div>
    </div>
  `;
}

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
        <strong>Active Specifications:</strong><br>
        • Trim: ${s.trim_width_in || 6.0}" × ${s.trim_height_in || 9.0}"<br>
        • Margins: Inside Gutter ${s.margins.inside_gutter_in || 0.875}", Outside ${s.margins.outside_margin_in || 0.625}"<br>
        • Typography: ${s.typography.body_font_name || 'EB Garamond'} (${s.typography.body_font_size_pt || 11}pt / ${s.typography.body_leading_pt || 15}pt)<br>
        • All exports automatically synced with live inspector!
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

// -------------------------------------------------------------
// 6. LIVE GEOMETRY UPDATE DISPATCHERS (DEBOUNCED)
// -------------------------------------------------------------
let geomDebounce = null;

function handleGeometrySlider(field, val, labelId) {
  document.getElementById(labelId).innerText = parseFloat(val).toFixed(3) + '"';
  clearTimeout(geomDebounce);
  geomDebounce = setTimeout(async () => {
    const updates = { margins: {} };
    updates.margins[field] = parseFloat(val);
    await dispatchSettingsUpdate(updates);
  }, 300);
}

function handleTypographySlider(field, val, labelId) {
  const isPt = field.includes("_pt");
  document.getElementById(labelId).innerText = parseFloat(val).toFixed(isPt ? 1 : 2) + (isPt ? " pt" : '"');
  clearTimeout(geomDebounce);
  geomDebounce = setTimeout(async () => {
    const updates = { typography: {} };
    updates.typography[field] = parseFloat(val);
    await dispatchSettingsUpdate(updates);
  }, 300);
}

function updateTrimPreset(w, h) {
  dispatchSettingsUpdate({ trim_width_in: w, trim_height_in: h });
}

function updatePaperTint(hex) {
  dispatchSettingsUpdate({ typography: { paper_tint: hex } });
}

function handleHeaderOverride(txt) {
  dispatchSettingsUpdate({ typography: { running_header_override: txt } });
}

async function resetMarginsToDefaults() {
  await dispatchSettingsUpdate({
    margins: {
      inside_gutter_in: 0.875,
      outside_margin_in: 0.625,
      top_margin_in: 0.75,
      bottom_margin_in: 0.875
    }
  });
}

async function saveMatterSettings() {
  const updates = {
    front_back_matter: {
      include_half_title: document.getElementById("fm-half-title").checked,
      include_frontispiece: document.getElementById("fm-frontispiece").checked,
      include_title_page: document.getElementById("fm-title-page").checked,
      include_copyright: document.getElementById("fm-copyright").checked,
      include_dedication: document.getElementById("fm-dedication").checked,
      dedication_text: document.getElementById("fm-dedication-text").value,
      include_epigraph: document.getElementById("fm-epigraph").checked,
      epigraph_text: document.getElementById("fm-epigraph-text").value,
      epigraph_source: document.getElementById("fm-epigraph-source").value,
      include_toc: document.getElementById("fm-toc").checked,
      include_acknowledgements: document.getElementById("fm-acknowledgements").checked,
      include_about_author: document.getElementById("fm-about-author").checked,
      include_colophon: document.getElementById("fm-colophon").checked,
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

// -------------------------------------------------------------
// 7. VISUAL PIN-DROPPER CALLOUT STUDIO
// -------------------------------------------------------------
function openVisualPinStudio(assetId) {
  const asset = state.manifest.assets.find(a => a.id === assetId);
  if (!asset) return;

  state.pinStudioState.assetId = assetId;
  state.pinStudioState.callouts = JSON.parse(JSON.stringify(asset.vector_callouts || []));
  state.pinStudioState.activePinIndex = null;

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
      <div class="modal-content" style="width:780px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:0.95rem; color:var(--accent-cyan);">
            📍 Visual Callout Studio — Click Canvas to Drop Pins
          </h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body" style="padding:14px; display:flex; flex-direction:column; gap:12px;">
          <div style="font-size:0.75rem; color:var(--text-muted);">
            Click anywhere on the plate to place a precision vector callout pin. Drag pins to reposition.
          </div>

          <!-- Interactive Pin Canvas -->
          <div style="text-align:center; background:#000; padding:10px; border-radius:6px; overflow:hidden;">
            <div id="pin-canvas-wrap" class="pin-canvas-container" onclick="handlePinCanvasClick(event)">
              <img id="pin-target-img" src="${asset.image_url}" style="max-height:360px; max-width:100%; display:block;" alt="${asset.title}">
              
              <!-- Render pins -->
              ${callouts.map((c, i) => `
                <div class="pin-marker" 
                     style="left:${c.x}%; top:${c.y}%;" 
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

        <div class="modal-footer">
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
    return `<div style="color:var(--text-dim); text-align:center;">Click anywhere on the image above to add a pin, or click an existing pin number to edit.</div>`;
  }

  const pin = callouts[idx];
  return `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <strong style="color:var(--accent-cyan);">Editing Pin #${idx + 1}</strong>
      <button onclick="deletePin(${idx})" style="background:#EF4444; color:#FFF; border:none; padding:2px 8px; border-radius:3px; cursor:pointer; font-size:0.7rem;">Delete Pin</button>
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
          <option value="arrow_up" ${pin.type === 'arrow_up' ? 'selected' : ''}>Arrow Up</option>
          <option value="arrow_down" ${pin.type === 'arrow_down' ? 'selected' : ''}>Arrow Down</option>
          <option value="arrow_left" ${pin.type === 'arrow_left' ? 'selected' : ''}>Arrow Left</option>
        </select>
      </div>
      <div>
        <label style="color:var(--text-muted); font-size:0.7rem;">Coordinates</label>
        <div style="padding:5px; color:var(--accent-gold); font-family:monospace; font-size:0.72rem;">X:${pin.x.toFixed(1)}% Y:${pin.y.toFixed(1)}%</div>
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
    // Update label preview live without re-rendering whole modal
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

  showToast("Rendering precision vector callout overlay...", "info");
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

// -------------------------------------------------------------
// 8. IMAGE PRINT LAB (SPLIT BEFORE/AFTER COMPARISON)
// -------------------------------------------------------------
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

        <div class="modal-footer">
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

// -------------------------------------------------------------
// 9. EXPORTS & TAILPIECE BALANCING
// -------------------------------------------------------------
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

async function exportDocument(format) {
  const bleed = state.showBleed;
  showToast(`Compiling ${format.toUpperCase()} with live geometry & publishing rules...`, "info");

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

// -------------------------------------------------------------
// 10. DRAG-AND-DROP RE-ANCHORING & FILE UPLOADS
// -------------------------------------------------------------
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
  const asset = state.manifest.assets.find(a => a.id === assetId);
  if (!asset || !asset.prompt) return;

  navigator.clipboard.writeText(asset.prompt).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = "✓ Copied!";
    btn.style.color = "#10B981";
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.color = "var(--accent-cyan)";
    }, 2000);
  });
}

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

// Window Load Trigger
window.addEventListener("DOMContentLoaded", initStudio);
