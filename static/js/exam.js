(function () {
  const blocks = Array.from(document.querySelectorAll('.question-block'));
  const cells = Array.from(document.querySelectorAll('.qcell'));
  const timerEl = document.getElementById('timer');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const clearBtn = document.getElementById('clear-btn');
  const submitBtn = document.getElementById('submit-btn');
  const submitForm = document.getElementById('submit-form');
  const answeredCountEl = document.getElementById('answered-count');
  let currentIdx = blocks.findIndex(b => b.style.display !== 'none');
  if (currentIdx < 0) currentIdx = 0;

  function answeredCount() {
    return blocks.filter(b => b.querySelector('input[type=radio]:checked')).length;
  }
  function flaggedQids() {
    return new Set(cells.filter(c => c.classList.contains('flagged')).map(c => c.dataset.qid));
  }

  function refreshGrid() {
    blocks.forEach((b, i) => {
      const cell = cells[i];
      cell.classList.remove('active', 'answered', 'flagged');
      if (b.querySelector('input[type=radio]:checked')) cell.classList.add('answered');
      if (b.dataset.flagged === '1') cell.classList.add('flagged');
      if (i === currentIdx) cell.classList.add('active');
    });
  }

  function showQ(i) {
    if (i < 0 || i >= blocks.length) return;
    blocks[currentIdx].style.display = 'none';
    currentIdx = i;
    blocks[currentIdx].style.display = 'block';
    refreshGrid();
    save({ current_idx: currentIdx });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function save(payload) {
    fetch('/exam/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {});
  }

  // Initial grid state from server-side rendered flags
  blocks.forEach((b, i) => {
    const flagBtn = b.querySelector('.flag-btn');
    if (flagBtn && flagBtn.textContent.includes('Ditandai')) {
      b.dataset.flagged = '1';
    }
  });
  refreshGrid();

  // Wire radios — autosave on change
  document.querySelectorAll('input[type=radio]').forEach(r => {
    r.addEventListener('change', () => {
      const block = r.closest('.question-block');
      const qid = block.dataset.qid;
      save({ question_id: qid, answer: r.value, current_idx: currentIdx });
      refreshGrid();
    });
  });

  // Flag buttons
  document.querySelectorAll('.flag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const qid = btn.dataset.qid;
      const block = blocks.find(b => b.dataset.qid === qid);
      const flagged = block.dataset.flagged === '1';
      block.dataset.flagged = flagged ? '' : '1';
      btn.textContent = flagged ? '🏳️ Tandai' : '🚩 Ditandai';
      save({ question_id: qid, flagged: !flagged });
      refreshGrid();
    });
  });

  // Navigation
  prevBtn.addEventListener('click', () => showQ(currentIdx - 1));
  nextBtn.addEventListener('click', () => showQ(currentIdx + 1));
  cells.forEach((c, i) => c.addEventListener('click', () => showQ(i)));

  clearBtn.addEventListener('click', () => {
    const block = blocks[currentIdx];
    const qid = block.dataset.qid;
    block.querySelectorAll('input[type=radio]').forEach(r => (r.checked = false));
    save({ question_id: qid, answer: null, clear: true, current_idx: currentIdx });
    refreshGrid();
  });

  // Submit confirmation
  const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
  submitBtn.addEventListener('click', () => {
    answeredCountEl.textContent = answeredCount();
    modal.show();
  });

  // Timer
  let remaining = parseInt(timerEl.dataset.remaining, 10) || 0;
  function tick() {
    if (remaining <= 0) {
      submitForm.submit();
      return;
    }
    const m = Math.floor(remaining / 60).toString().padStart(2, '0');
    const s = (remaining % 60).toString().padStart(2, '0');
    timerEl.textContent = `${m}:${s}`;
    if (remaining <= 5 * 60) timerEl.classList.add('warning');
    remaining -= 1;
  }
  tick();
  setInterval(tick, 1000);
})();
