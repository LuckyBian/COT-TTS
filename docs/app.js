(function () {
  const data = window.DEMO_DATA || { items: [], summary: {} };
  const featuredDemos = document.getElementById('featuredDemos');
  const tableBody = document.getElementById('demoTableBody');
  const languageFilter = document.getElementById('languageFilter');
  const familyFilter = document.getElementById('familyFilter');
  const searchInput = document.getElementById('searchInput');
  const sampleCount = document.getElementById('sampleCount');
  const modelCount = document.getElementById('modelCount');
  const visibleCount = document.getElementById('visibleCount');

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function languageName(lang) {
    if (lang === 'en') return 'English';
    if (lang === 'zh') return 'Chinese';
    return String(lang || 'Unknown').toUpperCase();
  }

  function matchesFilters(item) {
    const lang = languageFilter.value;
    const family = familyFilter.value;
    const query = searchInput.value.trim().toLowerCase();
    if (lang !== 'all' && item.language !== lang) return false;

    const models = filteredModels(item.models);
    if (!models.length) return false;

    if (!query) return true;
    const haystack = [
      item.eval_id,
      item.target_text,
      ...item.models.flatMap((model) => [model.key, model.display_key, model.name]),
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  }

  function filteredModels(models) {
    const family = familyFilter.value;
    if (family === 'all') return models;
    return models.filter((model) => model.family === family);
  }

  function renderAudio(src, label) {
    if (!src) {
      return '<span class="missing">Missing audio</span>';
    }
    return `
      <audio controls preload="none" src="./${escapeHtml(src)}" aria-label="${escapeHtml(label)}"></audio>
    `;
  }

  function renderTextBlock(label, text, extraClass = '') {
    return `
      <div class="featured-text-block ${escapeHtml(extraClass)}">
        <div class="text-label">${escapeHtml(label)}</div>
        <p>${escapeHtml(text || 'No text available.')}</p>
      </div>
    `;
  }

  function renderFeaturedCase(item, index) {
    return `
      <article class="featured-demo">
        <div class="featured-number">${String(index + 1).padStart(2, '0')}</div>
        <h3>${escapeHtml(item.title)}</h3>
        <div class="featured-flow">
          <section class="featured-step">
            <span>Historical dialogue audio</span>
            ${renderAudio(item.history_audio, `${item.title} historical dialogue audio`)}
          </section>
          ${renderTextBlock('Target text', item.target_text)}
          <section class="featured-step">
            <span>Reference audio</span>
            ${renderAudio(item.reference_audio, `${item.title} reference audio`)}
          </section>
          ${renderTextBlock('Historical understanding text', item.understanding_text)}
          ${renderTextBlock('CoT analysis', item.cot_text, 'cot-full')}
          <section class="featured-step">
            <span>Generated output audio</span>
            ${renderAudio(item.output_audio, `${item.title} generated output audio`)}
          </section>
        </div>
      </article>
    `;
  }

  function renderModel(model) {
    return `
      <article class="model-item ${escapeHtml(model.family)}">
        <div class="model-head">
          <div>
            <div class="model-name">${escapeHtml(model.name)}</div>
            <div class="model-key">${escapeHtml(model.display_key || model.key)}</div>
          </div>
          <span class="family-pill">${escapeHtml(model.family_label)}</span>
        </div>
        <div class="output-row">
          <span>Generated audio</span>
          ${renderAudio(model.output_audio, `${model.name} generated audio`)}
        </div>
      </article>
    `;
  }

  function renderRow(item) {
    const models = filteredModels(item.models);
    return `
      <tr>
        <td class="history-col">
          <div class="case-id">${escapeHtml(item.eval_id)}</div>
          <div class="case-meta">${languageName(item.language)}</div>
          ${renderAudio(item.history_audio, `${item.eval_id} historical dialogue audio`)}
        </td>
        <td class="target-col">
          <p>${escapeHtml(item.target_text || 'No target text available.')}</p>
        </td>
        <td class="models-col">
          <div class="models-grid">
            ${models.map(renderModel).join('')}
          </div>
        </td>
      </tr>
    `;
  }

  function render() {
    const visibleItems = data.items.filter(matchesFilters);
    tableBody.innerHTML = visibleItems.map(renderRow).join('');

    const totalModels = data.items.reduce((sum, item) => sum + item.models.length, 0);
    const visibleModels = visibleItems.reduce((sum, item) => sum + filteredModels(item.models).length, 0);

    sampleCount.textContent = `${data.items.length} samples`;
    modelCount.textContent = `${totalModels} model entries`;
    visibleCount.textContent = `Showing ${visibleItems.length} samples and ${visibleModels} model entries`;

    if (!visibleItems.length) {
      tableBody.innerHTML = `
        <tr>
          <td class="empty-state" colspan="3">
            No matching demos. Try clearing the filters or search text.
          </td>
        </tr>
      `;
    }
  }

  function renderFeatured() {
    const featured = data.featured || [];
    featuredDemos.innerHTML = featured.map(renderFeaturedCase).join('');
    if (!featured.length) {
      featuredDemos.innerHTML = '<div class="empty-featured">No featured demos found.</div>';
    }
  }

  [languageFilter, familyFilter, searchInput].forEach((el) => {
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  });

  renderFeatured();
  render();
})();
