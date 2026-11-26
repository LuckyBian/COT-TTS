(function () {
  const data = window.DEMO_DATA || { items: [], summary: {} };
  const featuredDemos = document.getElementById('featuredDemos');
  const controlTableBody = document.getElementById('controlTableBody');
  const emotionTableBody = document.getElementById('emotionTableBody');
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

  function renderAudiobook() {
    const container = document.getElementById('audiobookDemo');
    const audiobook = window.AUDIOBOOK_DEMO_DATA;
    if (!container || !audiobook) return;

    const original = audiobook.clips.slice(0, audiobook.original_count);
    const generated = audiobook.clips.slice(audiobook.original_count);
    const transition = original.reduce((sum, clip) => sum + clip.duration, 0);
    const total = audiobook.clips.reduce((sum, clip) => sum + clip.duration, 0);
    const timeLabel = (seconds) => `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(2).padStart(5, '0')}`;

    container.innerHTML = `
      <div class="audiobook-full">
        <div>
          <h3>Listen to the full passage</h3>
          <p>Original audiobook: 0:00–${timeLabel(transition)}<br>COT-TTS continuation: ${timeLabel(transition)}–${timeLabel(total)}</p>
        </div>
        <div class="audiobook-full-player">
          ${renderAudio(audiobook.full_audio, 'Full audiobook passage: four original sentences followed by six COT-TTS sentences')}
          <p id="audiobookPlaybackStatus">4 original sentences · 6 generated sentences</p>
        </div>
      </div>
      <div class="audiobook-group-heading">
        <h3>Original audiobook</h3>
        <p>Sentences 1–4 · Initial history and speaker reference</p>
      </div>
      <div class="audiobook-original-grid">
        ${original.map((clip) => `
          <article class="audiobook-sentence audiobook-original" data-sentence="${clip.number}">
            <div class="audiobook-sentence-heading">
              <h4>Sentence ${clip.number}</h4>
              <span class="audiobook-source">Original</span>
            </div>
            ${renderAudio(clip.audio, `Original audiobook sentence ${clip.number}`)}
          </article>
        `).join('')}
      </div>
      <div class="audiobook-group-heading">
        <h3>COT-TTS continuation</h3>
        <p>Sentences 5–10 · All preceding sentences are retained as history</p>
      </div>
      <div class="audiobook-generated-grid">
        ${generated.map((clip, index) => `
          <article class="audiobook-sentence audiobook-generated" data-sentence="${clip.number}">
            <div class="audiobook-sentence-heading">
              <h4>Sentence ${clip.number}</h4>
              <span class="audiobook-source">COT-TTS</span>
            </div>
            <p class="audiobook-history-label">History: sentences 1–${clip.number - 1}</p>
            <p class="audiobook-history-note">4 original sentences${index ? ` + ${index} generated ${index === 1 ? 'sentence' : 'sentences'}` : ''}</p>
            <div class="audiobook-output">
              <span>Generated audio</span>
              ${renderAudio(clip.audio, `COT-TTS generated sentence ${clip.number}`)}
            </div>
            <details class="audiobook-history">
              <summary>Listen to accumulated history</summary>
              ${renderAudio(clip.history_audio, `Accumulated history for sentence ${clip.number}: sentences 1 through ${clip.number - 1}`)}
            </details>
          </article>
        `).join('')}
      </div>
    `;

    const fullPlayer = container.querySelector('.audiobook-full audio');
    const playbackStatus = document.getElementById('audiobookPlaybackStatus');
    const sentenceCards = [...container.querySelectorAll('[data-sentence]')];
    const clearCurrentSentence = () => {
      sentenceCards.forEach((card) => card.removeAttribute('aria-current'));
    };

    function updateCurrentSentence() {
      let elapsed = 0;
      const current = audiobook.clips.find((clip) => {
        elapsed += clip.duration;
        return fullPlayer.currentTime < elapsed;
      }) || audiobook.clips[audiobook.clips.length - 1];
      sentenceCards.forEach((card) => {
        if (Number(card.dataset.sentence) === current.number) {
          card.setAttribute('aria-current', 'true');
        } else {
          card.removeAttribute('aria-current');
        }
      });
      const source = current.number <= audiobook.original_count ? 'Original audiobook' : 'COT-TTS continuation';
      playbackStatus.textContent = `${source} · Sentence ${current.number} of ${audiobook.clips.length}`;
    }

    fullPlayer.addEventListener('timeupdate', updateCurrentSentence);
    fullPlayer.addEventListener('seeking', updateCurrentSentence);
    fullPlayer.addEventListener('ended', () => {
      clearCurrentSentence();
      playbackStatus.textContent = 'Full passage complete · 4 original sentences · 6 generated sentences';
    });
    container.querySelectorAll('audio').forEach((player) => {
      player.addEventListener('play', () => {
        container.querySelectorAll('audio').forEach((other) => {
          if (other !== player) other.pause();
        });
        if (player === fullPlayer) {
          updateCurrentSentence();
        } else {
          clearCurrentSentence();
          playbackStatus.textContent = '4 original sentences · 6 generated sentences';
        }
      });
    });
  }

  function renderControlDefaultCell(item) {
    return `
      <div class="control-default">
        <div class="output-row output-row-single">
          <span>Historical audio</span>
          ${renderAudio(item.history_audio, `${window.CONTROL_DEMO_DATA.case_id} historical audio`)}
        </div>
        <div class="output-row output-row-single text-row control-cot-row">
          <span>CoT reasoning</span>
          <pre>${escapeHtml(item.cot_text)}</pre>
        </div>
        <div class="output-row output-row-single">
          <span>Default audio</span>
          ${renderAudio(item.output_audio, `${window.CONTROL_DEMO_DATA.case_id} default output audio`)}
        </div>
      </div>
    `;
  }

  function renderControlRow(row, rowIndex, defaultCellHtml) {
    const cells = row.items.map((item) => `
      <td class="control-audio-col">
        <div class="control-audio-card">
          <div class="control-setting">${escapeHtml(item.label)}</div>
          ${renderAudio(item.audio, `${row.variable} ${item.label} audio`)}
        </div>
      </td>
    `).join('');

    const defaultCell = rowIndex === 0
      ? `<td class="control-default-col" rowspan="${window.CONTROL_DEMO_DATA.rows.length}">${defaultCellHtml}</td>`
      : '';

    return `
      <tr>
        ${defaultCell}
        <td class="control-variable-col">
          <div class="control-variable-card">
            <div class="control-variable-en">${escapeHtml(row.variable)}</div>
            <div class="control-variable-note">${escapeHtml(row.note || '')}</div>
          </div>
        </td>
        ${cells}
      </tr>
    `;
  }

  function renderControlTable() {
    if (!controlTableBody || !window.CONTROL_DEMO_DATA) {
      return;
    }
    const controlData = window.CONTROL_DEMO_DATA;
    const defaultCellHtml = renderControlDefaultCell(controlData.default_case);
    controlTableBody.innerHTML = controlData.rows
      .map((row, index) => renderControlRow(row, index, defaultCellHtml))
      .join('');
  }

  function renderEmotionEntry(entry, kind) {
    if (kind === 'audio') {
      return `
        <div class="emotion-entry">
          <div class="emotion-entry-head">
            <span class="emotion-lang">${escapeHtml(entry.lang)}</span>
            <span class="emotion-eval">${escapeHtml(entry.eval_id)}</span>
          </div>
          <div class="output-row output-row-single">
            ${renderAudio(
              entry.output_audio,
              `${entry.eval_id} output audio`
            )}
          </div>
        </div>
      `;
    }

    if (kind === 'history') {
      return `
        <div class="emotion-entry">
          <div class="emotion-entry-head">
            <span class="emotion-lang">${escapeHtml(entry.lang)}</span>
            <span class="emotion-eval">${escapeHtml(entry.eval_id)}</span>
          </div>
          <div class="output-row output-row-single">
            ${renderAudio(
              entry.history_audio,
              `${entry.eval_id} historical audio`
            )}
          </div>
        </div>
      `;
    }

    if (kind === 'text') {
      return `
        <div class="emotion-entry emotion-text-entry">
          <div class="emotion-entry-head">
            <span class="emotion-lang">${escapeHtml(entry.lang)}</span>
            <span class="emotion-eval">${escapeHtml(entry.eval_id)}</span>
          </div>
          <p>${escapeHtml(entry.target_text || 'No target text available.')}</p>
        </div>
      `;
    }

    return '';
  }

  function renderEmotionRow(row) {
    return `
      <tr>
        <td class="emotion-category-col">
          <div class="emotion-category-card">${escapeHtml(row.category)}</div>
        </td>
        <td class="emotion-cell">
          <div class="emotion-stack">
            ${row.entries.map((entry) => renderEmotionEntry(entry, 'history')).join('')}
          </div>
        </td>
        <td class="emotion-cell">
          <div class="emotion-stack">
            ${row.entries.map((entry) => renderEmotionEntry(entry, 'text')).join('')}
          </div>
        </td>
        <td class="emotion-cell">
          <div class="emotion-stack">
            ${row.entries.map((entry) => renderEmotionEntry(entry, 'audio')).join('')}
          </div>
        </td>
      </tr>
    `;
  }

  function renderEmotionTable() {
    if (!emotionTableBody || !window.EMOTION_DEMO_DATA) {
      return;
    }
    emotionTableBody.innerHTML = (window.EMOTION_DEMO_DATA.rows || [])
      .map(renderEmotionRow)
      .join('');
  }

  function renderNeutralReferenceDemos() {
    const container = document.getElementById('neutralReferenceDemos');
    const groups = window.NEUTRAL_REFERENCE_DEMO_DATA?.groups;
    if (!container || !groups) return;

    container.innerHTML = groups.map((group) => `
      <section class="neutral-language" aria-labelledby="neutral-${escapeHtml(group.language)}-title">
        <div class="neutral-reference">
          <h3 id="neutral-${escapeHtml(group.language)}-title">${languageName(group.language)}</h3>
          <p class="neutral-reference-label">Shared neutral reference</p>
          ${renderAudio(group.reference_audio, `${languageName(group.language)} neutral reference shared by all five examples`)}
          <p class="neutral-reference-note">The same reference audio is used for every output in this group.</p>
        </div>
        <div class="neutral-cases">
          ${group.items.map((item) => `
            <article class="neutral-case" aria-label="${escapeHtml(item.eval_id)}">
              <div class="neutral-case-text">
                <span class="neutral-case-id">${escapeHtml(item.eval_id)}</span>
                <span class="neutral-label">Target text</span>
                <p lang="${escapeHtml(group.language)}">${escapeHtml(item.target_text)}</p>
              </div>
              <div class="neutral-audio-pair">
                <div class="neutral-player">
                  <span class="neutral-label">Historical audio</span>
                  ${renderAudio(item.history_audio, `${item.eval_id} historical dialogue audio`)}
                </div>
                <div class="neutral-player neutral-output">
                  <span class="neutral-label">Output audio</span>
                  ${renderAudio(item.output_audio, `${item.eval_id} generated output with the shared neutral reference`)}
                </div>
              </div>
            </article>
          `).join('')}
        </div>
      </section>
    `).join('');

    container.addEventListener('play', (event) => {
      if (event.target.tagName !== 'AUDIO') return;
      document.querySelectorAll('audio').forEach((player) => {
        if (player !== event.target) player.pause();
      });
    }, true);
  }

  function renderHistoryAblationDemos() {
    const container = document.getElementById('historyAblationDemos');
    const groups = window.HISTORY_ABLATION_DEMO_DATA?.groups;
    if (!container || !groups) return;

    const conditions = [
      { key: 'output_audio', title: 'Correct history', note: 'Original dialogue context', className: 'history-condition-correct' },
      { key: 'no_history_audio', title: 'No history', note: 'Historical audio removed', className: '' },
      { key: 'mismatched_history_audio', title: 'Mismatched history', note: 'Unrelated dialogue context', className: '' },
    ];

    container.innerHTML = groups.map((group) => `
      <section class="history-ablation-language" aria-labelledby="history-ablation-${escapeHtml(group.language)}">
        <h3 id="history-ablation-${escapeHtml(group.language)}">${languageName(group.language)}</h3>
        <div class="history-ablation-cases">
          ${group.items.map((item) => `
            <article class="history-ablation-case" aria-label="${escapeHtml(item.eval_id)} history comparison">
              <div class="neutral-case-text">
                <span class="neutral-case-id">${escapeHtml(item.eval_id)}</span>
                <span class="neutral-label">Target text · unchanged across conditions</span>
                <p lang="${escapeHtml(group.language)}">${escapeHtml(item.target_text)}</p>
              </div>
              <div class="history-ablation-inputs">
                <div class="neutral-player">
                  <span class="neutral-label">Reference audio · unchanged across conditions</span>
                  ${renderAudio(item.reference_audio, `${item.eval_id} reference audio shared across all three history conditions`)}
                </div>
                <div class="neutral-player">
                  <span class="neutral-label">Original historical audio</span>
                  ${renderAudio(item.history_audio, `${item.eval_id} original historical audio used in the correct-history condition`)}
                </div>
              </div>
              <div class="history-ablation-outputs">
                ${conditions.map((condition) => `
                  <section class="history-condition ${condition.className}" aria-label="${escapeHtml(condition.title)} output">
                    <h4>${condition.title}</h4>
                    <p>${condition.note}</p>
                    ${renderAudio(item[condition.key], `${item.eval_id} output with ${condition.title.toLowerCase()}`)}
                  </section>
                `).join('')}
              </div>
            </article>
          `).join('')}
        </div>
      </section>
    `).join('');

    container.addEventListener('play', (event) => {
      if (event.target.tagName !== 'AUDIO') return;
      document.querySelectorAll('audio').forEach((player) => {
        if (player !== event.target) player.pause();
      });
    }, true);
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
  renderAudiobook();
  renderControlTable();
  renderEmotionTable();
  renderNeutralReferenceDemos();
  renderHistoryAblationDemos();
  render();
})();
