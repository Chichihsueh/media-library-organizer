import tempfile
import unittest
from pathlib import Path
from scripts.inventory import infer, inventory
from scripts.plan import plan


class TestInfer(unittest.TestCase):
    def test_code_part(self):
        self.assertEqual(infer('ABC-123-CD2-1080p.mkv')['work_id'], 'ABC-123')
        self.assertEqual(infer('ABC-123-CD2-1080p.mkv')['part'], 2)

    def test_unknown(self):
        self.assertIsNone(infer('holiday movie.mkv')['work_id'])

    def test_resolution_is_not_a_code(self):
        self.assertIsNone(infer('ABC 1080p.mp4')['work_id'])
        self.assertIsNone(infer('ABC 720.mkv')['work_id'])
        self.assertEqual(infer('ABC-1080.mp4')['work_id'], 'ABC-1080')

    def test_camera_names_are_not_codes(self):
        for name in ('IMG_0045.mp4', 'DSC_0012.mov', 'PXL_20230101.mp4'):
            self.assertIsNone(infer(name)['work_id'], name)

    def test_edition_clues(self):
        self.assertEqual(infer('ABC-123_480p.mp4')['edition_clues'], ['480P'])
        self.assertEqual(infer('abc-123.4k.x265.mkv')['edition_clues'], ['4K', 'X265'])

    def test_leading_zeros_kept(self):
        self.assertEqual(infer('abc-007_1080p.mp4')['work_id'], 'ABC-007')


class TestInventory(unittest.TestCase):
    def test_skips_sidecars_and_nas_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            (root / 'ABC-123.mp4').write_bytes(b'1')
            (root / '._ABC-123.mp4').write_bytes(b'meta')
            (root / '@eaDir').mkdir(); (root / '@eaDir' / 'ABC-999.mp4').write_bytes(b'x')
            (root / '#recycle').mkdir(); (root / '#recycle' / 'ABC-888.mp4').write_bytes(b'x')
            names = [f['relative_path'] for f in inventory(root)['files']]
            self.assertEqual(names, ['ABC-123.mp4'])


class TestPlan(unittest.TestCase):
    def test_read_only_and_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            (root / 'ABC-123.mp4').write_bytes(b'123')
            (root / 'untitled.mkv').write_bytes(b'456')
            dest = Path(tmp) / 'dest'
            data = inventory(root)
            report = plan(data, dest)
            self.assertEqual(report['summary'], {'proposed': 1, 'skipped': 1, 'conflict': 0})
            self.assertFalse(dest.exists())
            self.assertEqual(len(list(root.iterdir())), 2)
            with self.assertRaises(ValueError): plan(data, root / 'organized')
            with self.assertRaises(ValueError): plan(data, root.parent)

    def test_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            (root / 'ABC-123.mp4').write_bytes(b'abc')
            dest = Path(tmp) / 'dest'; (dest / 'ABC-123').mkdir(parents=True)
            (dest / 'ABC-123' / 'ABC-123.mp4').write_bytes(b'other')
            self.assertEqual(plan(inventory(root), dest)['summary']['conflict'], 1)

    def test_same_name_in_two_folders_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'
            for d in ('a', 'b'):
                (root / d).mkdir(parents=True)
                (root / d / 'ABC-123.mp4').write_bytes(d.encode())
            summary = plan(inventory(root), Path(tmp) / 'dest')['summary']
            self.assertEqual(summary, {'proposed': 1, 'skipped': 0, 'conflict': 1})

    def test_source_changed_after_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            f = root / 'ABC-123.mp4'; f.write_bytes(b'abc')
            data = inventory(root)
            f.write_bytes(b'abcdef')  # modified after the scan
            report = plan(data, Path(tmp) / 'dest')
            self.assertEqual(report['summary']['conflict'], 1)
            self.assertIn('changed', report['changes'][0]['reason'])

    def test_review_groups_flag_versions_not_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            (root / 'ABC-123_720p.mp4').write_bytes(b'1')
            (root / 'ABC-123_1080p.mp4').write_bytes(b'22')
            (root / 'XYZ-001-CD1.mkv').write_bytes(b'3')
            (root / 'XYZ-001-CD2.mkv').write_bytes(b'4')
            groups = {g['work_id']: g for g in plan(inventory(root), Path(tmp) / 'd')['review_groups']}
            self.assertIn('do not delete', groups['ABC-123']['reason'])
            self.assertEqual(groups['XYZ-001']['reason'], 'multi-part set')
            self.assertEqual(groups['XYZ-001']['parts'], [1, 2])


if __name__ == '__main__': unittest.main()
