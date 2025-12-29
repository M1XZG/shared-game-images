# GitHub Pages Static Site Guide

This document describes the static site features and usage for the shared-game-images repository. This site is designed for quick image sharing and gallery viewing, and can be deployed via GitHub Pages.

---

A minimal static site to view and share direct links to images for any online game session. Works great for Tower Unite, VRChat, GTA RP servers, D&D maps, clan events, or any place you need a quick image host. Deploy to GitHub Pages and render straight from your `media/` folder.

**Live:** https://M1XZG.github.io/shared-game-images/

## Features
- Paste or deep-link to an image and display it instantly
- Auto-load via query param: `?src=media/your-image.jpg`
- Gallery auto-lists everything in `media/` (fetched via GitHub API)
- Quick actions: open original, copy link, download
- No backend — plain HTML/CSS/JS

## Usage
- Place your images in the `media/` folder (committed to the repo) to serve them via GitHub Pages.
- The viewer only serves local media files. Use relative paths like `?src=media/your-image.jpg`.
- Supported image types: png, jpg, jpeg, gif, webp, avif, bmp.
- The page automatically lists and thumbnails everything in `media/` via the GitHub contents API. Click a thumbnail to view.

> Note: External URLs are intentionally disallowed; keep assets in `media/`.

## Rebranding for your game or group
- Update the page title, meta description, and header blurb in `index.html` to match your community or server.
- Add your own images or logos to `media/` and reference them with `?src=media/your-logo.png`.
- If you fork this repo, adjust the `owner`, `repo`, and `branch` constants in `script.js` so the gallery pulls from your project instead of `M1XZG/shared-game-images`.

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
Just open `index.html` in a browser, or run a simple server. Ensure your images are under `media/`:

```bash
# Python 3
python -m http.server 8080
# Then visit http://localhost:8080/
```
