(function () {
  const data = window.DEMO_DATA || { items: [], summary: {} };
  const featuredDemos = document.getElementById('featuredDemos');
  const tableBody = document.getElementById('demoTableBody');
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

  function displayModelName(name) {
    if (name === 'COTalker-0.6B') return 'Our-0.6B';
    if (name === 'COTalker-1.7B') return 'Our-1.7B';
    return name;
  }

  const MODEL_ORDER = [
    'ground_truth',
    'final__our-0.6',
    'final__our-1.7',
    'three__dia-a3b-fish2',
    'three__dia-a3b-voxcpm',
    'three__qwen3asr-a3b-fish2',
    'three__qwenasr-a3b-voxcpm',
    'two__qwen-fish',
    'two__qwen-voxcpm',
    'two__qwen3omni-seedvc',
  ];

  function orderedModels(models) {
    const rank = new Map(MODEL_ORDER.map((key, index) => [key, index]));
    return [...models].sort((a, b) => {
      const aRank = rank.has(a.key) ? rank.get(a.key) : Number.MAX_SAFE_INTEGER;
      const bRank = rank.has(b.key) ? rank.get(b.key) : Number.MAX_SAFE_INTEGER;
      return aRank - bRank;
    });
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
            <div class="model-name">${escapeHtml(displayModelName(model.name))}</div>
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
    const models = orderedModels(item.models);
    return `
      <tr>
        <td class="history-col">
          <div class="info-card model-item info-item">
            <div class="case-id">${escapeHtml(item.eval_id)}</div>
            <div class="case-meta">${languageName(item.language)}</div>
            <div class="output-row output-row-single">
              <span>Historical audio</span>
              ${renderAudio(item.history_audio, `${item.eval_id} historical dialogue audio`)}
            </div>
          </div>
        </td>
        <td class="target-col">
          <div class="info-card model-item info-item">
            <div class="output-row output-row-single text-row">
              <span>Target text</span>
              <p>${escapeHtml(item.target_text || 'No target text available.')}</p>
            </div>
          </div>
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
    const visibleItems = data.items || [];
    tableBody.innerHTML = visibleItems.map(renderRow).join('');

    const totalModels = data.items.reduce((sum, item) => sum + item.models.length, 0);
    const visibleModels = visibleItems.reduce((sum, item) => sum + item.models.length, 0);

    if (sampleCount) {
      sampleCount.textContent = `${data.items.length} samples`;
    }
    if (modelCount) {
      modelCount.textContent = `${totalModels} model entries`;
    }
    visibleCount.textContent = `Showing ${visibleItems.length} samples and ${visibleModels} model entries`;

    if (!visibleItems.length) {
      tableBody.innerHTML = `
        <tr>
          <td class="empty-state" colspan="3">
            No demos found.
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

  renderFeatured();
  render();
})();
