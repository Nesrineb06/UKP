(function () {
  const API = window.API_BASE || '';
  const loading = document.getElementById('loading');
  const comparisonEl = document.getElementById('comparison');
  const errorEl = document.getElementById('error');
  const reviewA = document.getElementById('review-a');
  const reviewB = document.getElementById('review-b');
  const modelA = document.getElementById('model-a');
  const modelB = document.getElementById('model-b');
  const btnA = document.getElementById('btn-a');
  const btnB = document.getElementById('btn-b');
  const btnTie = document.getElementById('btn-tie');
  const votedMsg = document.getElementById('voted-msg');

  let currentComparisonId = null;

  function showError(msg) {
    loading.classList.add('hidden');
    comparisonEl.classList.add('hidden');
    errorEl.textContent = msg;
    errorEl.classList.remove('hidden');
  }

  function setButtonsEnabled(enabled) {
    btnA.disabled = btnB.disabled = btnTie.disabled = !enabled;
  }

  async function loadComparison() {
    loading.classList.remove('hidden');
    comparisonEl.classList.add('hidden');
    errorEl.classList.add('hidden');
    modelA.classList.add('hidden');
    modelB.classList.add('hidden');
    votedMsg.classList.add('hidden');
    document.getElementById('panel-a').classList.remove('revealed');
    document.getElementById('panel-b').classList.remove('revealed');
    setButtonsEnabled(true);
    try {
      const res = await fetch(API + '/comparison');
      if (!res.ok) throw new Error('Failed to load comparison');
      const data = await res.json();
      currentComparisonId = data.comparison_id;
      reviewA.textContent = data.review_a;
      reviewB.textContent = data.review_b;
      loading.classList.add('hidden');
      comparisonEl.classList.remove('hidden');
    } catch (e) {
      showError(e.message || 'Error loading comparison');
    }
  }

  async function revealModels() {
    if (!currentComparisonId) return;
    try {
      const res = await fetch(API + '/comparison/' + currentComparisonId + '/reveal');
      if (!res.ok) return;
      const data = await res.json();
      modelA.textContent = 'Model: ' + data.model_a;
      modelB.textContent = 'Model: ' + data.model_b;
      modelA.classList.remove('hidden');
      modelB.classList.remove('hidden');
      document.getElementById('panel-a').classList.add('revealed');
      document.getElementById('panel-b').classList.add('revealed');
    } catch (_) {}
  }

  async function vote(winner) {
    if (!currentComparisonId) return;
    setButtonsEnabled(false);
    try {
      const res = await fetch(API + '/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comparison_id: currentComparisonId, winner: winner })
      });
      if (!res.ok) throw new Error('Vote failed');
      votedMsg.classList.remove('hidden');
      revealModels();
    } catch (e) {
      errorEl.textContent = e.message || 'Vote failed';
      errorEl.classList.remove('hidden');
      setButtonsEnabled(true);
    }
  }

  btnA.addEventListener('click', () => vote('A'));
  btnB.addEventListener('click', () => vote('B'));
  btnTie.addEventListener('click', () => vote('tie'));

  loadComparison();
})();
