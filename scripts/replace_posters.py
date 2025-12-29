#!/usr/bin/env python3
import os
import shutil
import hashlib
import random

POSTER_DIR = 'vrc/soft-space/'
POOL_DIR = 'vrc/soft-space/image-pool/p/'
POSTER_FILES = ['poster1.png', 'poster2.png', 'poster3.png']

# Helper to get SHA256 hash of a file
def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    # Get current poster hashes
    current_hashes = set()
    for poster in POSTER_FILES:
        poster_path = os.path.join(POSTER_DIR, poster)
        if os.path.exists(poster_path):
            current_hashes.add(file_sha256(poster_path))

    # Get all pool images and their hashes
    pool_images = []
    pool_hashes = {}
    for fname in os.listdir(POOL_DIR):
        if fname.lower().endswith('.png'):
            fpath = os.path.join(POOL_DIR, fname)
            h = file_sha256(fpath)
            pool_images.append((fname, h))
            pool_hashes[fname] = h

    # Filter out images that match any current poster
    available = [(fname, h) for fname, h in pool_images if h not in current_hashes]
    if len(available) < 3:
        raise Exception('Not enough unique images in pool to replace all posters.')

    # Randomly select 3 unique images
    selected = random.sample(available, 3)

    # Copy to poster files
    for i, (fname, _) in enumerate(selected):
        src = os.path.join(POOL_DIR, fname)
        dst = os.path.join(POSTER_DIR, POSTER_FILES[i])
        shutil.copy2(src, dst)
        print(f'Replaced {POSTER_FILES[i]} with {fname}')

if __name__ == '__main__':
    main()
