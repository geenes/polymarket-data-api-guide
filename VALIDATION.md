# Polymarket Data API guide validation

Checked September 7, 2026. These checks used public, unauthenticated GET requests. A public wallet/condition ID was selected from a two-row recent-trades sample; it is not asserted to belong to the maintainer. Raw account samples are kept outside the published files.

## Source fingerprint

- Source: https://docs.polymarket.com/api-spec/data-openapi.yaml
- Specification version label: `1.0.0`
- SHA-256 of retrieved bytes: `9d5d62b302bced648b7212e6e8c589a741b258d38bb8769a1cd57c5224ecc1fe`
- Documented routes covered: 20 of 20 paths in that retrieved specification.
- Other sources: official endpoint Markdown pages, API guide, market discovery, wallet/profile documentation, pUSD reference, and rate limits. The README cites relevant pages next to claims.

## Live request results

| Request | Observed result |
| --- | --- |
| Data `/` | HTTP 200; dict; 1 top-level items |
| Data `/trades` | HTTP 200; list; 2 top-level items |
| Data `/positions` | HTTP 200; list; 2 top-level items |
| Data `/closed-positions` | HTTP 200; list; 2 top-level items |
| Data `/activity` | HTTP 200; list; 2 top-level items |
| Data `/holders` | HTTP 200; list; 2 top-level items |
| Data `/value` | HTTP 200; list; 1 top-level items |
| Data `/oi` | HTTP 200; list; 1 top-level items |
| Data `/traded` | HTTP 200; dict; 2 top-level items |
| Data `/v1/market-positions` | HTTP 200; list; 2 top-level items |
| Data `/v1/leaderboard` | HTTP 200; list; 2 top-level items |
| Data `/v1/positions/combos` | HTTP 200; dict; 2 top-level items |
| Data `/v1/activity/combos` | HTTP 200; dict; 2 top-level items |
| Data `/v1/approvals` | HTTP Error 500: Internal Server Error |
| Gamma `/markets` | HTTP 200; list; 1 top-level items |

The populated positions sample included `grossInitialValue`, `entryFeesUsdc`, and an additional `eventId` field. Both combo response objects had empty collections; this checks envelope shape only. The approvals endpoint returned HTTP 500 for this sampled wallet. No successful approvals response was established.

## Example and document checks

- `python3 -m unittest discover -s tests -v`: five tests passed, covering false/zero/CSV query encoding, page advancement, explicit incomplete-result errors, offset caps, and parser utilities.
- `python3 examples/data_api.py`: completed live Gamma discovery and public trade reads.
- `node examples/data-api.mjs`: completed live public trade reads.
- Checked the README's internal links, balanced code fences, single top-level heading outside code blocks, endpoint coverage, and parameter inventory against the retrieved specification.

## Limits of validation

These were tiny samples, not an exhaustive endpoint test suite or a load test. Maximum page sizes and rate ceilings were read from documentation, not stress-tested. No full historical export, populated combo ledger, trading operation, wallet signing, accounting reconciliation, production SLA, browser CORS behavior, or SEO ranking/indexing was verified. Accounting snapshot, builder endpoints, live-volume, revisions, and Other-size behavior were documented from the specification rather than exercised in the initial sample.

## Repeatable review

Run the tests and the two read-only examples. For wallet-specific pagination, run `python3 examples/data_api.py --user "$POLY_WALLET"` with a public address whose scope you understand. Re-fetch the official schema, compare limits/filters and fields, and record a new retrieval hash/date. Preserve historical observations when endpoint behavior changes. Never turn a failed request into a zero metric.
