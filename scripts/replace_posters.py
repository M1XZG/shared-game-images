
#!/usr/bin/env python3
"""
replace_posters.py

Automates the replacement of poster images for VRChat worlds.
For each world listed in world-list.txt, replaces poster images in vrc/<world>/
with new images from image-pool/portrait/, ensuring:
    - No duplicate images within a world
    - No poster receives the same image as before (when possible)
    - All changes are committed and pushed to Git

Run this script from the repository root.
"""

import os
import shutil
import hashlib
import random
import subprocess
import sys

WORLD_LIST_FILE = 'world-list.txt'
POOL_DIR = 'image-pool/portrait/'


def file_sha256(path):
    """
    Compute the SHA256 hash of a file.
    Args:
        path (str): Path to the file.
    Returns:
        str: SHA256 hex digest of the file contents.
    """
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def get_worlds():
    """
    Read the list of world names from WORLD_LIST_FILE.
    Returns:
        list[str]: List of world names.
    """
    with open(WORLD_LIST_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def get_poster_files(world_dir):
    """
    Get all poster image filenames in a world directory, sorted by number.
    Only matches files like poster1.png, poster2.png, etc.
    Args:
        world_dir (str): Path to the world directory.
    Returns:
        list[str]: Sorted list of poster filenames.
    """
    posters = []
    for fname in os.listdir(world_dir):
        if fname.startswith('poster') and fname.endswith('.png') and fname[6:-4].isdigit():
            posters.append(fname)
    posters.sort(key=lambda x: int(x[6:-4]))
    return posters


def git_run(args, check=True):
    """
    Run a git command and print its output.
    Args:
        args (list[str]): Git command arguments.
        check (bool): Raise error if command fails.
    Returns:
        subprocess.CompletedProcess: Result of the git command.
    """
    print(f"[GIT] {' '.join(args)}")
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(args)}")
    return result


def setup_git():
    """
    Configure git user and remote for automated commits and pushes.
    Uses environment variables for author info and GitHub token if available.
    """
    user_name = os.environ.get("GIT_AUTHOR_NAME", "Poster Bot")
    user_email = os.environ.get("GIT_AUTHOR_EMAIL", "poster-bot@example.com")
    git_run(["config", "user.name", user_name])
    git_run(["config", "user.email", user_email])
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            # Try to get from origin url
            result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
            repo_url = result.stdout.strip().split(":")[-1].replace(".git","")
            repo = repo_url
        remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
        git_run(["remote", "set-url", "origin", remote_url])

def main():
    """
    Main entry point: replaces poster images for each world with new images from the pool.
    Ensures no duplicates within a world and avoids reusing the same image for a poster (when possible).
    Commits and pushes changes to Git.
    """
    setup_git()
    worlds = get_worlds()
    pool_images = []
    pool_hashes = {}
    for fname in os.listdir(POOL_DIR):
        if fname.lower().endswith('.png'):
            fpath = os.path.join(POOL_DIR, fname)
            h = file_sha256(fpath)
            pool_images.append((fname, h))
            pool_hashes[fname] = h

    for world in worlds:
        poster_dir = os.path.join('vrc', world)
        if not os.path.isdir(poster_dir):
            print(f"World directory not found: {poster_dir}")
            continue
        poster_files = get_poster_files(poster_dir)
        if not poster_files:
            print(f"No poster files found in {poster_dir}")
            continue

        # Only ensure no duplicates within this world and not same as previous image
        used_hashes = set()
        selected = []
        available = pool_images[:]
        random.shuffle(available)

        # Get current hashes for each poster file
        current_hashes = []
        for pf in poster_files:
            pf_path = os.path.join(poster_dir, pf)
            if os.path.exists(pf_path):
                current_hashes.append(file_sha256(pf_path))
            else:
                current_hashes.append(None)

        # For each poster, pick a pool image that is not the same as the current one and not already used in this world
        for idx, prev_hash in enumerate(current_hashes):
            found = False
            for fname, h in available:
                if h not in used_hashes and h != prev_hash:
                    selected.append((fname, h))
                    used_hashes.add(h)
                    found = True
                    break
            if not found:
                print(f"[WARNING] Not enough unique images in pool to replace poster {poster_files[idx]} for {world} (may repeat old image)")
                # fallback: allow using an image even if it's the same as before, but not already used in this world
                for fname, h in available:
                    if h not in used_hashes:
                        selected.append((fname, h))
                        used_hashes.add(h)
                        found = True
                        break
            if not found:
                print(f"[ERROR] Not enough unique images in pool to replace all posters for {world}.")
                break

        if len(selected) < len(poster_files):
            print(f"Not enough unique images in pool to replace all posters for {world}.")
            continue

        # Copy to poster files with debug output and force overwrite
        changed = False
        for i, (fname, _) in enumerate(selected):
            src = os.path.join(POOL_DIR, fname)
            dst = os.path.join(poster_dir, poster_files[i])
            print(f"[DEBUG] Attempting to copy from {src} to {dst}")
            if not os.path.exists(src):
                print(f"[ERROR] Source image does not exist: {src}")
                continue
            if not os.path.exists(poster_dir):
                print(f"[ERROR] Destination directory does not exist: {poster_dir}")
                continue
            # Print hash and mtime before
            if os.path.exists(dst):
                before_hash = file_sha256(dst)
                before_mtime = os.path.getmtime(dst)
                print(f"[DEBUG] Before: {dst} hash={before_hash} mtime={before_mtime}")
                try:
                    os.remove(dst)
                    print(f"[DEBUG] Removed existing file {dst}")
                except Exception as e:
                    print(f"[ERROR] Could not remove {dst}: {e}")
            else:
                print(f"[DEBUG] {dst} does not exist before copy")
            try:
                shutil.copy2(src, dst)
                after_hash = file_sha256(dst)
                after_mtime = os.path.getmtime(dst)
                print(f"[DEBUG] After: {dst} hash={after_hash} mtime={after_mtime}")
                print(f"[{world}] Replaced {poster_files[i]} with {fname}")
                changed = True
            except Exception as e:
                print(f"[ERROR] Failed to copy {src} to {dst}: {e}")
        # Commit after each world if any changes
        if changed:
            git_run(["add", os.path.join(poster_dir, "poster*.png")])
            git_run(["commit", "-m", f"Automated poster replacement for {world}"])

    # Push once at the end
    git_run(["push"])


if __name__ == '__main__':
    main()
