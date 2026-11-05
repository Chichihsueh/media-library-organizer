import tempfile
import unittest
from pathlib import Path
from scripts.inventory import infer, inventory
from scripts.plan import plan

class TestOrganizer(unittest.TestCase):
    def test_code_part(self):
        self.assertEqual(infer('ABC-123-CD2-1080p.mkv')['work_id'], 'ABC-123')
        self.assertEqual(infer('ABC-123-CD2-1080p.mkv')['part'], 2)
    def test_unknown(self):
        self.assertIsNone(infer('holiday movie.mkv')['work_id'])
    def test_read_only_and_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source'; root.mkdir()
            (root/'ABC-123.mp4').write_bytes(b'123')
            (root/'untitled.mkv').write_bytes(b'456')
            dest=Path(tmp)/'dest'
            data=inventory(root)
            report=plan(data,dest)
            self.assertEqual(report['summary'],{'proposed':1,'skipped':1,'conflict':0})
            self.assertFalse(dest.exists())
            self.assertEqual(len(list(root.iterdir())),2)
            with self.assertRaises(ValueError): plan(data,root/'organized')
    def test_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source'; root.mkdir()
            (root/'ABC-123.mp4').write_bytes(b'abc')
            dest=Path(tmp)/'dest'; (dest/'ABC-123').mkdir(parents=True)
            (dest/'ABC-123'/'ABC-123.mp4').write_bytes(b'other')
            self.assertEqual(plan(inventory(root),dest)['summary']['conflict'],1)

if __name__=='__main__': unittest.main()
