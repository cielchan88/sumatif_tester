// Hafalan recorder — supports single-stage (doa) and two-stage (hadits).
(function () {
  'use strict';

  function pickMimeType() {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    if (typeof MediaRecorder === 'undefined') return null;
    for (const t of candidates) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
  }

  function ensureGetUserMedia() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error(
        'Browsermu belum mendukung perekaman suara. Coba pakai Chrome / Edge / Safari versi terbaru.'
      );
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error('Browsermu belum mendukung MediaRecorder.');
    }
  }

  class Recorder {
    constructor() {
      this.mediaRecorder = null;
      this.chunks = [];
      this.stream = null;
      this.mimeType = pickMimeType();
    }

    async start() {
      ensureGetUserMedia();
      this.chunks = [];
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const opts = this.mimeType ? { mimeType: this.mimeType } : undefined;
      this.mediaRecorder = new MediaRecorder(this.stream, opts);
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) this.chunks.push(e.data);
      };
      this.mediaRecorder.start();
    }

    stop() {
      return new Promise((resolve) => {
        if (!this.mediaRecorder) return resolve(null);
        this.mediaRecorder.onstop = () => {
          const blob = new Blob(this.chunks, {
            type: this.mimeType || 'audio/webm',
          });
          this._closeStream();
          resolve(blob);
        };
        try {
          this.mediaRecorder.stop();
        } catch (e) {
          this._closeStream();
          resolve(new Blob(this.chunks, { type: this.mimeType || 'audio/webm' }));
        }
      });
    }

    _closeStream() {
      if (this.stream) {
        this.stream.getTracks().forEach((t) => t.stop());
        this.stream = null;
      }
      this.mediaRecorder = null;
    }
  }

  function fmtTime(s) {
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
  }

  function attachTimer(el) {
    let seconds = 0;
    el.textContent = fmtTime(0);
    const id = setInterval(() => {
      seconds += 1;
      el.textContent = fmtTime(seconds);
    }, 1000);
    return () => clearInterval(id);
  }

  function showError(box, msg) {
    if (!box) {
      alert(msg);
      return;
    }
    box.textContent = msg;
    box.classList.remove('d-none');
  }

  function setLoading(button, label, original) {
    if (label) {
      button.disabled = true;
      button.dataset.original = original || button.innerHTML;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>' + label;
    } else {
      button.disabled = false;
      button.innerHTML = button.dataset.original || button.innerHTML;
    }
  }

  // -------------------------------------------------------------------------
  // Single-stage (doa)
  // -------------------------------------------------------------------------
  window.initDoaRecorder = function (config) {
    const btn = document.getElementById(config.buttonId);
    const status = document.getElementById(config.statusId);
    const timer = document.getElementById(config.timerId);
    const errBox = document.getElementById(config.errorId);
    const recorder = new Recorder();
    let recording = false;
    let stopTimer = null;

    btn.addEventListener('click', async () => {
      errBox.classList.add('d-none');
      if (!recording) {
        try {
          await recorder.start();
          recording = true;
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-danger');
          btn.innerHTML = '⏹️ Selesai Rekam';
          status.textContent = 'Sedang merekam... bacalah dengan jelas.';
          stopTimer = attachTimer(timer);
        } catch (e) {
          showError(errBox, e.message || 'Tidak bisa mengakses mikrofon.');
        }
        return;
      }
      const blob = await recorder.stop();
      recording = false;
      if (stopTimer) stopTimer();
      setLoading(btn, 'Memproses suara...', '🎙️ Mulai Rekam');
      status.textContent = 'Mengirim ke server, mohon tunggu sebentar...';
      try {
        const form = new FormData();
        form.append('audio', blob, 'recording.webm');
        const res = await fetch(config.submitUrl, {
          method: 'POST',
          body: form,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          throw new Error(data.error || 'Gagal memproses rekaman.');
        }
        window.location.href = data.result_url;
      } catch (e) {
        setLoading(btn, null);
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-primary');
        btn.innerHTML = '🎙️ Coba Rekam Lagi';
        status.textContent = '';
        showError(errBox, e.message || 'Terjadi kesalahan.');
      }
    });
  };

  // -------------------------------------------------------------------------
  // Two-stage (hadits)
  // -------------------------------------------------------------------------
  window.initHaditsRecorder = function (config) {
    const stages = {
      arab: {
        section: document.getElementById('stage-arab'),
        btn: document.getElementById('btn-arab'),
        status: document.getElementById('status-arab'),
        timer: document.getElementById('timer-arab'),
      },
      artinya: {
        section: document.getElementById('stage-artinya'),
        btn: document.getElementById('btn-artinya'),
        status: document.getElementById('status-artinya'),
        timer: document.getElementById('timer-artinya'),
      },
    };
    const errBox = document.getElementById(config.errorId);
    const stepLabel = document.getElementById('step-label');

    let stage = 'arab';
    let recording = false;
    let recorder = new Recorder();
    let stopTimer = null;
    let blobArab = null;
    let blobArtinya = null;

    function showStage(name) {
      stage = name;
      Object.keys(stages).forEach((k) => {
        stages[k].section.classList.toggle('d-none', k !== name);
      });
      if (name === 'arab') stepLabel.textContent = 'Langkah 1 dari 2';
      if (name === 'artinya') stepLabel.textContent = 'Langkah 2 dari 2';
    }

    async function toggle(name) {
      errBox.classList.add('d-none');
      const s = stages[name];
      if (!recording) {
        try {
          recorder = new Recorder();
          await recorder.start();
          recording = true;
          s.btn.classList.remove('btn-primary');
          s.btn.classList.add('btn-danger');
          s.btn.innerHTML = '⏹️ Selesai Rekam';
          s.status.textContent = 'Sedang merekam... bacalah dengan jelas.';
          stopTimer = attachTimer(s.timer);
        } catch (e) {
          showError(errBox, e.message || 'Tidak bisa mengakses mikrofon.');
        }
        return;
      }
      const blob = await recorder.stop();
      recording = false;
      if (stopTimer) stopTimer();
      if (name === 'arab') {
        blobArab = blob;
        s.btn.disabled = true;
        s.btn.innerHTML = '✅ Bacaan Arab tersimpan';
        s.status.textContent = 'Bagus! Lanjut ke langkah berikutnya...';
        setTimeout(() => showStage('artinya'), 600);
      } else {
        blobArtinya = blob;
        s.btn.disabled = true;
        s.btn.innerHTML = '✅ Artinya tersimpan';
        s.status.textContent = 'Mengirim kedua rekaman ke server...';
        await submitBoth();
      }
    }

    async function submitBoth() {
      try {
        const form = new FormData();
        form.append('audio_arab', blobArab, 'arab.webm');
        form.append('audio_artinya', blobArtinya, 'artinya.webm');
        const res = await fetch(config.submitUrl, {
          method: 'POST',
          body: form,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          throw new Error(data.error || 'Gagal memproses rekaman.');
        }
        window.location.href = data.result_url;
      } catch (e) {
        showError(errBox, e.message || 'Terjadi kesalahan.');
        // Reset stage 2 so the user can retry
        stages.artinya.btn.disabled = false;
        stages.artinya.btn.classList.remove('btn-danger');
        stages.artinya.btn.classList.add('btn-primary');
        stages.artinya.btn.innerHTML = '🎙️ Rekam Ulang Artinya';
      }
    }

    stages.arab.btn.addEventListener('click', () => toggle('arab'));
    stages.artinya.btn.addEventListener('click', () => toggle('artinya'));
    showStage('arab');
  };

  // -------------------------------------------------------------------------
  // Multi-stage (Quran per-ayat)
  // -------------------------------------------------------------------------
  // config: { totalAyat, submitUrl, buttonId, statusId, timerId, progressId, errorId }
  window.initAyatRecorder = function (config) {
    const btn = document.getElementById(config.buttonId);
    const status = document.getElementById(config.statusId);
    const timer = document.getElementById(config.timerId);
    const progress = document.getElementById(config.progressId);
    const errBox = document.getElementById(config.errorId);
    const totalAyat = config.totalAyat;
    let currentAyat = 1;
    let recording = false;
    let recorder = new Recorder();
    let stopTimer = null;
    const blobs = [];

    function updateProgress() {
      progress.textContent = `Ayat ${currentAyat} dari ${totalAyat}`;
      btn.innerHTML = `🎙️ Rekam Ayat ${currentAyat}`;
      btn.classList.remove('btn-danger');
      btn.classList.add('btn-primary');
      status.textContent = '';
      timer.textContent = '00:00';
    }

    btn.addEventListener('click', async () => {
      errBox.classList.add('d-none');
      if (!recording) {
        try {
          recorder = new Recorder();
          await recorder.start();
          recording = true;
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-danger');
          btn.innerHTML = '⏹️ Selesai Ayat';
          status.textContent = 'Sedang merekam ayat ' + currentAyat + '...';
          stopTimer = attachTimer(timer);
        } catch (e) {
          showError(errBox, e.message || 'Tidak bisa mengakses mikrofon.');
        }
        return;
      }
      const blob = await recorder.stop();
      recording = false;
      if (stopTimer) stopTimer();
      blobs.push(blob);

      if (currentAyat < totalAyat) {
        currentAyat += 1;
        // brief pause then prep next
        btn.disabled = true;
        btn.innerHTML = `✅ Ayat ${currentAyat - 1} tersimpan...`;
        status.textContent = `Bersiap untuk ayat ${currentAyat}...`;
        setTimeout(() => {
          btn.disabled = false;
          updateProgress();
        }, 800);
      } else {
        btn.disabled = true;
        btn.innerHTML = '✅ Semua ayat tersimpan';
        status.textContent = 'Mengirim ke server, mohon tunggu...';
        progress.textContent = 'Memproses semua rekaman...';
        try {
          const form = new FormData();
          blobs.forEach((b, i) => {
            form.append(`audio_${i + 1}`, b, `ayat_${i + 1}.webm`);
          });
          const res = await fetch(config.submitUrl, {
            method: 'POST', body: form,
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data.ok) {
            throw new Error(data.error || 'Gagal memproses rekaman.');
          }
          window.location.href = data.result_url;
        } catch (e) {
          showError(errBox, e.message || 'Terjadi kesalahan.');
          btn.disabled = false;
          btn.innerHTML = '🔁 Coba Kirim Ulang';
          btn.onclick = async () => {
            errBox.classList.add('d-none');
            btn.disabled = true;
            status.textContent = 'Mengirim ulang...';
            try {
              const form = new FormData();
              blobs.forEach((b, i) => {
                form.append(`audio_${i + 1}`, b, `ayat_${i + 1}.webm`);
              });
              const res = await fetch(config.submitUrl, {
                method: 'POST', body: form,
              });
              const data = await res.json().catch(() => ({}));
              if (!res.ok || !data.ok) throw new Error(data.error || 'Gagal.');
              window.location.href = data.result_url;
            } catch (err) {
              showError(errBox, err.message);
              btn.disabled = false;
            }
          };
        }
      }
    });
  };
})();
