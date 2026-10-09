#!/usr/bin/env python3
"""Compress still PNGs to a byte ceiling, saving originals as filename.png.bak."""

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from PIL import Image, ImageOps


REPO = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO / "image-pool" / "portrait"
MAX_INPUT_BYTES = 100 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Image exceeds the 100 MiB input limit")
    with Image.open(BytesIO(data)) as image:
        if image.format != "PNG" or image.n_frames != 1:
            raise ValueError("Only still PNG images are supported")
        if max(image.size) > 16384 or image.width * image.height > 60_000_000:
            raise ValueError("Image exceeds the dimension limit")
        image.verify()
    with Image.open(BytesIO(data)) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert("RGBA")


def compress(data, target, pngquant):
    original = decode(data)
    if len(data) <= target:
        return data, original.size, False
    scale = 1.0
    for _ in range(40):
        size = tuple(max(1, round(side * scale)) for side in original.size)
        rendered = original.resize(size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        rendered.save(buffer, format="PNG", compress_level=1)
        encoded = subprocess.run(
            [pngquant, "--quality=85-100", "--speed=3", "--output", "-", "-"],
            input=buffer.getvalue(), capture_output=True, timeout=180, check=False,
        )
        if encoded.returncode not in (0, 99):
            raise RuntimeError(
                f"pngquant exited {encoded.returncode}: "
                + encoded.stderr.decode("utf-8", errors="replace").strip()
            )
        if encoded.returncode == 0:
            result = encoded.stdout
            checked = decode(result)
            if checked.size != size:
                raise RuntimeError("Encoder returned unexpected dimensions")
            if len(result) <= target:
                if original.getchannel("A").getextrema() == (255, 255):
                    if checked.getchannel("A").getextrema() != (255, 255):
                        raise RuntimeError("Compression introduced transparency")
                return result, size, size != original.size
            factor = min(0.9, max(0.35, math.sqrt(target / len(result)) * 0.97))
        else:
            # Rejecting the palette is not permission to lower colour quality.
            factor = 0.85
        if size == (1, 1):
            break
        scale *= factor
    raise RuntimeError("Cannot meet the size limit at the required palette quality")


def scan(path):
    if path.is_symlink():
        raise ValueError("Symbolic-link inputs are not supported")
    if path.is_file():
        if path.suffix.lower() != ".png":
            raise ValueError("Input must be a PNG or a folder containing PNGs")
        return [path], []
    if not path.is_dir():
        raise ValueError(f"Input does not exist: {path}")
    files, excluded = [], []
    for candidate in sorted(path.iterdir()):
        if candidate.is_symlink() or not candidate.is_file() or candidate.suffix.lower() != ".png":
            excluded.append(candidate.name)
        else:
            files.append(candidate)
    if not files:
        raise ValueError("No PNGs found (subfolders and symbolic links are excluded)")
    return files, excluded


def backup_originals(files, folder):
    for source in files:
        backup = source.with_name(source.name + ".bak")
        if backup.exists() or backup.is_symlink():
            raise FileExistsError(f"Backup already exists; it will not be overwritten: {backup}")
    records = []
    for source in files:
        if source.is_symlink():
            raise ValueError(f"Source became a symbolic link: {source}")
        if source.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(f"Image exceeds the 100 MiB input limit: {source}")
        before = source.read_bytes()
        destination = source.with_name(source.name + ".bak")
        with destination.open("xb") as stream:
            stream.write(before)
        if destination.read_bytes() != before or source.read_bytes() != before:
            raise RuntimeError(f"Backup verification failed: {source}")
        records.append({"input": str(source), "backup": str(destination),
                        "bytes": len(before), "sha256": digest(before)})
    (folder / "originals.json").write_text(json.dumps(records, indent=2) + "\n")
    return records


def replace_verified(source, data, expected_hash):
    if source.is_symlink() or digest(source.read_bytes()) != expected_hash:
        raise RuntimeError(f"Source changed since backup: {source}")
    fd, name = tempfile.mkstemp(prefix=f".{source.name}.", suffix=".pending", dir=source.parent)
    pending = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        shutil.copymode(source, pending)
        if pending.read_bytes() != data:
            raise RuntimeError(f"Replacement write failed: {source}")
        if source.is_symlink() or digest(source.read_bytes()) != expected_hash:
            raise RuntimeError(f"Source changed before replacement: {source}")
        os.replace(pending, source)
    finally:
        pending.unlink(missing_ok=True)


def run(args):
    files, excluded = scan(args.input)
    pngquant = shutil.which(args.pngquant)
    if not pngquant:
        raise ValueError("pngquant is missing. Install it or supply --pngquant /path/to/pngquant")
    subprocess.run([pngquant, "--version"], capture_output=True, check=True, timeout=10)
    target = args.kb * 1000
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    replace = args.replace or (args.input.is_file() and args.output is None)
    if replace:
        job = REPO.parent / f"{REPO.name}-backups" / f"png-compression-{stamp}"
        job.mkdir(parents=True, exist_ok=False)
        output = job / "compressed"
    else:
        output = args.output or (
            REPO.parent / f"{REPO.name}-compressed" / f"{args.kb}kb-{stamp}"
        )
    output.mkdir(parents=True, exist_ok=False)
    originals = backup_originals(files, output)
    report = {"target_bytes": target, "replace": replace, "output": str(output),
              "backups": [record["backup"] for record in originals],
              "excluded": excluded, "files": []}
    report_path = output / "compression-report.json"
    failures = 0
    for index, source in enumerate(files):
        record = {"input": str(source), "state": "failed"}
        try:
            if source.is_symlink():
                raise ValueError("Source became a symbolic link")
            if source.stat().st_size > MAX_INPUT_BYTES:
                raise ValueError("Image exceeds the 100 MiB input limit")
            original = originals[index]
            data = Path(original["backup"]).read_bytes()
            if digest(data) != original["sha256"]:
                raise RuntimeError("Original backup changed after verification")
            result, size, resized = compress(data, target, pngquant)
            destination = output / source.name
            with destination.open("xb") as stream:
                stream.write(result)
            written = destination.read_bytes()
            decode(written)
            if written != result or len(written) > target:
                raise RuntimeError("Output failed verification")
            if replace and result != data:
                replace_verified(source, result, original["sha256"])
                if source.read_bytes() != result:
                    raise RuntimeError("Replaced file failed verification")
            record.update(state="done", output=str(destination), input_bytes=len(data),
                          output_bytes=len(result), output_sha256=digest(result),
                          dimensions=list(size), resized=resized, unchanged=result == data)
            print(f"{source.name}: {len(data):,} -> {len(result):,} bytes "
                  f"({size[0]}x{size[1]})", flush=True)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            failures += 1
            record["error"] = f"{type(error).__name__}: {error}"
            print(f"FAILED {source.name}: {record['error']}", file=sys.stderr, flush=True)
        report["files"].append(record)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Done: {len(files) - failures}; failed: {failures}; excluded: {len(excluded)}")
    print("Verified originals backups: each input filename + .bak")
    print(f"Report: {report_path}")
    return 2 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT,
                        help="PNG (replaced by default) or folder; defaults to image-pool/portrait")
    parser.add_argument("--kb", type=int, default=500, help="Maximum decimal KB (default: 500)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_true",
                      help="Replace folder inputs after verifying adjacent .bak copies")
    mode.add_argument("--output", type=Path, help="New folder for copies (must not exist)")
    parser.add_argument("--pngquant", default="pngquant", help="Encoder name or executable path")
    args = parser.parse_args()
    if not 1 <= args.kb <= 100_000:
        parser.error("--kb must be between 1 and 100000")
    args.input = args.input.absolute()
    try:
        return run(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
