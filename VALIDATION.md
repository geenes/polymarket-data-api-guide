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

## V2 / V3 and unified SDK revision — September 7, 2026

The first edition omitted official Exchange V3/PolyV2 support and the newer unified SDKs. This revision adds those distinctions, current package/runtime pins, official source links, and executable SDK examples while preserving the 20-route Data API reference.

### Installed packages and source evidence

| Package | Version checked | Runtime requirement |
| --- | --- | --- |
| `@polymarket/client` | 0.9.0 | Node >=24 |
| `polymarket-client` | 0.9.0 | Python >=3.11 |
| `@polymarket/clob-client-v2` | 1.1.0 | Node >=20.10 |
| `py-clob-client-v2` | 1.1.0 | Python >=3.9.10 |
| `polymarket_client_sdk_v2` | 0.7.0 | Rust >=1.88.0 |

The unified TypeScript and Python packages were installed and exercised. Older V2 package metadata and Rust manifests were inspected; their runtimes were not installed or tested. The local SDK tests ran on Node 26.8.1 and Python 3.12.14. The JavaScript example commits an npm dependency lock; Python pins the direct SDK dependency and allows its transitive dependencies to resolve during installation.

Official sources included the SDK changelog, both migration guides, package registries, official repository manifests, and the published Python order builder, protocol decoder, models, and environment configuration. Code inspection established domain `2`/`3` selection, the V3 exchange address, separate CTF/PolyV2 IDs, and 31/32-byte neutral condition input handling. No signatures were produced and no secure clients were constructed.

### Additional public live checks

| Check | Observation |
| --- | --- |
| TypeScript `listMarkets`, `listTrades` | Success; two markets and two trades parsed through 0.9.0 |
| Python `list_markets`, `list_trades` | Success; two markets and two trades parsed through 0.9.0 |
| TypeScript `fetchOrderBook({assetId})` | Success; sampled CTF asset returned 34 bid levels and 127 ask levels |
| Python `get_order_book(asset_id=...)` | Success for the same asset and observed book counts |
| Gamma `/markets/keyset?closed=false&limit=2` | HTTP 200; object with `markets`, `next_cursor`, and `$schema` |
| Raw HTTP Python and JavaScript examples | Both completed after the identifier-mapping update |

A sampled market had protocol `v1`, Combo status `pending`, and both decimal CTF token IDs and mapped PolyV2 position IDs. This supports preserving both mappings, not choosing the mapped position automatically. Small recent-market samples also returned `v1` markets with null position IDs. No populated live `v2` portfolio or successful V3 book/order execution was established.

Observed trade normalization: raw seconds became TypeScript milliseconds and Python timezone-aware datetimes; numeric size/price fields became decimal strings in TypeScript and `Decimal` in Python. Python's public approval reader takes `wallet=...`, while TypeScript takes `{user: ...}`. Python 0.9.0 `list_positions` lacks an `includeArchived` argument. The guide records the corresponding direct-HTTP alternative.

### Checks and limits

Seven unit tests pass, including mixed-protocol mapping preservation, mismatched array rejection, refusal to coerce numeric asset IDs, and the original bounded pagination checks. All Markdown Python blocks parse; JavaScript blocks pass `node --check`; shell blocks pass `bash -n`. The guide has one H1, balanced fences, working internal anchors, and all 20 Data API route headings. Newly cited Python SDK source URLs were fetched successfully from the official repository.

The public book and market checks do not validate order signing, approval transactions, settlement, Combo RFQ execution, populated combo accounting, a complete catalogue, or complete historical exports. V3 support is documented from official code and release evidence, not live trading. Prior endpoint failures above remain part of the record; this revision does not claim they are fixed.

### Revised source fingerprints

- `api-spec__data-openapi.yaml`: SHA-256 `9d5d62b302bced648b7212e6e8c589a741b258d38bb8769a1cd57c5224ecc1fe`.
- `api-spec__gamma-openapi.yaml`: SHA-256 `02d14aa0ad0b958fdb41b06b777136aa4cf2f50dbbb5f29e41cabfe051cfc000`.
- `api-spec__clob-openapi.yaml`: SHA-256 `82529177635db366c31a08777355b4b95c392a427298c3ba68904b937d4594da`.
- `changelog__sdks.md`: SHA-256 `22cd00085261ffcca54d8a1f86f4a0e92fc297101af0227083030ae84dc7f1a6`.
- `v2-migration.md`: SHA-256 `8dc52780b87a85faa22a030174cb28a2ee7bfd3c2797712527e3a83147452c7b`.
