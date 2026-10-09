from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, StringIO
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import compress_images as compressor


class CompressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.input = self.repo / "photos"
        self.input.mkdir()
        self.pngquant = shutil.which("pngquant")
        self.assertIsNotNone(self.pngquant, "Install pngquant to run the native tests")
        patcher = patch.object(compressor, "REPO", self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

    def png(self, name="photo.png"):
        path = self.input / name
        Image.new("RGBA", (32, 64), (150, 50, 20, 120)).save(path)
        return path

    def run_script(self, **kwargs):
        args = Namespace(input=self.input, kb=500, replace=False,
                         output=self.root / "output", pngquant=self.pngquant)
        for key, value in kwargs.items():
            setattr(args, key, value)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return compressor.run(args)

    def test_passthrough_preserves_exact_bytes_and_transparency(self):
        source = self.png()
        data = source.read_bytes()
        result, size, resized = compressor.compress(data, 500000, self.pngquant)
        self.assertEqual(result, data)
        self.assertEqual(size, (32, 64))
        self.assertFalse(resized)

    def test_native_compression_meets_ceiling(self):
        rng = random.Random(42)
        image = Image.frombytes("RGB", (512, 1024), rng.randbytes(512 * 1024 * 3))
        data = BytesIO()
        image.save(data, format="PNG")
        result, size, _ = compressor.compress(data.getvalue(), 500000, self.pngquant)
        self.assertLessEqual(len(result), 500000)
        self.assertEqual(compressor.decode(result).size, size)
        self.assertLessEqual(size[0], 512)
        low = max((size[0] - .5) / 512, (size[1] - .5) / 1024)
        high = min((size[0] + .5) / 512, (size[1] + .5) / 1024)
        self.assertLessEqual(low, high)

    def test_native_reencoding_retains_transparency(self):
        rng = random.Random(7)
        image = Image.frombytes("RGB", (256, 512), rng.randbytes(256 * 512 * 3)).convert("RGBA")
        image.paste((0, 0, 0, 0), (0, 0, 100, 512))
        data = BytesIO()
        image.save(data, format="PNG")
        self.assertGreater(len(data.getvalue()), 100000)
        result, _, _ = compressor.compress(data.getvalue(), 100000, self.pngquant)
        self.assertLessEqual(len(result), 100000)
        self.assertEqual(compressor.decode(result).getchannel("A").getextrema(), (0, 255))

    def test_copy_mode_leaves_input_unchanged(self):
        source = self.png()
        data = source.read_bytes()
        self.assertEqual(self.run_script(), 0)
        self.assertEqual(source.read_bytes(), data)
        self.assertEqual((self.root / "output" / source.name).read_bytes(), data)

    def test_output_collision_leaves_existing_files_untouched(self):
        self.png()
        output = self.root / "output"
        output.mkdir()
        marker = output / "marker"
        marker.write_text("keep")
        with self.assertRaises(FileExistsError):
            self.run_script()
        self.assertEqual(marker.read_text(), "keep")

    def test_replace_verifies_backup_before_changing_input(self):
        source = self.png()
        original = source.read_bytes()
        data = BytesIO()
        Image.new("RGBA", (16, 32), (10, 20, 30, 120)).save(data, format="PNG")
        with patch.object(compressor, "compress", return_value=(data.getvalue(), (16, 32), True)):
            self.assertEqual(self.run_script(replace=True, output=None), 0)
        jobs = list((self.root / "repo-backups").iterdir())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(source.with_name(source.name + ".bak").read_bytes(), original)
        manifest = json.loads((jobs[0] / "compressed" / "originals.json").read_text())
        self.assertEqual(manifest[0]["sha256"], compressor.digest(original))
        self.assertEqual(source.read_bytes(), data.getvalue())

    def test_single_file_defaults_to_replacement_with_adjacent_backup(self):
        source = self.png()
        original = source.read_bytes()
        data = BytesIO()
        Image.new("RGBA", (16, 32), (10, 20, 30, 120)).save(data, format="PNG")
        with patch.object(compressor, "compress", return_value=(data.getvalue(), (16, 32), True)):
            self.assertEqual(self.run_script(input=source, output=None), 0)
        self.assertEqual(source.with_name(source.name + ".bak").read_bytes(), original)
        self.assertEqual(source.read_bytes(), data.getvalue())

    def test_backup_collision_does_not_overwrite_backup_or_any_source(self):
        source = self.png()
        second = self.png("second.png")
        original = source.read_bytes()
        backup = second.with_name(second.name + ".bak")
        backup.write_bytes(b"older original")
        with self.assertRaisesRegex(FileExistsError, "will not be overwritten"):
            self.run_script(replace=True, output=None)
        self.assertEqual(backup.read_bytes(), b"older original")
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse(source.with_name(source.name + ".bak").exists())

    def test_dangling_backup_symlink_is_not_followed(self):
        source = self.png()
        backup = source.with_name(source.name + ".bak")
        backup.symlink_to(self.root / "nonexistent")
        with self.assertRaises(FileExistsError):
            self.run_script()
        self.assertFalse((self.root / "nonexistent").exists())

    def test_changed_source_is_not_overwritten(self):
        source = self.png()
        old_hash = compressor.digest(source.read_bytes())
        source.write_bytes(b"new data")
        with self.assertRaisesRegex(RuntimeError, "changed since backup"):
            compressor.replace_verified(source, b"replacement", old_hash)
        self.assertEqual(source.read_bytes(), b"new data")

    def test_bad_image_does_not_block_next_photo(self):
        (self.input / "a-bad.png").write_bytes(b"broken")
        self.png("z-good.png")
        self.assertEqual(self.run_script(), 2)
        report = json.loads((self.root / "output" / "compression-report.json").read_text())
        self.assertEqual([row["state"] for row in report["files"]], ["failed", "done"])

    def test_animated_png_is_rejected(self):
        first = Image.new("RGB", (16, 16), "red")
        data = BytesIO()
        first.save(data, format="PNG", save_all=True,
                   append_images=[Image.new("RGB", (16, 16), "blue")])
        with self.assertRaisesRegex(ValueError, "still PNG"):
            compressor.decode(data.getvalue())

    def test_symlinks_and_subfolders_are_excluded(self):
        source = self.png()
        (self.input / "link.png").symlink_to(source)
        (self.input / "nested").mkdir()
        files, excluded = compressor.scan(self.input)
        self.assertEqual(files, [source])
        self.assertEqual(set(excluded), {"link.png", "nested"})

    def test_backup_failure_prevents_any_replacements(self):
        source = self.png()
        original = source.read_bytes()
        with patch.object(compressor, "backup_originals", side_effect=RuntimeError("backup failed")):
            with self.assertRaisesRegex(RuntimeError, "backup failed"):
                self.run_script(replace=True, output=None)
        self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
