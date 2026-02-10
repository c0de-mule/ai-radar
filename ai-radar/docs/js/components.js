/**
 * AI Radar — Reusable UI Components
 *
 * Pure functions that take data and return HTML strings.
 * No side effects, no DOM manipulation — just rendering.
 */

const CATEGORY_EMOJI = {
  models: '🧠',
  tools: '🛠️',
  research: '📄',
  industry: '📰',
  tutorials: '📚',
};

const CATEGORY_LABEL = {
  models: 'Models',
  tools: 'Tools',
  research: 'Research',
  industry: 'Industry',
  tutorials: 'Tutorials',
};

/**
 * Render a single briefing item card.
 * @param {Object} item - A BriefingItem from the JSON data.
 * @returns {string} HTML string for the card.
 */
function renderCard(item) {
  const emoji = CATEGORY_EMOJI[item.category] || '📋';
  const label = CATEGORY_LABEL[item.category] || item.category;

  // Score indicator
  let scoreClass = 'score-low';
  if (item.relevance_score >= 7) scoreClass = 'score-high';
  else if (item.relevance_score >= 4) scoreClass = 'score-med';

  // Tags (max 3)
  const tagsHtml = (item.tags || [])
    .slice(0, 3)
    .map(tag => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join('');

  return `
    <article class="card" data-category="${item.category}" data-id="${item.id}">
      <div class="card-header">
        <h3 class="card-title">
          <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a>
        </h3>
        <span class="card-category" data-category="${item.category}">${emoji} ${label}</span>
      </div>
      <p class="card-summary">${escapeHtml(item.summary)}</p>
      <div class="card-meta">
        <span class="card-source">${escapeHtml(item.source_detail || item.source)}</span>
        <div class="card-tags">${tagsHtml}</div>
        <span class="card-score">
          <span class="score-dot ${scoreClass}"></span>
          ${item.relevance_score.toFixed(1)}
        </span>
      </div>
    </article>
  `;
}

/**
 * Render stats badges for the headline banner.
 * @param {Object} stats - BriefingStats object.
 * @returns {string} HTML string for stat badges.
 */
function renderStats(stats) {
  const badges = [];

  badges.push(`<span class="stat-badge">📊 ${stats.total_items} items</span>`);

  if (stats.sources) {
    const sourceList = Object.entries(stats.sources)
      .map(([src, count]) => `${count} ${src}`)
      .join(', ');
    badges.push(`<span class="stat-badge">📡 ${sourceList}</span>`);
  }

  return badges.join('');
}

/**
 * Render skeleton loading cards.
 * @param {number} count - Number of skeleton cards.
 * @returns {string} HTML string for skeleton cards.
 */
function renderSkeletons(count = 6) {
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="card skeleton">
        <div class="skeleton-line w80"></div>
        <div class="skeleton-line w100"></div>
        <div class="skeleton-line w60"></div>
      </div>
    `;
  }
  return html;
}

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str - Raw string.
 * @returns {string} Escaped string.
 */
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
