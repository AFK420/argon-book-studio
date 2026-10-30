/**
 * Argon Book Studio - Interactive Publishing Engine Frontend.
 * Powers the 3-panel visual workspace, live 2-page spread preview,
 * drag-and-drop anchor repositioning, vector callouts, Pillow filters,
 * and one-click multi-format exports.
 */

const state = {
  profiles: {},
  books: [],
  activeBookId: "book01",
  activeBook: null,
  manuscript: null,
  manifest: { assets: [] },
  pagination: { spreads: [], pages: [], short_endings: [] },
  currentSpreadIndex: 1, // 0-based index into pagination.spreads
  showMargins: true,
  showBleed: false,
  zoomLevel: 1.0,
  activeTab: "manifest", // 'manifest' or 'tree'
  selectedAsset: null,
  modalOpen: null, // 'addSlot', 'editCallouts', 'frontMatter'
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

// Toast notification system
function showToast(message, type = "info") {
  let toastContainer = document.getElementById("toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.style.cssText =
      "position: fixed; top: 18px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px;";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  const bg =
    type === "error" ? "#EF4444" : type === "success" ? "#10B981" : "#1E293B";
  const border =
    type === "error" ? "#B91C1C" : type === "success" ? "#059669" : "#3B82F6";
  toast.style.cssText = `background: ${bg}; color: #FFF; border-left: 4px solid ${border}; padding: 10px 16px; border-radius: 6px; font-size: 0.85rem; box-shadow: 0 4px 15px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 8px; transition: all 0.3s ease;`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ"}</span> <span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Initialization
async function initStudio() {
  try {
    const profilesRes = await fetchAPI("/api/profiles");
    state.profiles = profilesRes.profiles;

    const booksRes = await fetchAPI("/api/books");
    state.books = booksRes.books;
    state.activeBookId = booksRes.active_book_id || "book01";

    await loadBook(state.activeBookId);
    setupEventListeners();
  } catch (err) {
    console.error("Initialization error:", err);
  }
}

// Load Book Data
async function loadBook(bookId) {
  state.activeBookId = bookId;
  const data = await fetchAPI(`/api/book/${bookId}`);
  state.activeBook = data.profile;
  state.manuscript = data.manuscript;
  state.manifest = data.manifest;
  state.pagination = data.pagination;
  state.frontMatter = data.front_matter;
  state.currentSpreadIndex = 1; // Default to first actual spread (Pages 2-3) or 0 (Page 1)

  renderAll();
}

// Master Render Function
function renderAll() {
  renderHeader();
  renderLeftPanel();
  renderSpreadCanvas();
  renderRightPanel();
}

// Render Top Header
function renderHeader() {
  const selector = document.getElementById("book-profile-select");
  if (selector) {
    selector.innerHTML = state.books
      .map(
        (b) =>
          `<option value="${b.id}" ${b.id === state.activeBookId ? "selected" : ""}>
        ${b.short_title} (${b.genre.split("/")[0].trim()})
      </option>`
      )
      .join("");
  }

  const indicator = document.getElementById("active-profile-indicator");
  if (indicator && state.activeBook) {
    indicator.innerHTML = `
      <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${state.activeBook.accent_color};"></span>
      <span style="font-weight:600;">${state.activeBook.short_title}</span>
      <span style="color:var(--text-dim); font-size:0.75rem;">6x9" • ${state.activeBook.body_font_name}</span>
    `;
  }
}

// Render Left Panel (Manuscript & Anchor Tree)
function renderLeftPanel() {
  const tabManifestBtn = document.getElementById("tab-manifest-btn");
  const tabTreeBtn = document.getElementById("tab-tree-btn");
  const contentArea = document.getElementById("left-panel-content");
  if (!contentArea) return;

  if (tabManifestBtn && tabTreeBtn) {
    tabManifestBtn.classList.toggle("active", state.activeTab === "manifest");
    tabTreeBtn.classList.toggle("active", state.activeTab === "tree");
  }

  if (state.activeTab === "manifest") {
    renderManifestTab(contentArea);
  } else {
    renderTreeTab(contentArea);
  }
}

function renderManifestTab(container) {
  const assets = state.manifest.assets || [];
  let html = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">${assets.length} PLANNED ILLUSTRATION SLOTS</span>
      <button onclick="openAddSlotModal()" style="background:var(--accent-gold); color:#000; border:none; padding:4px 8px; border-radius:4px; font-size:0.72rem; font-weight:700; cursor:pointer;">
        + Add Slot
      </button>
    </div>
  `;

  if (assets.length === 0) {
    html += `<div style="text-align:center; padding:30px 10px; color:var(--text-dim); font-size:0.85rem;">No illustration slots planned yet. Click "+ Add Slot" or drop an image.</div>`;
  } else {
    assets.forEach((asset) => {
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
            <div style="flex:1; font-size:0.75rem;">
              <div style="color:var(--text-dim); margin-bottom:4px;">Filter: <strong style="color:var(--accent-cyan);">${asset.filter_applied ? "300 DPI Texture Applied" : "Pending"}</strong></div>
              <button onclick="openCalloutModal('${asset.id}')" style="background:rgba(255,255,255,0.08); border:1px solid var(--border-subtle); color:var(--text-main); font-size:0.7rem; padding:3px 8px; border-radius:4px; cursor:pointer;">
                ✎ Vector Callouts (${calloutCount})
              </button>
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

          <!-- File Drop Zone for custom illustration -->
          <div class="drop-zone" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDropImage(event, '${asset.id}')" onclick="triggerFileInput('${asset.id}')">
            📁 Drop Image Here or Click to Upload (Auto 300 DPI + Filter)
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
  let html = `<div style="font-size:0.75rem; color:var(--text-dim); margin-bottom:10px;">Drag an illustration card here to anchor it to any paragraph.</div>`;

  chapters.forEach((ch) => {
    html += `
      <div class="manuscript-ch-header">
        Chapter ${ch.chapter_number}: ${ch.title}
      </div>
    `;

    (ch.elements || []).forEach((el) => {
      const isAnchored = (state.manifest.assets || []).some(
        (a) => a.anchor === el.id
      );
      const textPreview =
        el.type === "paragraph"
          ? (el.text || "").substring(0, 68) + "..."
          : el.type === "container"
            ? `[Container: ${el.tag}]`
            : "— Scene Break —";

      html += `
        <div class="manuscript-p-row ${isAnchored ? "drop-target" : ""}" 
             data-anchor-id="${el.id}"
             ondragover="handleDragOver(event)" 
             ondragleave="handleDragLeave(event)" 
             ondrop="handleDropAnchor(event, '${el.id}')">
          <span class="p-id-tag">${el.id}</span>
          <span style="flex:1;">${textPreview}</span>
          ${isAnchored ? '<span style="color:var(--accent-gold); font-size:0.8rem;">⚓</span>' : ""}
        </div>
      `;
    });
  });

  container.innerHTML = html;
}

function getPlacementBadgeClass(placement) {
  switch (placement) {
    case "Full-Page Recto Plate":
      return "badge-full-plate";
    case "Half-Page Top":
      return "badge-half-top";
    case "Inline Archival Insert":
      return "badge-inline";
    case "Chapter Opener Vignette":
      return "badge-opener";
    case "Chapter End Tailpiece":
      return "badge-tailpiece";
    default:
      return "badge-inline";
  }
}

// Center Panel: Live 2-Page Spread Preview
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

  // Bound index
  if (state.currentSpreadIndex < 0) state.currentSpreadIndex = 0;
  if (state.currentSpreadIndex >= spreads.length)
    state.currentSpreadIndex = spreads.length - 1;

  const currentSpread = spreads[state.currentSpreadIndex];

  // Update nav bar
  if (spreadIndicator) {
    const versoPage = currentSpread.verso?.page_number;
    const rectoPage = currentSpread.recto?.page_number;
    const pageLabel =
      versoPage && rectoPage
        ? `Pages ${versoPage}–${rectoPage}`
        : rectoPage
          ? `Page ${rectoPage}`
          : `Page ${versoPage}`;
    spreadIndicator.innerText = `Spread ${state.currentSpreadIndex + 1} of ${spreads.length} (${pageLabel})`;
  }
  if (prevBtn) prevBtn.disabled = state.currentSpreadIndex === 0;
  if (nextBtn) nextBtn.disabled = state.currentSpreadIndex === spreads.length - 1;

  // Build 2-Page Spread HTML
  let spreadHTML = `
    <div class="book-spread-container" style="transform: scale(${state.zoomLevel});">
  `;

  // VERSO (LEFT) PAGE
  if (currentSpread.verso) {
    spreadHTML += renderSinglePageHTML(currentSpread.verso, "page-verso");
  } else {
    // Empty left placeholder for Page 1 recto opening
    spreadHTML += `
      <div class="spread-page empty-placeholder" style="border-right:1px solid #222;">
        <span style="font-size:0.75rem; letter-spacing:0.1em;">[FRONT COVER REVERSE / VERSO BLANK]</span>
      </div>
    `;
  }

  // RECTO (RIGHT) PAGE
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
    const hasShortVerso =
      currentSpread.verso?.short_ending && !currentSpread.verso?.has_tailpiece;
    const hasShortRecto =
      currentSpread.recto?.short_ending && !currentSpread.recto?.has_tailpiece;
    const shortPageNum = hasShortVerso
      ? currentSpread.verso.page_number
      : hasShortRecto
        ? currentSpread.recto.page_number
        : null;

    if (shortPageNum) {
      bannerContainer.innerHTML = `
        <div class="short-ending-banner">
          <div style="font-size:1.1rem;">⚠️</div>
          <div>
            <div style="font-size:0.82rem; font-weight:700; color:#FDE68A;">Short Chapter Ending Detected (Page ${shortPageNum})</div>
            <div style="font-size:0.72rem; color:#E0E7FF;">Page content is &lt; 18 lines. Whitespace is unbalanced.</div>
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
}

// Render individual page contents with exact CSS & typography
function renderSinglePageHTML(page, sideClass) {
  const profile = state.activeBook || state.profiles["book01"];
  const isVerso = sideClass === "page-verso";

  // Running header calculation
  const runningHeader = !page.suppress_header
    ? isVerso
      ? profile.short_title.toUpperCase()
      : `CHAPTER ${page.chapter_number} • ${page.chapter_title.toUpperCase()}`
    : "";

  let elementsHTML = "";

  (page.elements || []).forEach((elem) => {
    if (elem.type === "half_title") {
      elementsHTML += `
        <div style="text-align:center; margin-top:140px;">
          <h2 style="font-family:${profile.display_font}; font-size:14pt; letter-spacing:0.14em; text-transform:uppercase;">${elem.title}</h2>
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
        <div style="text-align:center; margin-top:80px;">
          <h1 style="font-family:${profile.display_font}; font-size:16pt; margin-bottom:6px; color:${profile.accent_color};">${elem.title}</h1>
          <div style="font-style:italic; font-size:8.5pt; margin-bottom:24px;">${elem.subtitle}</div>
          <div style="margin-bottom:24px;">${profile.scene_break_svg}</div>
          <div style="font-family:${profile.display_font}; font-size:9.5pt; font-weight:700; letter-spacing:0.1em; text-transform:uppercase;">${elem.author}</div>
          <div style="margin-top:110px; font-size:6.8pt; letter-spacing:0.16em; color:#888;">${elem.imprint}</div>
        </div>
      `;
    } else if (elem.type === "copyright_page") {
      elementsHTML += `
        <div style="margin-top:280px; font-size:6.5pt; line-height:9.5pt; color:#666;">
          <strong>${elem.title}</strong><br>
          Copyright © ${elem.year} by ${elem.author}<br>
          All rights reserved. First 6x9" Illustrated Collector's Edition.<br>
          Published by The Argon Book Studio Press.<br>
          ISBN ${elem.isbn}<br><br>
          ${elem.colophon_summary}
        </div>
      `;
    } else if (elem.type === "table_of_contents") {
      elementsHTML += `
        <div style="margin-top:70px;">
          <h2 style="font-family:${profile.display_font}; font-size:11pt; letter-spacing:0.16em; text-align:center; text-transform:uppercase; margin-bottom:18px;">Contents</h2>
          ${(elem.chapters || [])
            .map(
              (ch) => `
            <div style="display:flex; justify-content:space-between; font-size:8.5pt; margin-bottom:8px; border-bottom:1px dotted #ccc; padding-bottom:2px;">
              <span>Chapter ${ch.number} — ${ch.title}</span>
            </div>
          `
            )
            .join("")}
        </div>
      `;
    } else if (elem.type === "chapter_header") {
      elementsHTML += `
        <div class="chapter-sinkage-box">
          <div class="ch-label">Chapter ${elem.chapter_number}</div>
          <h1 class="ch-title" style="font-family:${profile.display_font}; color:${profile.accent_color};">${elem.title}</h1>
          <div class="ornament-wrap">${elem.ornament_svg}</div>
        </div>
      `;
    } else if (elem.type === "paragraph") {
      const isFirst = elem.is_first_after_break;
      const isDrop = isFirst && page.page_type === "chapter_opener";
      elementsHTML += `
        <p class="${isFirst ? "indent-zero" : ""} ${isDrop ? "has-dropcap" : ""}" 
           style="font-family:${profile.body_font};" 
           data-p-id="${elem.id}">
          ${elem.text}
        </p>
      `;
    } else if (elem.type === "container") {
      elementsHTML += `
        <div class="container-box ${elem.tag}">
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
        <div class="spread-plate-wrapper ${isFull ? "full-page" : ""}" 
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
    } else if (elem.type === "colophon") {
      elementsHTML += `
        <div style="text-align:center; margin-top:160px; font-size:7.5pt; line-height:11pt; color:#555;">
          <h3 style="font-family:${profile.display_font}; font-size:9pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:10px; color:${profile.accent_color};">Colophon</h3>
          <p class="indent-zero" style="text-align:center;">
            This volume was designed and typeset in 6x9 inch format using the Argon Universal Publishing Engine.<br>
            Body text set in ${elem.body_font}. Display headers set in ${elem.display_font}.<br>
            ${elem.specs}
          </p>
          <div style="margin-top:20px;">${profile.tailpiece_svg}</div>
        </div>
      `;
    }
  });

  return `
    <div class="spread-page ${sideClass}" style="background-color:${profile.paper_tint};">
      ${state.showMargins ? '<div class="margin-guide-overlay"></div>' : ""}
      ${state.showBleed ? '<div class="bleed-guide-line"></div>' : ""}
      
      <!-- Running Header -->
      <div class="page-header-running" style="font-family:${profile.body_font};">${runningHeader}</div>
      
      <!-- Content -->
      <div class="page-body-content">
        ${elementsHTML}
      </div>
      
      <!-- Running Footer / Page Number -->
      ${!page.suppress_footer ? `<div class="page-footer-running" style="font-family:${profile.body_font};">${page.page_number}</div>` : ""}
    </div>
  `;
}

// Right Panel: Post-Processing & One-Click Export Suite
function renderRightPanel() {
  const container = document.getElementById("right-panel-content");
  if (!container) return;

  const profile = state.activeBook || state.profiles["book01"];

  container.innerHTML = `
    <!-- Section 1: Book Theme Profile Specs -->
    <div class="section-block">
      <div class="section-title">
        <span>🎨 Book Theme Profile</span>
        <span style="font-size:0.68rem; color:var(--accent-gold);">${profile.id.toUpperCase()}</span>
      </div>
      <div style="font-size:0.8rem; margin-bottom:8px;">
        <strong>${profile.title}</strong>
      </div>
      <div style="font-size:0.75rem; color:var(--text-muted); line-height:1.4;">
        <div>• <strong>Body Font:</strong> ${profile.body_font_name} (${profile.body_font_size} / ${profile.body_leading})</div>
        <div>• <strong>Display Font:</strong> ${profile.display_font_name}</div>
        <div>• <strong>Custom Containers:</strong> ${(profile.containers || []).map((c) => `.${c.tag}`).join(", ")}</div>
      </div>
      <div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--border-subtle); display:flex; gap:6px;">
        <span style="font-size:0.68rem; background:${profile.accent_color}; color:#FFF; padding:2px 6px; border-radius:3px;">${profile.accent_color}</span>
        <span style="font-size:0.68rem; background:${profile.brass_accent}; color:#000; padding:2px 6px; border-radius:3px; font-weight:700;">${profile.brass_accent}</span>
      </div>
    </div>

    <!-- Section 2: Image Print Texture Filter Studio -->
    <div class="section-block">
      <div class="section-title">
        <span>📷 Print Texture Studio</span>
        <span style="font-size:0.68rem; color:var(--accent-cyan);">300 DPI</span>
      </div>
      <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:8px;">
        ${profile.filter_description}
      </div>
      <div style="margin-bottom:10px;">
        <label style="font-size:0.72rem; color:var(--text-dim); text-transform:uppercase;">Medium Preset:</label>
        <select id="filter-preset-select" onchange="handleFilterPresetChange(this.value)" style="width:100%; background:var(--bg-main); border:1px solid var(--border-subtle); color:var(--text-main); font-size:0.78rem; padding:6px; border-radius:4px; margin-top:3px;">
          <option value="cyanotype_silver_plate" ${profile.filter_preset === "cyanotype_silver_plate" ? "selected" : ""}>Cyanotype / 19th-C Silver Plate</option>
          <option value="charcoal_lithograph" ${profile.filter_preset === "charcoal_lithograph" ? "selected" : ""}>Charcoal & Hebridean Lithograph</option>
          <option value="blueprint_halftone" ${profile.filter_preset === "blueprint_halftone" ? "selected" : ""}>Blueprint Halftone & Oscilloscope</option>
          <option value="sepia_bioluminescent_amber" ${profile.filter_preset === "sepia_bioluminescent_amber" ? "selected" : ""}>1928 Sepia & Bioluminescent Amber</option>
          <option value="desert_ochre_uv" ${profile.filter_preset === "desert_ochre_uv" ? "selected" : ""}>Desert Ochre & UV Fluorescence</option>
        </select>
      </div>
      <button onclick="reapplyFilterToAll()" style="width:100%; background:rgba(56,189,248,0.15); border:1px solid var(--accent-cyan); color:var(--accent-cyan); font-weight:700; font-size:0.75rem; padding:8px; border-radius:4px; cursor:pointer;">
        ⚡ Re-Apply Filter & Resample (300 DPI)
      </button>
    </div>

    <!-- Section 3: Front & Back Matter Generator -->
    <div class="section-block">
      <div class="section-title">
        <span>📖 Front & Back Matter</span>
        <button onclick="openFrontMatterModal()" style="background:none; border:none; color:var(--accent-gold); font-size:0.72rem; cursor:pointer; font-weight:700;">
          Preview
        </button>
      </div>
      <div style="font-size:0.75rem; color:var(--text-muted); display:flex; flex-direction:column; gap:6px;">
        <label><input type="checkbox" checked disabled> Half-Title Page</label>
        <label><input type="checkbox" checked disabled> Thematic Frontispiece</label>
        <label><input type="checkbox" checked disabled> Full Title Page (Imprint)</label>
        <label><input type="checkbox" checked disabled> Copyright & Library Cataloging</label>
        <label><input type="checkbox" checked disabled> Table of Contents (Auto-Calculated)</label>
        <label><input type="checkbox" checked disabled> Back Colophon & Production Notes</label>
      </div>
    </div>

    <!-- Section 4: One-Click Export Suite -->
    <div class="section-block" style="border-color:var(--accent-gold);">
      <div class="section-title">
        <span>🚀 One-Click Export Suite</span>
        <label style="font-size:0.68rem; display:flex; align-items:center; gap:4px; text-transform:none; color:var(--text-main); cursor:pointer;">
          <input type="checkbox" id="export-bleed-toggle" ${state.showBleed ? "checked" : ""} onchange="state.showBleed = this.checked; renderSpreadCanvas();">
          +0.125" Bleed
        </label>
      </div>

      <button class="btn-export" onclick="exportDocument('pdf')">
        <span>📄 Print-Ready 6x9" PDF</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">WeasyPrint/Edge</span>
      </button>

      <button class="btn-export" onclick="exportDocument('docx')">
        <span>📝 Styled Editable DOCX</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">python-docx</span>
      </button>

      <button class="btn-export" onclick="exportDocument('epub')">
        <span>📱 Reflowable EPUB 3</span>
        <span style="font-size:0.7rem; color:var(--text-dim);">ebooklib</span>
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

// Event Listeners & Drag-and-Drop
function setupEventListeners() {
  // Book profile selector
  const profileSelect = document.getElementById("book-profile-select");
  if (profileSelect) {
    profileSelect.addEventListener("change", (e) => loadBook(e.target.value));
  }

  // Manuscript file upload button
  const uploadInput = document.getElementById("manuscript-file-input");
  if (uploadInput) {
    uploadInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("book_id", state.activeBookId);
      formData.append("file", file);

      showToast(`Parsing ${file.name}...`, "info");
      const res = await fetch("/api/manuscript/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast("Manuscript parsed into chapters & paragraphs!", "success");
        await loadBook(state.activeBookId);
      }
    });
  }
}

// Drag & Drop Handlers
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

// Drop slot onto paragraph anchor
async function handleDropAnchor(event, targetAnchor) {
  event.preventDefault();
  event.currentTarget.classList.remove("dragover");

  const assetId = event.dataTransfer.getData("text/plain");
  if (!assetId) return;

  showToast(`Moving ${assetId} to anchor ${targetAnchor}...`, "info");
  const res = await fetchAPI(
    `/api/manifest/${state.activeBookId}/update-anchor`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_id: assetId, new_anchor: targetAnchor }),
    }
  );

  if (res.status === "success") {
    showToast(
      `Slot anchored to ${targetAnchor}! Pagination updated.`,
      "success"
    );
    state.pagination = res.pagination;
    // Update local manifest
    const asset = state.manifest.assets.find((a) => a.id === assetId);
    if (asset) asset.anchor = targetAnchor;
    renderAll();
  }
}

// Drop local image onto slot
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

  showToast(
    `Uploading & processing ${file.name} (Pillow 300 DPI filter)...`,
    "info"
  );
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(
    `/api/assets/upload/${state.activeBookId}/${assetId}`,
    {
      method: "POST",
      body: formData,
    }
  );
  const data = await res.json();
  if (data.status === "success") {
    showToast("Print texture filter applied at 300 DPI!", "success");
    state.pagination = data.pagination;
    const asset = state.manifest.assets.find((a) => a.id === assetId);
    if (asset) {
      asset.image_url = data.image_url;
      asset.filter_applied = true;
    }
    renderAll();
  }
}

