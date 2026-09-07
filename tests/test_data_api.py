import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from data_api import fetch_pages, query_string, retry_delay, parse_array


class ClientTests(unittest.TestCase):
    def test_query_preserves_zero_false_and_csv(self):
        self.assertEqual(parse_qs(query_string({'user': None, 'sizeThreshold': 0,
                          'takerOnly': False, 'market': ['a', 'b']})),
                         {'sizeThreshold': ['0'], 'takerOnly': ['false'], 'market': ['a,b']})

    @patch('data_api.time.sleep')
    def test_pages_advance_and_stop_on_short_page(self, _):
        calls = []
        def fetch(path, params):
            calls.append(params['offset'])
            return [1, 2] if params['offset'] == 0 else [3]
        self.assertEqual(fetch_pages('/positions', {}, page_size=2, fetch=fetch), [1, 2, 3])
        self.assertEqual(calls, [0, 2])

    @patch('data_api.time.sleep')
    def test_budget_does_not_silently_return_partial_history(self, _):
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            fetch_pages('/positions', {}, page_size=1, max_pages=2,
                        fetch=lambda *_: [1])

    @patch('data_api.time.sleep')
    def test_offset_cap_never_sends_an_invalid_request(self, _):
        offsets = []
        def fetch(path, params):
            offsets.append(params['offset'])
            return [1] * params['limit']
        with self.assertRaisesRegex(RuntimeError, 'Offset cap'):
            fetch_pages('/activity', {}, page_size=500, max_pages=20, fetch=fetch)
        self.assertEqual(max(offsets), 5000)

    def test_retry_and_gamma_formats(self):
        self.assertEqual(retry_delay('12'), 12)
        self.assertIsNone(retry_delay('invalid'))
        self.assertEqual(parse_array('["Yes","No"]'), ['Yes', 'No'])
        self.assertEqual(parse_array(['Yes']), ['Yes'])


if __name__ == '__main__':
    unittest.main()
