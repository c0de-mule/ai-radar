/**
 * AI Radar — Dashboard Application
 *
 * Fetches daily briefing JSON and renders the dashboard.
 * Supports: category filtering, text search, date navigation.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let currentBriefing = null;  // The currently displayed DailyBriefing
  let availableDates = [];      // From index.json
  let currentDateIndex = 0;     // Index into availableDates
  let activeCategory = 'all';   // Active filter
  let searchQuery = '';          // Current search text

  // Data path — works both locally and on GitHub Pages
  const DATA_BASE = getDataBasePath();

  function getDataBasePath() {
    // If served from /ai-radar/docs/ or /ai-radar/, adjust path
    const path = window.location.pathname;
    if (path.includes('/docs/') || path.endsWith('/docs')) {
      return '../data';
    }
    return 'data';
  }

  // ---------------------------------------------------------------------------
  // DOM References
  // ---------------------------------------------------------------------------
  const $headlineText = document.getElementById('headline-text');
  const $headlineStats = document.getElementById('headline-stats');
  const $currentDate = document.getElementById('current-date');
  const $cardsGrid = document.getElementById('cards-grid');
  const $emptyState = document.getElementById('empty-state');
  const $prevDay = document.getElementById('prev-day');
  const $nextDay = document.getElementById('next-day');
  const $searchInput = document.getElementById('search-input');
  const $filterBtns = document.querySelectorAll('.filter-btn');

  // ---------------------------------------------------------------------------
  // Data Fetching
  // ---------------------------------------------------------------------------

  async function fetchJSON(url) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.error(`Failed to fetch ${url}:`, err);
      return null;
    }
  }

  async function loadIndex() {
    const index = await fetchJSON(`${DATA_BASE}/index.json`);
    if (index && index.dates) {
      availableDates = index.dates;
    }
  }

  async function loadBriefing(dateStr) {
    const fileName = dateStr ? `${dateStr}.json` : 'latest.json';
    const briefing = await fetchJSON(`${DATA_BASE}/${fileName}`);
    if (briefing) {
      currentBriefing = briefing;
      render();
    } else {
      showError(dateStr);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  function render() {
    if (!currentBriefing) return;

    // Update header
    $currentDate.textContent = formatDate(currentBriefing.date);
    document.title = `AI Radar — ${currentBriefing.date}`;

    // Update headline
    $headlineText.textContent = currentBriefing.headline;
    $headlineStats.innerHTML = renderStats(currentBriefing.stats);

    // Filter items
    const filtered = getFilteredItems();

    // Render cards
    if (filtered.length === 0) {
      $cardsGrid.innerHTML = '';
      $emptyState.classList.remove('hidden');
    } else {
      $emptyState.classList.add('hidden');
      $cardsGrid.innerHTML = filtered.map(renderCard).join('');
    }

    // Update nav buttons
    updateNavButtons();
  }

  function getFilteredItems() {
    if (!currentBriefing || !currentBriefing.items) return [];

    let items = currentBriefing.items;

    // Category filter
    if (activeCategory !== 'all') {
      items = items.filter(item => item.category === activeCategory);
    }

    // Text search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      items = items.filter(item =>
        item.title.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        (item.tags || []).some(tag => tag.includes(q)) ||
        (item.source_detail || '').toLowerCase().includes(q)
      );
    }

    return items;
  }

  function showError(dateStr) {
    $headlineText.textContent = dateStr
      ? `No briefing found for ${dateStr}`
      : 'No briefing data available yet';
    $headlineStats.innerHTML = '<span class="stat-badge">Run the pipeline to generate your first briefing</span>';
    $cardsGrid.innerHTML = '';
    $emptyState.classList.add('hidden');
  }

  function updateNavButtons() {
    const dateIdx = availableDates.indexOf(currentBriefing?.date);
    if (dateIdx >= 0) {
      currentDateIndex = dateIdx;
    }
    $nextDay.disabled = currentDateIndex <= 0;
    $prevDay.disabled = currentDateIndex >= availableDates.length - 1;
  }

  function formatDate(dateStr) {
    try {
      const date = new Date(dateStr + 'T12:00:00');
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  }

  // ---------------------------------------------------------------------------
  // Event Handlers
  // ---------------------------------------------------------------------------

  function handleCategoryFilter(e) {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;

    $filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCategory = btn.dataset.category;
    render();
  }

  function handleSearch() {
    searchQuery = $searchInput.value.trim();
    render();
  }

  function handlePrevDay() {
    if (currentDateIndex < availableDates.length - 1) {
      currentDateIndex++;
      loadBriefing(availableDates[currentDateIndex]);
    }
  }

  function handleNextDay() {
    if (currentDateIndex > 0) {
      currentDateIndex--;
      loadBriefing(availableDates[currentDateIndex]);
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  function bindEvents() {
    document.getElementById('category-filters').addEventListener('click', handleCategoryFilter);
    $searchInput.addEventListener('input', debounce(handleSearch, 200));
    $prevDay.addEventListener('click', handlePrevDay);
    $nextDay.addEventListener('click', handleNextDay);
  }

  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  async function init() {
    bindEvents();

    // Load index first (for date navigation), then today's briefing
    await loadIndex();
    await loadBriefing(null); // null = load latest.json
  }

  // Go
  init();
})();