// Copy prompt helper
function copyPrompt(assetId, btn) {
  const asset = state.manifest.assets.find((a) => a.id === assetId);
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

// Auto-Insert Tailpiece Ornament
async function autoInsertTailpiece(pageNumber) {
  showToast(
    `Inserting thematic tailpiece ornament on page ${pageNumber}...`,
    "info"
  );
  const res = await fetchAPI("/api/tailpiece/auto-insert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: state.activeBookId,
      page_number: pageNumber,
      enable: true,
    }),
  });

  if (res.status === "success") {
    showToast(
      "Whitespace balanced with authentic tailpiece ornament!",
      "success"
    );
    state.pagination = res.pagination;
    renderSpreadCanvas();
  }
}

// Spread Navigator Actions
function nextSpread() {
  if (state.currentSpreadIndex < state.pagination.spreads.length - 1) {
    state.currentSpreadIndex++;
    renderSpreadCanvas();
  }
}

function prevSpread() {
  if (state.currentSpreadIndex > 0) {
    state.currentSpreadIndex--;
    renderSpreadCanvas();
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

function switchTab(tabName) {
  state.activeTab = tabName;
  renderLeftPanel();
}

// Filter Preset Switcher
async function handleFilterPresetChange(preset) {
  showToast(`Switching image filter medium to: ${preset}...`, "info");
  for (const asset of state.manifest.assets) {
    await fetchAPI(
      `/api/assets/apply-filter/${state.activeBookId}/${asset.id}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filter_preset: preset }),
      }
    );
  }
  showToast("All illustrations resampled with new medium filter!", "success");
  await loadBook(state.activeBookId);
}

async function reapplyFilterToAll() {
  const sel = document.getElementById("filter-preset-select");
  const preset = sel ? sel.value : state.activeBook.filter_preset;
  await handleFilterPresetChange(preset);
}

// Export Documents
async function exportDocument(format) {
  const bleed = state.showBleed;
  showToast(
    `Compiling ${format.toUpperCase()} with 6x9" mirrored publishing rules...`,
    "info"
  );

  const endpoint = `/api/export/${format}`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: state.activeBookId, bleed: bleed }),
  });

  if (!res.ok) {
    showToast(`Failed to export ${format.toUpperCase()}`, "error");
    return;
  }

  const blob = await res.blob();
  const filename =
    format === "all"
      ? `${state.activeBookId}_ArgonPublishingPackage.zip`
      : format === "pdf"
        ? `${state.activeBookId}_print_6x9.pdf`
        : format === "docx"
          ? `${state.activeBookId}_styled_6x9.docx`
          : `${state.activeBookId}_reflowable.epub`;

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  showToast(`${filename} downloaded successfully!`, "success");
}

