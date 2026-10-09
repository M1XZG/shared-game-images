# Image utilities

## compress_images.py

To compress one image in place from your Linux/WSL terminal:

```bash
python3 scripts/compress_images.py "/path/to/photo.png"
```

This first saves and verifies `photo.png.bak` beside the original, then
replaces `photo.png` with a PNG of at most **500,000 bytes**. The repository's
`.gitignore` excludes `*.bak` files. Existing backups are never overwritten;
move an old backup to an archive location before processing that file again.

To process the portrait pool in place, run from the repository:

```bash
python3 scripts/compress_images.py --replace
```

Before changing any input, this copies and verifies all selected PNGs to
adjacent `.bak` files. PNG filenames stay the same. The script does not commit,
push or rotate posters.

For folder inputs without `--replace`, it leaves the PNGs untouched and writes
compressed copies to a new dated folder under `../shared-game-images-compressed/`.
The `.bak` copies are still created. `--output` also selects copy mode for a
single file. Other examples:

```bash
python3 scripts/compress_images.py "/path/to/photos" --replace
python3 scripts/compress_images.py "/path/to/photo.png" --output "/path/to/new-output"
python3 scripts/compress_images.py --kb 300
```

Existing output folders are never overwritten. Only still PNGs are supported;
subfolders, symbolic links and other extensions are excluded. Damaged or
animated PNGs are reported as failures, and subsequent photos are still
attempted. Exit codes are 0 for success, 2 for per-image failures, and 1 for
setup or backup errors. Every run writes `compression-report.json`.

Images already within the limit retain their exact bytes. Larger images use
pngquant with a minimum palette quality of 85 and proportional Lanczos
downscaling when needed. This is lossy compression, not a promise of original
pixel dimensions or colour-profile/metadata preservation. Transparency is
retained rather than filled with a background.

`originals.json` beside the compression report records each source, `.bak`
path and SHA-256 hash. To undo a replacement, copy `photo.png.bak` back over
`photo.png`. Reports and staged compressed copies remain outside the repository
unless you explicitly choose an output folder inside it.

Dependencies are Python 3.10+, Pillow and the `pngquant` executable on PATH.
They are available on this PC in Linux/WSL. For another machine:

```bash
python3 -m pip install -r scripts/requirements.txt
sudo apt install pngquant
```

Use `--pngquant /path/to/pngquant` if the executable is elsewhere. Offline tests:

```bash
TMPDIR="$HOME/copilot-sessions/tmp" python3 -m unittest discover -s scripts -p 'test_compress_images.py'
```

## replace_posters.py

This script automates the replacement of poster images for a set of VRChat worlds, ensuring that each poster is updated with a new image from a pool and that no poster receives the same image as before (when possible).

## Flow and Logic

1. **Setup and Configuration**
   - The script sets up Git user configuration and authentication if required.
   - It reads the list of world names from `world-list.txt`.
   - It loads all available images from the `image-pool/portrait/` directory, computing their SHA256 hashes for uniqueness checks.

2. **Processing Each World**
   - For each world listed:
     - The script locates the corresponding world directory under `vrc/`.
     - It identifies all poster files (e.g., `poster1.png`, `poster2.png`, etc.).
     - It computes the current hash of each poster image.

3. **Selecting New Images**
   - For each poster file:
     - The script selects a new image from the pool that:
       - Has not already been used for another poster in the same world.
       - Is not the same as the previous image for that poster (when possible).
     - If there are not enough unique images, it warns and may reuse an old image as a fallback.

4. **Replacing Posters**
   - The script copies the selected images to replace the existing poster files, printing debug information before and after each operation.
   - If any posters were changed, it commits the changes to Git for that world.

5. **Finalization**
   - After all worlds are processed, the script pushes all changes to the remote repository.

## Notes
- The script ensures no duplicate images within a world and tries to avoid reusing the same image for a poster.
- It provides debug output for traceability and error handling.
- The script is intended to be run from the repository root.
