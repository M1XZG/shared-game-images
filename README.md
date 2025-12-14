# Tower Unite Images

A minimal static site to view and share direct links to images, intended for Tower Unite use. Host on GitHub Pages and quickly render images from external URLs.

## Features
- Paste an image URL and display it instantly
- Auto-load via query param: `?src=https://...`
- Quick actions: open original, copy link, download
- No backend — plain HTML/CSS/JS

## Usage
- Open the site and paste a link, or
- Share a URL like:
  - `https://<your-pages-domain>/towerunite-images/?src=https://example.com/pic.jpg`

> Note: External images are loaded client-side. Some hosts block cross-origin access or downloads; right-click Save As usually works.

## GitHub Pages Deployment
You can deploy from the `main` branch root or `/docs`. This repo is ready to serve from root.

### Option A: Enable Pages (no workflow)
1. Push this repo to GitHub.
2. In the repo: Settings → Pages → Build and deployment
3. Source: `Deploy from a branch`
4. Branch: `main` and folder: `/ (root)`
5. Save. Your site appears at `https://<username>.github.io/<repo>/`.

### Option B: Use GitHub Actions workflow
- This repo includes a workflow in `.github/workflows/pages.yml` that builds and publishes the site to Pages.
- Enable GitHub Pages (Settings → Pages → Source: GitHub Actions) after pushing.

## Local Preview
Just open `index.html` in a browser, or run a simple server:

```bash
# Python 3
python -m http.server 8080
# Then visit http://localhost:8080/
```