// Modal Managers
function openAddSlotModal() {
  const modal = document.getElementById("modal-container");
  if (!modal) return;

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:1rem; color:var(--accent-gold);">+ Add Planned Illustration Slot</h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body">
          <div style="margin-bottom:12px;">
            <label style="font-size:0.75rem; color:var(--text-muted);">Asset Title</label>
            <input type="text" id="new-slot-title" value="Anomalous Chemical Assay Plate" style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; border-radius:4px;">
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
            <div>
              <label style="font-size:0.75rem; color:var(--text-muted);">Placement Type</label>
              <select id="new-slot-placement" style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; border-radius:4px;">
                <option value="Half-Page Top">Half-Page Top</option>
                <option value="Full-Page Recto Plate">Full-Page Recto Plate</option>
                <option value="Inline Archival Insert">Inline Archival Insert</option>
                <option value="Chapter Opener Vignette">Chapter Opener Vignette</option>
                <option value="Chapter End Tailpiece">Chapter End Tailpiece</option>
              </select>
            </div>
            <div>
              <label style="font-size:0.75rem; color:var(--text-muted);">Paragraph Anchor</label>
              <input type="text" id="new-slot-anchor" value="ch01_p03" style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; border-radius:4px;">
            </div>
          </div>
          <div style="margin-bottom:12px;">
            <label style="font-size:0.75rem; color:var(--text-muted);">Ready-to-Copy Image Prompt</label>
            <textarea id="new-slot-prompt" rows="3" style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; border-radius:4px;">Intaglio silver-plate etching of Victorian chemical glassware with brass vernier calipers, high contrast, clean technical engraving --ar 3:2</textarea>
          </div>
          <div>
            <label style="font-size:0.75rem; color:var(--text-muted);">Figure Caption</label>
            <input type="text" id="new-slot-caption" value="Plate III: Assay Analysis of Sublimated Residue." style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; border-radius:4px;">
          </div>
        </div>
        <div class="modal-footer">
          <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 12px; border-radius:4px; cursor:pointer;">Cancel</button>
          <button onclick="submitNewSlot()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Create Slot</button>
        </div>
      </div>
    </div>
  `;
}

async function submitNewSlot() {
  const title = document.getElementById("new-slot-title").value;
  const placement = document.getElementById("new-slot-placement").value;
  const anchor = document.getElementById("new-slot-anchor").value;
  const prompt = document.getElementById("new-slot-prompt").value;
  const caption = document.getElementById("new-slot-caption").value;

  showToast(`Creating new slot: ${title}...`, "info");
  const res = await fetchAPI(`/api/manifest/${state.activeBookId}/add-slot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      placement,
      anchor,
      prompt,
      caption,
    }),
  });

  if (res.status === "success") {
    showToast("New planned illustration slot added!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// Vector Callouts Modal
function openCalloutModal(assetId) {
  const asset = state.manifest.assets.find((a) => a.id === assetId);
  if (!asset) return;

  const modal = document.getElementById("modal-container");
  if (!modal) return;

  const callouts = asset.vector_callouts || [];

  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:1rem; color:var(--accent-cyan);">✎ Vector Callout Overlay: ${asset.title}</h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body">
          <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:12px;">
            Render sharp, non-hallucinated vector callout boxes and arrows directly over maps and diagrams.
          </div>
          
          <div id="callout-list" style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;">
            ${callouts
              .map(
                (c, i) => `
              <div style="display:grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap:6px; align-items:center; background:var(--bg-card); padding:8px; border-radius:4px;">
                <input type="text" placeholder="Label text" value="${c.label}" id="callout-label-${i}" style="padding:4px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem;">
                <input type="number" placeholder="X%" value="${c.x}" id="callout-x-${i}" style="padding:4px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem;">
                <input type="number" placeholder="Y%" value="${c.y}" id="callout-y-${i}" style="padding:4px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem;">
                <select id="callout-type-${i}" style="padding:4px; background:var(--bg-main); border:1px solid var(--border-subtle); color:#FFF; font-size:0.75rem;">
                  <option value="box" ${c.type === "box" ? "selected" : ""}>Box</option>
                  <option value="badge" ${c.type === "badge" ? "selected" : ""}>Badge</option>
                  <option value="arrow_up" ${c.type === "arrow_up" ? "selected" : ""}>Arrow Up</option>
                  <option value="arrow_left" ${c.type === "arrow_left" ? "selected" : ""}>Arrow Left</option>
                </select>
                <button onclick="removeCalloutRow(${i}, '${assetId}')" style="background:#EF4444; color:#FFF; border:none; padding:4px 8px; border-radius:3px; cursor:pointer;">&times;</button>
              </div>
            `
              )
              .join("")}
          </div>

          <button onclick="addCalloutRow('${assetId}')" style="background:rgba(56,189,248,0.15); border:1px solid var(--accent-cyan); color:var(--accent-cyan); padding:6px 12px; border-radius:4px; font-size:0.75rem; cursor:pointer;">
            + Add Callout Label
          </button>
        </div>
        <div class="modal-footer">
          <button onclick="closeModal()" style="background:var(--bg-card); border:1px solid var(--border-subtle); color:#FFF; padding:6px 12px; border-radius:4px; cursor:pointer;">Cancel</button>
          <button onclick="saveCallouts('${assetId}')" style="background:var(--accent-cyan); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Save & Render Overlay</button>
        </div>
      </div>
    </div>
  `;
}

function addCalloutRow(assetId) {
  const asset = state.manifest.assets.find((a) => a.id === assetId);
  if (!asset) return;
  if (!asset.vector_callouts) asset.vector_callouts = [];
  asset.vector_callouts.push({
    label: "NEW VECTOR TAG",
    x: 50,
    y: 50,
    type: "box",
  });
  openCalloutModal(assetId);
}

function removeCalloutRow(index, assetId) {
  const asset = state.manifest.assets.find((a) => a.id === assetId);
  if (!asset || !asset.vector_callouts) return;
  asset.vector_callouts.splice(index, 1);
  openCalloutModal(assetId);
}

async function saveCallouts(assetId) {
  const asset = state.manifest.assets.find((a) => a.id === assetId);
  if (!asset) return;

  const count = (asset.vector_callouts || []).length;
  const updated = [];
  for (let i = 0; i < count; i++) {
    const lbl = document.getElementById(`callout-label-${i}`)?.value || "";
    const x =
      parseFloat(document.getElementById(`callout-x-${i}`)?.value) || 50;
    const y =
      parseFloat(document.getElementById(`callout-y-${i}`)?.value) || 50;
    const type = document.getElementById(`callout-type-${i}`)?.value || "box";
    if (lbl) {
      updated.push({ label: lbl, x, y, type });
    }
  }

  showToast(`Rendering vector callout overlay...`, "info");
  const res = await fetchAPI(
    `/api/manifest/${state.activeBookId}/update-callouts`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_id: assetId, callouts: updated }),
    }
  );

  if (res.status === "success") {
    showToast("Vector callout overlay saved & rendered!", "success");
    closeModal();
    await loadBook(state.activeBookId);
  }
}

// Front Matter Preview Modal
function openFrontMatterModal() {
  const modal = document.getElementById("modal-container");
  if (!modal || !state.frontMatter) return;

  const fm = state.frontMatter;
  modal.innerHTML = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal-content" style="width:680px;" onclick="event.stopPropagation()">
        <div class="modal-header">
          <h3 style="margin:0; font-size:1rem; color:var(--accent-gold);">📖 Front & Back Matter Specifications</h3>
          <button onclick="closeModal()" style="background:none; border:none; color:#AAA; font-size:1.2rem; cursor:pointer;">&times;</button>
        </div>
        <div class="modal-body" style="font-size:0.8rem; line-height:1.4;">
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; margin-bottom:10px;">
            <strong style="color:var(--accent-gold);">1. Half-Title:</strong> ${fm.half_title.title}
          </div>
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; margin-bottom:10px;">
            <strong style="color:var(--accent-gold);">2. Full Title Page:</strong> ${fm.title_page.title} — ${fm.title_page.subtitle}<br>
            <span style="color:var(--text-muted);">Author: ${fm.title_page.author} • Imprint: ${fm.title_page.imprint}</span>
          </div>
          <div style="background:var(--bg-card); padding:12px; border-radius:6px; margin-bottom:10px;">
            <strong style="color:var(--accent-gold);">3. Copyright Page:</strong> ISBN ${fm.copyright_page.isbn_hardcover}<br>
            <span style="color:var(--text-muted);">${fm.copyright_page.colophon_summary}</span>
          </div>
          <div style="background:var(--bg-card); padding:12px; border-radius:6px;">
            <strong style="color:var(--accent-gold);">4. Back Edition Colophon:</strong><br>
            <span style="color:var(--text-muted);">${fm.colophon.body}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button onclick="closeModal()" style="background:var(--accent-gold); color:#000; font-weight:700; border:none; padding:6px 16px; border-radius:4px; cursor:pointer;">Close</button>
        </div>
      </div>
    </div>
  `;
}

function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  const modal = document.getElementById("modal-container");
  if (modal) modal.innerHTML = "";
}

// Window load trigger
window.addEventListener("DOMContentLoaded", initStudio);
