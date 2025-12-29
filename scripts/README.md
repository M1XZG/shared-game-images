# replace_posters.py

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
