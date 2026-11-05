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

    def test_dmm_padding_is_normalised(self):
        self.assertEqual(infer('club00502.mp4')['work_id'], 'CLUB-502')
        self.assertEqual(infer('HOMA-00030.mp4')['work_id'], 'HOMA-030')
        self.assertEqual(infer('bdst06701.mp4')['work_id'], 'BDST-6701')
        self.assertEqual(infer('ABC-0007.mp4')['work_id'], 'ABC-0007')

    def test_leading_zeros_kept(self):
        self.assertEqual(infer('abc-007_1080p.mp4')['work_id'], 'ABC-007')

    def test_padded_number_is_not_a_resolution(self):
        self.assertEqual(infer('ssni00360.mp4')['work_id'], 'SSNI-360')

    def test_labelled_formats(self):
        cases = {
            'fc2-911944_hd.mp4': 'FC2-PPV-911944',
            'FC2-PPV-1234567.mp4': 'FC2-PPV-1234567',
            '(Heyzo)(1883)title.mp4': 'HEYZO-1883',
            '020217-365-CARIB-1080p.mp4': 'CARIB-020217-365',
            '011714_749-caribpr-low.wmv': 'CARIBPR-011714-749',
            '111018_767-1pon-1080p.mp4': '1PON-111018-767',
            '200GANA-1765.mp4': '200GANA-1765',
            '300mium_1248_g.mp4': '300MIUM-1248',
            'Caribbeancompr050416_557x.mp4': 'CARIBPR-050416-557',
            'caribbeancom-031516_117.mp4': 'CARIB-031516-117',
        }
        for name, expected in cases.items():
            got = infer(name)
            self.assertEqual(got['work_id'], expected, name)
            self.assertEqual(got['id_confidence'], 'labelled', name)

    def test_unlabelled_dates_and_noise_are_not_codes(self):
        for name in ('122619_226.mp4', '318628-full.mp4', 'x264-100.mp4', 'movie 720p.mp4',
                     'h_172hdm00001pl.mp4'):
            self.assertIsNone(infer(name)['work_id'], name)


class TestInventory(unittest.TestCase):
    def test_legacy_formats_are_inventoried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            for n in ('ABC-123.rmvb', 'ABC-124.rm', 'ABC-125.flv', 'ABC-126.mpg', 'note.txt'):
                (root / n).write_bytes(b'1')
            names = sorted(f['relative_path'] for f in inventory(root)['files'])
            self.assertEqual(names, ['ABC-123.rmvb', 'ABC-124.rm', 'ABC-125.flv', 'ABC-126.mpg'])

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

    def test_labelled_ids_are_planned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; root.mkdir()
            (root / '200GANA-073.mp4').write_bytes(b'1')
            (root / 'fc2-911944_hd.mp4').write_bytes(b'2')
            summary = plan(inventory(root), Path(tmp) / 'dest')['summary']
            self.assertEqual(summary, {'proposed': 2, 'skipped': 0, 'conflict': 0})

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
