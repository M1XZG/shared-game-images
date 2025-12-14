function qs(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function setError(msg) {
  const error = document.getElementById('error');
  error.textContent = msg || '';
  error.classList.toggle('hidden', !msg);
}

function mediaUrl(filename) {
  // Build a URL relative to the current page for images in media/
  return new URL(filename, window.location.href).toString();
}

async function loadGallery() {
  const grid = document.getElementById('gallery-grid');
  const status = document.getElementById('gallery-status');
  const owner = 'M1XZG';
  const repo = 'towerunite-images';
  const branch = 'main';
  try {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/media?ref=${branch}`);
    if (!res.ok) throw new Error(`GitHub API error ${res.status}`);
    const files = await res.json();
    const images = files.filter((f) => f.type === 'file');
    if (!images.length) {
      status.textContent = 'No images yet. Add files to media/ and refresh.';
      grid.innerHTML = '<div class="empty">No images in media/.</div>';
      return;
    }
    status.textContent = `Loaded ${images.length} file(s) from media/`;
    grid.innerHTML = '';
    images.forEach((file) => {
      const card = document.createElement('div');
      card.className = 'thumb';
      const img = document.createElement('img');
      img.src = mediaUrl(file.path);
      img.alt = file.name;
      const label = document.createElement('div');
      label.className = 'thumb-name';
      label.textContent = file.name;
      card.appendChild(img);
      card.appendChild(label);
      card.addEventListener('click', () => {
        const url = file.path;
        const params = new URLSearchParams(window.location.search);
        params.set('src', url);
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        history.replaceState(null, '', newUrl);
        document.getElementById('src').value = url;
        showViewer(url);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      grid.appendChild(card);
    });
  } catch (err) {
    status.textContent = 'Unable to load media list (GitHub API). Add images to media/ and try again.';
    console.error(err);
  }
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

  loadGallery();

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = input.value.trim();
    if (!url) return;
    const finalUrl = url.replace(/^\.\//, '');
    // Enforce media/ prefix to keep all images local
    if (!finalUrl.startsWith('media/')) {
      setError('Images must be in the media/ folder (use media/your-image.jpg).');
      return;
    }
    const params = new URLSearchParams(window.location.search);
    params.set('src', finalUrl);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    history.replaceState(null, '', newUrl);
    showViewer(finalUrl);
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
