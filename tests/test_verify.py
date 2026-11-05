import unittest
from scripts.verify import classify, verify, fetch_json


class TestVerify(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify('ABC-123', 200, {'dvd_id': 'abc-123', 'content_id': 'x'})['status'], 'id_match')
        self.assertEqual(classify('ABC-123', 200, {'dvd_id': 'ABC-124'})['status'], 'mismatch')
        self.assertEqual(classify('ABC-123', 404, None)['status'], 'not_found')
        self.assertEqual(classify('ABC-123', 503, None)['status'], 'error')

    def test_classify_via_content_id(self):
        self.assertEqual(classify('AMA-027', 200, {'content_id': '118ama00027'})['status'], 'id_match')
        self.assertEqual(classify('AMA-027', 200, {'content_id': '118ama00028'})['status'], 'mismatch')
        self.assertEqual(classify('ABC-123', 200, {'content_id': 'h_068abc00123'})['status'], 'id_match')
        self.assertEqual(classify('ASKD-007', 200, {'content_id': 'h_1329askd00007'})['status'], 'id_match')
        self.assertEqual(classify('DANDY-911', 200, {'content_id': '1dandy911r'})['status'], 'id_match')
        self.assertEqual(classify('ABC-123', 200, {'content_id': 'weird content id'})['status'], 'unconfirmed')

    def test_only_valid_ids_are_sent_and_cached(self):
        calls, cache = [], {}
        def fake(i):
            calls.append(i); return 200, {'dvd_id': i}
        res, sent = verify(['ABC-123', 'bad id/../x', 'ABC-123'], fetch=fake, cache=cache, sleep=lambda s: None)
        self.assertEqual(calls, ['ABC-123'])
        self.assertEqual(res['bad id/../x']['status'], 'skipped')
        self.assertIn('ABC-123', cache)
        res2, sent2 = verify(['ABC-123'], fetch=fake, cache=cache, sleep=lambda s: None)
        self.assertEqual(sent2, 0); self.assertTrue(res2['ABC-123']['from_cache'])

    def test_limit_and_rate_limit_fail_closed(self):
        res, sent = verify(['AAA-111', 'BBB-222', 'CCC-333'], fetch=lambda i: (200, {'dvd_id': i}),
                           limit=2, sleep=lambda s: None)
        self.assertEqual(sent, 2); self.assertEqual(res['CCC-333']['detail'], 'request limit reached')
        res, sent = verify(['AAA-111', 'BBB-222'], fetch=lambda i: (429, None), sleep=lambda s: None)
        self.assertEqual(sent, 1); self.assertNotIn('BBB-222', res)

    def test_progress_callback_every_50(self):
        ticks = []
        ids = [f'AAA-{i:03d}' for i in range(100, 160)]
        verify(ids, fetch=lambda i: (200, {'dvd_id': i}), limit=60, sleep=lambda s: None,
               on_progress=lambda sent, total: ticks.append(sent))
        self.assertEqual(ticks, [50])

    def test_fetch_refuses_unvalidated_id(self):
        with self.assertRaises(ValueError): fetch_json('../etc/passwd')


if __name__ == '__main__': unittest.main()
