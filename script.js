function qs(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function setError(msg) {
  const error = document.getElementById('error');
  error.textContent = msg || '';
  error.classList.toggle('hidden', !msg);
}

function showViewer(url) {
  const viewer = document.getElementById('viewer');
  const img = document.getElementById('image');
  const openLink = document.getElementById('open-link');
  viewer.classList.remove('hidden');
  img.src = url;
  openLink.href = url;
  setError('');
}

async function downloadImage(url) {
  try {
    const res = await fetch(url, { mode: 'no-cors' });
    const a = document.createElement('a');
    a.href = url;
    const filename = url.split('/').pop()?.split('?')[0] || 'image';
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) {
    setError('Unable to download this image directly. Try right-click > Save image as.');
  }
}

function init() {
  const form = document.getElementById('image-form');
  const input = document.getElementById('src');
  const copyBtn = document.getElementById('copy-link');
  const dlBtn = document.getElementById('download-image');

  const initial = qs('src');
  if (initial) {
    input.value = initial;
    showViewer(initial);
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = input.value.trim();
    if (!url) return;
    try {
      new URL(url);
      const params = new URLSearchParams(window.location.search);
      params.set('src', url);
      const newUrl = `${window.location.pathname}?${params.toString()}`;
      history.replaceState(null, '', newUrl);
      showViewer(url);
    } catch (err) {
      setError('Please enter a valid URL.');
    }
  });

  copyBtn.addEventListener('click', async () => {
    const url = document.getElementById('image').src;
    try {
      await navigator.clipboard.writeText(url);
      setError('Link copied to clipboard.');
      setTimeout(() => setError(''), 1200);
    } catch (e) {
      setError('Unable to copy link to clipboard.');
    }
  });

  dlBtn.addEventListener('click', () => {
    const url = document.getElementById('image').src;
    downloadImage(url);
  });
}

document.addEventListener('DOMContentLoaded', init);
