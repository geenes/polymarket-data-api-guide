"""Read-only Polymarket examples. Python 3.10+, standard library only."""
import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA_API = 'https://data-api.polymarket.com'
GAMMA_API = 'https://gamma-api.polymarket.com'
PAGE_RULES = {'/positions': (500, 10000), '/closed-positions': (50, 100000),
              '/trades': (10000, 10000), '/activity': (500, 5000)}


def query_string(params):
    def encode(value):
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (list, tuple)):
            return ','.join(encode(item) for item in value)
        return str(value)
    return urlencode({key: encode(value) for key, value in params.items()
                      if value is not None})


def retry_delay(value):
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) -
                            datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


def get_json(path, params=None, *, base=DATA_API, attempts=4, timeout=20):
    """Bounded GET retries; preserve JSON decimal precision on ingestion."""
    url = base + path + ('?' + query_string(params) if params else '')
    for attempt in range(attempts):
        delay = None
        try:
            request = Request(url, headers={'Accept': 'application/json',
                                           'User-Agent': 'PolymarketDataGuide/1.0'})
            with urlopen(request, timeout=timeout) as response:
                return json.load(response, parse_float=Decimal)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            delay = retry_delay(error.headers.get('Retry-After'))
            # A long cooldown needs a scheduler, not an early retry.
            if delay is not None and delay > 60:
                raise RuntimeError(f'Server requested {delay:.0f}s cooldown; reschedule') from error
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        time.sleep(delay if delay is not None else (2 ** attempt + random.random()))
    raise RuntimeError('attempts must be positive')


def fetch_pages(path, params, *, page_size=100, max_pages=20, fetch=get_json):
    """Return one bounded result; raise if completeness cannot be established.

    Snapshot-sensitive live collections can still change during pagination.
    For history, freeze end and split start/end windows at the caller.
    """
    if path not in PAGE_RULES:
        raise ValueError('Use an endpoint-specific pager for this response shape')
    max_size, max_offset = PAGE_RULES[path]
    if not 1 <= page_size <= max_size or max_pages < 1:
        raise ValueError('Invalid page_size or max_pages')
    if 'offset' in params or 'limit' in params:
        raise ValueError('Pager owns offset and limit')
    result = []
    offset = 0
    for _ in range(max_pages):
        if offset > max_offset:
            raise RuntimeError('Offset cap reached; narrow filters or split the time window')
        rows = fetch(path, {**params, 'limit': page_size, 'offset': offset})
        if not isinstance(rows, list):
            raise TypeError('Expected a JSON array')
        result.extend(rows)
        if len(rows) < page_size:
            return result
        offset += len(rows)
        time.sleep(0.2)
    raise RuntimeError('Page budget reached; result is incomplete; narrow the query')


def parse_array(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise TypeError('Expected array or JSON-encoded array')
    return value


def market_example():
    markets = get_json('/markets', {'closed': False, 'limit': 1}, base=GAMMA_API)
    if not markets:
        raise RuntimeError('No market returned')
    market = markets[0]
    outcomes = parse_array(market['outcomes'])
    tokens = parse_array(market['clobTokenIds'])
    if len(tokens) != len(outcomes):
        raise ValueError('Token/outcome mapping has different lengths')
    return {'conditionId': market['conditionId'], 'slug': market['slug'],
            'outcomes': [{'outcome': name, 'tokenId': str(token)}
                         for name, token in zip(outcomes, tokens)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', help='Public profile / position-holding wallet address')
    args = parser.parse_args()
    result = {'market': market_example(),
              'recentTrades': get_json('/trades', {'limit': 2, 'takerOnly': True})}
    if args.user:
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', args.user):
            parser.error('--user must be a 0x-prefixed 40-hex address')
        result['positions'] = fetch_pages('/positions', {'user': args.user,
                                            'sizeThreshold': 0, 'includeArchived': True})
        result['value'] = get_json('/value', {'user': args.user})
    # Decimal values are strings in this CLI output to preserve precision.
    print(json.dumps(result, default=str, indent=2))


if __name__ == '__main__':
    main()
