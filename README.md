# Polymarket API Guide: Data Endpoints, V2/V3 & Official SDKs

Build Polymarket wallet trackers, portfolio dashboards, trade-history exports, and market analytics with the public **Polymarket Data API** at `https://data-api.polymarket.com`. This independent developer guide covers all 20 routes in the retrieved Data API specification, official TypeScript and Python SDKs, CLOB V2 and Exchange V3 differences, PolyV2 identifiers, Gamma joins, pagination, and P&L interpretation.

**Maintainer:** [geenes](https://github.com/geenes) · **Reviewed:** September 7, 2026 · **Scope:** Polymarket prediction-market Data API, current unified SDKs, and V2/V3 integration boundaries. This is community documentation, not an official Polymarket product or a Perps/Polymarket US API reference.

**Start here:** no API key or private key is needed for these public read requests. Use Gamma for market discovery, Data API for positions and historical activity, and CLOB for order books and trading. The full guide lives in the [GitHub repository](https://github.com/geenes/polymarket-data-api-guide); report reproducible documentation problems through [repository issues](https://github.com/geenes/polymarket-data-api-guide/issues).

## Contents

- [Quick start: make your first API request](#quick-start-make-your-first-api-request)
- [Data API vs Gamma API vs CLOB API](#data-api-vs-gamma-api-vs-clob-api)
- [Polymarket API versions: V1, V2, PolyV2, and Exchange V3](#polymarket-api-versions-v1-v2-polyv2-and-exchange-v3)
- [Official documentation and SDK directory](#official-documentation-and-sdk-directory)
- [PolyV2 identifiers and safe cross-protocol joins](#polyv2-identifiers-and-safe-cross-protocol-joins)
- [Official SDK quick starts and migration recipes](#official-sdk-quick-starts-and-migration-recipes)
- [V2 and V3 signing, collateral, and approvals](#v2-and-v3-signing-collateral-and-approvals)
- [Wallet addresses, condition IDs, event IDs, and token IDs](#wallet-addresses-condition-ids-event-ids-and-token-ids)
- [Endpoint reference and current limits](#endpoint-reference-and-current-limits)
- [Response fields, amounts, and PnL](#response-fields-amounts-and-pnl)
- [Pagination and complete history exports](#pagination-and-complete-history-exports)
- [Python: read positions with bounded retries](#python-read-positions-with-bounded-retries)
- [JavaScript: fetch trades with Node.js](#javascript-fetch-trades-with-nodejs)
- [Recipes for dashboards and research](#recipes-for-dashboards-and-research)
- [Rate limits, errors, and production operation](#rate-limits-errors-and-production-operation)
- [Frequently asked developer questions](#frequently-asked-developer-questions)
- [Validation, sources, and maintenance](#validation-sources-and-maintenance)

## Quick start: make your first API request

Requires `curl`; `jq` is optional for formatting and discovery. These requests read public data and do not place trades.

```bash
# Health check: the OpenAPI specification documents GET /.
curl --fail-with-body --max-time 20 'https://data-api.polymarket.com/'

# Two recent taker-side trade records; no wallet required.
curl --fail-with-body --max-time 20 --get \
  'https://data-api.polymarket.com/trades' \
  --data-urlencode 'limit=2' \
  --data-urlencode 'takerOnly=true'
```

To read a wallet, replace the placeholder with its public profile/position-holding address. Do not paste a seed phrase or private key.

```bash
export POLY_WALLET='REPLACE_WITH_0x_WALLET_ADDRESS'

curl --fail-with-body --max-time 20 --get \
  'https://data-api.polymarket.com/positions' \
  --data-urlencode "user=$POLY_WALLET" \
  --data-urlencode 'sizeThreshold=0' \
  --data-urlencode 'includeArchived=true' \
  --data-urlencode 'limit=100'
```

This requests one page. `sizeThreshold=0` includes positions below the default one-share threshold; `includeArchived=true` requests still-active positions in archived markets. A successful empty array is a valid response and is not, by itself, an authentication problem. [Official positions reference](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)

## Data API vs Gamma API vs CLOB API

| Developer task | Service | Base URL / stream |
| --- | --- | --- |
| Discover markets/events; search titles; obtain IDs and token mappings | Gamma API | `https://gamma-api.polymarket.com` |
| Current/closed positions, activity, holders, public trades, rankings | Data API | `https://data-api.polymarket.com` |
| Order books, bid/ask prices, spreads, historical token prices | CLOB public market data | `https://clob.polymarket.com` |
| Submit/cancel orders; private account orders and fills | Authenticated CLOB | Same CLOB host; authentication required |
| Stream public book/price updates | CLOB market WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/market` |
| Stream authenticated account order/trade updates | CLOB user WebSocket | `wss://ws-subscriptions-clob.polymarket.com/ws/user` |

The Data API's `GET /trades` and authenticated CLOB trade endpoints are different interfaces. Do not send CLOB authentication headers to an unrelated host or assume their pagination matches. A recorded trade price is also different from a currently executable quote. [Official integration surfaces and authentication](https://docs.polymarket.com/getting-started/api)

## Polymarket API versions: V1, V2, PolyV2, and Exchange V3

**Yes, official V2 and V3 support exists.** These labels describe different components. There is no single global API version you can apply by adding `/v3` to every Polymarket URL.

| Version label | What it identifies | Integration consequence |
| --- | --- | --- |
| Data API schema `info.version: 1.0.0` | Version metadata inside the retrieved OpenAPI file | The 20 documented paths below include unversioned routes and selected `/v1/...` routes. Use each exact path. |
| Legacy CLOB V1 | Retired exchange/signing integration | Old V1 order signatures and clients are not a production migration target. |
| CLOB / CTF Exchange V2 | Current CTF trading exchange generation | Production CLOB host remains `https://clob.polymarket.com`; use V2-compatible signing for CTF assets. |
| Market `version: "v1"` or `"v2"` | Position protocol reported by market metadata | This is distinct from the exchange's signing-domain version. `v1` metadata does not mean the retired CLOB V1 service. |
| PolyV2 | New position protocol, including binary, negative-risk, and Combo positions | Preserve structured position IDs and protocol-neutral condition IDs. |
| Exchange V3 | Exchange used by the current unified SDKs for PolyV2 orders | SDK routing selects the V3 exchange and signing domain from the supported position ID. |
| SDK `0.9.0`, V2 client `1.1.0`, Rust crate `0.7.0` | Independently released package versions | Package semver is not an HTTP path or onchain protocol number. |

The official migration page dates production CLOB V2 to **April 28, 2026**. Its former testing host, `clob-v2.polymarket.com`, is not the production host to copy into new code. [CLOB V2 migration](https://docs.polymarket.com/v2-migration)

The official unified-SDK changelog records Exchange V3 routing in TypeScript 0.7.0, protocol-neutral read fields in 0.8.0, and `assetId` order inputs in 0.9.0. Python 0.9.0 adds the corresponding asset identifiers, V3 routing, and PolyV2 lifecycle support. [SDK changelog](https://docs.polymarket.com/changelog/sdks)

The published Python 0.9.0 implementation independently confirms the distinction: order creation assigns domain version `"3"` to a recognized PolyV2 position ID and `"2"` to a CTF asset; exchange selection follows the same decision. The market model separately defines protocol values `v1` and `v2`. [Order version selection](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/actions/orders/orders.py), [exchange routing](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/actions/orders/context.py), [market model](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/models/gamma/market.py)

A third-party provider can also call its own service “Polymarket API v3.” Check its hostname, publisher, authentication, retention, and rate limits separately. That label does not establish compatibility with Polymarket Exchange V3.

## Official documentation and SDK directory

**For a new integration needing multiple Polymarket services, start with the current unified TypeScript or Python SDK.** Keep direct HTTP available for documented fields that a particular SDK release does not expose. For an existing CLOB-only application, consult both migration guides before choosing an incremental V2 upgrade or the unified interface.

Package versions and runtime requirements below were checked against package registries and official manifests on **September 7, 2026**. These are dated pins, not promises about future latest releases.

| Interface | Official package / import | Verified version | Minimum runtime | Source and package |
| --- | --- | --- | --- | --- |
| Unified TypeScript / JavaScript | `@polymarket/client`; `createPublicClient`, `createSecureClient` | `0.9.0` | Node.js `>=24` | [Source](https://github.com/Polymarket/ts-sdk), [npm](https://www.npmjs.com/package/@polymarket/client/v/0.9.0) |
| Unified Python | Distribution `polymarket-client`; import `polymarket` | `0.9.0` | Python `>=3.11` | [Source](https://github.com/Polymarket/py-sdk), [PyPI](https://pypi.org/project/polymarket-client/0.9.0/) |
| CLOB V2 TypeScript client | `@polymarket/clob-client-v2` | `1.1.0` | Node.js `>=20.10` | [Source](https://github.com/Polymarket/clob-client-v2), [npm](https://www.npmjs.com/package/@polymarket/clob-client-v2/v/1.1.0) |
| CLOB V2 Python client | Distribution `py-clob-client-v2`; import `py_clob_client_v2` | `1.1.0` | Python `>=3.9.10` | [Source](https://github.com/Polymarket/py-clob-client-v2), [PyPI](https://pypi.org/project/py-clob-client-v2/1.1.0/) |
| Rust V2 client | Crate `polymarket_client_sdk_v2` | `0.7.0` | Rust `>=1.88.0` | [Source](https://github.com/Polymarket/rs-clob-client-v2), [crate](https://crates.io/crates/polymarket_client_sdk_v2/0.7.0) |
| Direct HTTP / WebSocket | No SDK required | Endpoint-specific | Any compatible runtime | [Official API guide](https://docs.polymarket.com/getting-started/api) |

The Rust package above is the existing V2 client. The official SDK overview describes a separate unified Rust SDK as still in development. V3 behavior in this guide was verified from the current unified TypeScript/Python packages; do not infer identical support from a V2 package name. [Official SDK overview](https://docs.polymarket.com/getting-started/sdks-apis)

### Primary documentation by task

| Need | Start with |
| --- | --- |
| SDK setup, typed responses, public vs secure clients | [TypeScript](https://docs.polymarket.com/getting-started/typescript), [Python](https://docs.polymarket.com/getting-started/python) |
| Upgrade an earlier SDK | [Unified SDK migration](https://docs.polymarket.com/getting-started/migrate-from-previous-sdks), [CLOB V2 migration](https://docs.polymarket.com/v2-migration) |
| Market/event discovery, filters, keyset pagination | [Gamma OpenAPI](https://docs.polymarket.com/api-spec/gamma-openapi.yaml), [market discovery](https://docs.polymarket.com/market-data/discover-markets) |
| Wallets, activity, positions, P&L, holders | [Data OpenAPI](https://docs.polymarket.com/api-spec/data-openapi.yaml), [20-route reference below](#endpoint-reference-and-current-limits) |
| Books, prices, orders, authentication payloads | [CLOB OpenAPI](https://docs.polymarket.com/api-spec/clob-openapi.yaml) |
| Real-time books and account events | [Market stream](https://docs.polymarket.com/api-reference/wss/market), [user stream](https://docs.polymarket.com/api-reference/wss/user) |
| Gasless wallet transactions and relayer authentication | [Relayer OpenAPI](https://docs.polymarket.com/api-spec/relayer-openapi.yaml), [submit-transaction reference](https://docs.polymarket.com/api-reference/relayer/submit-a-transaction) |
| Combo discovery and RFQ requests/quotes | [Combos RFQ OpenAPI](https://docs.polymarket.com/api-spec/combos-rfq-openapi.yaml), [Combo market discovery](https://docs.polymarket.com/api-reference/combo-markets/get-combo-markets) |
| Supported bridge assets and transfer status | [Bridge OpenAPI](https://docs.polymarket.com/api-spec/bridge-openapi.yaml) |
| Settlement contracts and collateral | [Contract registry](https://docs.polymarket.com/resources/contracts), [pUSD](https://docs.polymarket.com/concepts/pusd) |
| Changes, limits, and debugging | [SDK changelog](https://docs.polymarket.com/changelog/sdks), [prediction-market changelog](https://docs.polymarket.com/changelog/predictions), [HTTP limits](https://docs.polymarket.com/api-reference/rate-limits), [trading limits](https://docs.polymarket.com/api-reference/trading-rate-limits) |
| Find additional official pages | [Documentation index](https://docs.polymarket.com/llms.txt) |

These adjacent specifications cover separate services, not additional Data API endpoints. This guide focuses on prediction-market data and integration boundaries; it does not claim complete Perps, bridge execution, or Polymarket US coverage.

## PolyV2 identifiers and safe cross-protocol joins

Treat `ClobAssetId` as a string identifier that can represent **either a CTF token ID or a PolyV2 position ID**. “Structured” describes the position ID's encoded layout; it does not mean every response returns a JSON object. The sampled Gamma position IDs were large decimal strings. Do not convert them through JavaScript `Number`, truncate them, or derive protocol from decimal-string length. [Published identifier types](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/models/types.py), [protocol decoder](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/protocol.py)

| Concept | Current unified SDK representation | Practical rule |
| --- | --- | --- |
| CTF outcome | `outcomes.yes.tokenId` / `.no.tokenId`; Python `token_id` | Nullable; keep outcome labels alongside IDs. “yes”/“no” slots can carry labels such as “Up”/“Down.” |
| PolyV2 outcome | `outcomes.yes.positionId` / `.no.positionId`; Python `position_id` | Nullable; keep it separately from the CTF mapping. |
| Asset in CLOB/Data responses | `assetId`; Python `asset_id` | Prefer this protocol-neutral SDK field over deprecated token aliases. |
| Market condition | `conditionId`; Python `condition_id` | Do not assume every protocol uses a 32-byte CTF hash. |
| Market protocol | `market.version` | Preserve it with the mapping; missing/unknown values need explicit handling. |
| Combo eligibility | `market.state.comboStatus`; Python `combo_status` | Pending eligibility is not evidence of an executable Combo market. |

The Python 0.9.0 request type accepts **31-byte or 32-byte hex condition IDs**. Its response parser accepts hex condition strings without inferring protocol. By contrast, some raw endpoint schemas still document 32-byte CTF-style patterns. Treat that as an interface difference to verify per route; do not globally pad, shorten, or rewrite identifiers to satisfy a stale assumption. [Condition validation source](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/models/types.py)

A live Gamma sample on the review date reported `version: "v1"`, `comboStatus: "pending"`, and **both** token and position IDs. Therefore, `positionId ?? tokenId` is not a sufficient general trading selector. For a new order, establish which protocol/asset is currently supported and check the market's order-acceptance state. Once an intended supported asset is supplied, the unified SDK performs exchange routing. An existing position/trade already provides its own asset identity; retain that identity when joining records.

For storage, use separate columns for service, chain, wallet, market ID, condition ID, asset ID, protocol version, outcome label, and raw source identifiers. Join assets using explicit metadata mappings, not matching question text. Keep raw response payloads or their reproducible source records when auditability matters. This storage recommendation follows from the identifier differences above; it is not an official database schema.

### Raw JSON is not the SDK model

| Data | Raw response example | TypeScript 0.9.0 | Python 0.9.0 |
| --- | --- | --- | --- |
| Trade asset | `asset` | `assetId` | `asset_id` |
| Trade holding wallet | `proxyWallet` | `wallet` | `wallet` |
| Trade condition | `conditionId` | `conditionId` | `condition_id` |
| Trade timestamp | Unix seconds | Epoch **milliseconds** | Timezone-aware `datetime` |
| Trade size/price | JSON number | Decimal string | `Decimal` |
| Gamma outcomes | JSON-encoded parallel arrays may occur | Structured `outcomes.yes` / `.no` | `MarketOutcomes.yes` / `.no` |
| List results | Array or endpoint-specific envelope | Page with `items`, `hasMore`, `nextCursor` | Page with `items`, `has_more`, `next_cursor` |

Timestamp and decimal conversions above were observed in the two installed SDKs' public trade reads. The Python Data models also show the wire-field aliases explicitly. Apply conversion rules to the specific model, not every timestamp returned by every API. [Trade models](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/models/data/activity.py), [portfolio models](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/models/data/portfolio.py)

## Official SDK quick starts and migration recipes

The repository contains dependency-free HTTP examples **and** examples using the current official SDKs. The latter intentionally fetch only two markets and two trades. They require no credentials and do not create a secure client.

### TypeScript SDK from JavaScript: Node.js 24 or newer

From a clone of [this repository](https://github.com/geenes/polymarket-data-api-guide):

```bash
npm ci --prefix examples --ignore-scripts
node examples/sdk-public.mjs
```

The pinned dependency is `@polymarket/client@0.9.0`. In a separate project, install it with `npm install --save-exact @polymarket/client@0.9.0`. Minimal public discovery:

```javascript
import { createPublicClient } from '@polymarket/client';

const client = createPublicClient();
const pages = client.listMarkets({ closed: false, pageSize: 2 });
const page = await pages.firstPage();
for (const market of page.items) {
  console.log({
    id: market.id,
    version: market.version,
    conditionId: market.conditionId,
    outcomes: market.outcomes, // Contains separate tokenId and positionId fields.
  });
}
// Save nextCursor unchanged, together with the original query and SDK version.
// const nextPage = await pages.from(page.nextCursor).firstPage();
```

Only resume when `page.hasMore` is true and `page.nextCursor` exists. Do not translate an SDK cursor into a numeric REST offset. The runnable [JavaScript SDK example](https://github.com/geenes/polymarket-data-api-guide/blob/main/examples/sdk-public.mjs) also demonstrates public trades, correct timestamp conversion, and an optional book read using `POLY_ASSET_ID`. [Official TypeScript pagination](https://docs.polymarket.com/getting-started/typescript)

### Python SDK: Python 3.11 or newer

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r examples/requirements-sdk.txt
.venv/bin/python examples/sdk_public.py
```

Use another installed Python version at least 3.11 if appropriate. The distribution is `polymarket-client==0.9.0`; the import is `polymarket`, not `py_clob_client_v2`.

```python
from polymarket import PublicClient

with PublicClient() as client:
    pages = client.list_markets(closed=False, page_size=2)
    page = pages.first_page()
    for market in page.items:
        print(market.id, market.version, market.condition_id)
        print(market.outcomes.yes.token_id, market.outcomes.yes.position_id)
    if page.has_more and page.next_cursor:
        next_page = pages.from_cursor(page.next_cursor).first_page()
        print("Second page:", len(next_page.items))
```

Use `AsyncPublicClient` with `async with` and await `.first_page()` in asynchronous applications. Subscription workflows are async-only. The runnable [Python SDK example](https://github.com/geenes/polymarket-data-api-guide/blob/main/examples/sdk_public.py) serializes `Decimal` as strings and `datetime` as ISO text. [Official Python guide](https://docs.polymarket.com/getting-started/python)

### Common method and field migrations

These are current **unified SDK** method names, not methods promised on older CLOB client classes. Casing alone is not enough to translate between languages.

| Task | TypeScript 0.9.0 | Python 0.9.0 |
| --- | --- | --- |
| Discover markets | `listMarkets({pageSize: 2})` | `list_markets(page_size=2)` |
| Read public trades | `listTrades({pageSize: 2})` | `list_trades(page_size=2)` |
| Read wallet positions | `listPositions({user, pageSize: 2})` | `list_positions(user=wallet, page_size=2)` |
| Read one order book | `fetchOrderBook({assetId})` | `get_order_book(asset_id=asset_id)` |
| Inspect trading approvals without signing | `fetchTradingApprovalsState({user})` | `get_trading_approvals_state(wallet=wallet)` |
| First page | `await pages.firstPage()` | `pages.first_page()`; await for async client |
| Resume SDK cursor | `pages.from(cursor)` | `pages.from_cursor(cursor)` |
| Preferred asset inputs/outputs | `assetId`, `assetIds` where supported | `asset_id`, `asset_ids` where supported |
| Preferred condition model field | `conditionId` | `condition_id` |

Prefer current neutral asset names. Deprecated token aliases remain in these releases, but do not pass both canonical and alias parameters: Python's resolver rejects that ambiguity. Raw HTTP parameters retain their documented names; the SDK rename does **not** authorize changing every URL query to `assetId`. [Asset argument resolver](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/actions/exchange_asset.py)

Check actual callable signatures when feature coverage matters. For example, the installed Python 0.9.0 `list_positions` did **not** expose the raw endpoint's `includeArchived` parameter. Use the direct HTTP example with `includeArchived=true` for that requirement, rather than silently dropping it or assuming every schema field has an SDK argument. The Data API endpoint tables below remain useful even when you adopt an SDK.

### Gamma keyset pagination for larger discovery jobs

Gamma documents `GET /markets/keyset` and `/events/keyset`. For markets, `limit` is 1–100, default 20. The response envelope contains `markets` and `next_cursor`. Pass response `next_cursor` back as `after_cursor`; **`offset` is rejected**. Preserve the original filters and ordering across pages. [Gamma keyset specification](https://docs.polymarket.com/api-spec/gamma-openapi.yaml)

```bash
curl --fail-with-body --max-time 20 --get \
  'https://gamma-api.polymarket.com/markets/keyset' \
  --data-urlencode 'closed=false' \
  --data-urlencode 'limit=2'
```

The earlier `/markets?limit=1` example remains a small discovery request, not a recommended whole-catalogue scan. SDK pagination is its own abstraction and can use different backend strategies by method/release. Do not assume its cursor is interchangeable with `after_cursor`. For any broad export, record its scope, checkpoint, observation time, and whether the scan reached the end.

### Errors and secure-client boundaries

Public clients expose typed input, transport, response, rejection, and rate-limit errors. Retain the original error and endpoint context, respect retry information when available, and keep retries bounded. The example scripts let failures terminate the process rather than printing plausible empty data. In TypeScript, action-specific guards such as `ListMarketsError.isError(error)` support narrower handling. [TypeScript error handling](https://docs.polymarket.com/getting-started/typescript)

Secure client setup is an operational step: configuration can create/derive API credentials and, if a wallet is omitted, initialize a deposit wallet. Supplying an existing wallet and its correct type matters. Do not use a secure client merely to read public data. Follow the official migration guide for signer adapters, wallet selection, credentials, and relayer authorization; those details are not equivalent to the public constructors above. [Secure-client migration](https://docs.polymarket.com/getting-started/migrate-from-previous-sdks)

## V2 and V3 signing, collateral, and approvals

This section is a compatibility reference for developers integrating trading alongside analytics. The examples in this repository do not sign messages, approve tokens, deploy wallets, or place orders.

### Signed orders and authentication are separate layers

| Layer | What to verify |
| --- | --- |
| CTF order signing | Exchange domain version `"2"`, correct standard/negative-risk verifying contract, current signed order fields. |
| PolyV2 order signing | Exchange domain version `"3"` and V3 verifying contract selected for the intended supported position ID. |
| CLOB API key derivation | `ClobAuthDomain` still uses version `"1"`; do not replace it because order signing moved to V2/V3. |
| Authenticated REST request | API-key/HMAC request authentication is separate from the signed order included in the request. |
| Deposit-wallet signature | Contract-wallet validation adds its own envelope; it is not interchangeable with an EOA signature. |
| Relayer request | Builder or Relayer API authentication belongs to the relayer service. It is separate from order attribution. |

The current Python typed-data builder retains the signed field name `tokenId` even when the SDK input is `asset_id`. Its domain is selected per order; deposit-wallet signatures additionally wrap the order for contract-wallet verification. **Do not rename the signed struct to match application-facing field names.** [Typed-data implementation](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/actions/orders/typed_data.py)

Relative to V1, the V2 signed struct removes `taker`, `expiration`, `nonce`, and `feeRateBps`; it adds millisecond `timestamp`, `metadata`, and `builder`. GTD `expiration` remains in the submitted order body even though it is outside the V2 signed struct. The order-domain name is still `Polymarket CTF Exchange`. Authentication domain/version and order-domain/version must be checked independently. [Official V2 payload and authentication migration](https://docs.polymarket.com/v2-migration)

### Polygon contract map

Network: **Polygon mainnet, chain ID 137**. These are dated reference addresses from the official registry and installed SDK configuration. Recheck the registry before using them in a deployment; selecting an address does not establish that an approval is needed.

| Role | Address |
| --- | --- |
| CTF Exchange V2 | `0xE111180000d2663C0091e4f400237545B87B996B` |
| Negative-risk CTF Exchange V2 | `0xe2222d279d744050d28e00520010520000310F59` |
| Exchange V3 proxy, listed under Combos contracts | `0xe3333700cA9d93003F00f0F71f8515005F6c00Aa` |
| CTF conditional tokens | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |
| PolyV2 PositionManager proxy | `0x006F54F7f9A22e0000CC2AB60031000000ae9fEF` |
| BinaryModule proxy | `0x1000008dD9001B968442c1000017eaE6E0dA00Ba` |
| NegRiskModule proxy | `0x200000900045e3B6259600682756002200028933` |
| CombinatorialModule proxy | `0x30000034706C7d8e12009DAB006Be20000c031A8` |
| pUSD proxy | `0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB` |

[Official contract registry](https://docs.polymarket.com/resources/contracts); the [SDK environment configuration](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/environments.py) identifies the V3 exchange explicitly.

Current collateral is pUSD; older response names containing `usdc` do not identify the settlement contract. Approval state is scoped to wallet, token, operator/spender, and protocol. A CTF allowance is not proof that a PolyV2 position can be transferred or traded. The current SDK includes PositionManager and PolyV2 module approvals in its lifecycle logic. Read approval state first; the public check is distinct from `setupTradingApprovals` / `setup_trading_approvals`, which can submit transactions. [Approval implementation](https://github.com/Polymarket/py-sdk/blob/main/src/polymarket/_internal/actions/relayer/approvals.py), [pUSD reference](https://docs.polymarket.com/concepts/pusd)

Old CLOB V1 negative-risk adapter addresses still appear in historical material. The current registry labels the old adapter deprecated. Do not copy a historical “approve all these contracts” list into a new integration. Use the current SDK workflow for the specific wallet and position protocol. [Contract deprecation status](https://docs.polymarket.com/resources/contracts)

### Migration procedure for an existing application

1. Inventory service URLs, installed packages, wallet type, asset/condition types, raw field names, and persisted cursors.
2. Upgrade one supported SDK generation deliberately; compile/type-check and inspect its actual signatures. Keep a dependency lock and note the runtime requirement change.
3. Preserve both token and position mappings. Replace CTF-only model assumptions where the chosen API supports neutral identifiers; retain wire names at the HTTP boundary.
4. Recheck market metadata and intended asset routing. For trading, validate the correct exchange, domain, collateral, wallet signer, tick grid, and approvals through the chosen SDK.
5. Reconcile read-only outputs first: market mapping, trade times, positions, decimals, and pagination. Test migration behavior against saved cases, including a market that exposes both ID families.
6. Validate signing and trading separately in your own authorized integration. An accepted or matched order is not itself proof of final onchain settlement.

This is an integration checklist derived from the version differences above, not a claim that a trading migration was exercised here.

### Known documentation and validation gaps

The documentation, raw specifications, and package releases can advance independently. This review found a historical `clob-v2` host in an SDK migration example, CTF-oriented wording in raw schemas, and older `tokenId` examples alongside newer neutral asset fields. Prefer the explicit production-host correction, the exact installed package API, and dated source evidence; report unresolved discrepancies upstream.

Live checks exercised public CTF-backed market/book data and observed mapped PolyV2 IDs. They **did not establish successful live Exchange V3 order execution or a populated PolyV2 portfolio**. V3 signing/routing claims here are supported by official release notes and inspected published code. The [validation record](https://github.com/geenes/polymarket-data-api-guide/blob/main/VALIDATION.md) separates these kinds of evidence.

## Wallet addresses, condition IDs, event IDs, and token IDs

Polymarket uses multiple identifiers. The Data API `market` filter expects a **condition ID**, not the numeric Gamma market ID, event ID, market slug, or outcome token ID.

| Identifier | Shape | Where to use it |
| --- | --- | --- |
| Profile/holding wallet | `0x` + 40 hexadecimal characters | Data API `user`; commonly returned as `proxyWallet` |
| Condition ID | CTF: `0x` + 64 hex characters; neutral SDK types also accept 31-byte conditions | Data API `market` under its endpoint-specific schema; Gamma/SDK `conditionId` |
| Question ID | `0x` + 64 hexadecimal characters | `questionID` for revisions; distinct from condition ID |
| Gamma market ID | Numeric ID, often represented as a string | Gamma market lookup |
| Event ID | Positive integer | `eventId` where supported; `id` on `/live-volume` |
| Outcome asset ID | String; CTF token or PolyV2 position ID depending on protocol | Preserve raw `asset`/`token` and use SDK `assetId` / `asset_id`; see protocol section above |
| Slug | Human-readable text | Gamma slug lookup and user-facing links |

A signer address and a proxy/deposit wallet need not be the same address. Resolve a supplied wallet through Gamma's public profile endpoint and inspect its `proxyWallet`; check it against a known position or trade before concluding the account is empty. Gamma accepts a proxy wallet or user address as the profile lookup input. [Public profile reference](https://docs.polymarket.com/api-reference/profiles/get-public-profile-by-wallet-address)

```bash
curl --fail-with-body --max-time 20 --get \
  'https://gamma-api.polymarket.com/public-profile' \
  --data-urlencode "address=$POLY_WALLET"
```

Discover a market and extract its condition ID with `jq`:

```bash
POLY_MARKET_JSON=$(curl --fail-with-body --max-time 20 --get \
  'https://gamma-api.polymarket.com/markets' \
  --data-urlencode 'closed=false' --data-urlencode 'limit=1')
export POLY_CONDITION_ID=$(printf '%s' "$POLY_MARKET_JSON" | jq -er '.[0].conditionId')

curl --fail-with-body --max-time 20 --get \
  'https://data-api.polymarket.com/holders' \
  --data-urlencode "market=$POLY_CONDITION_ID" \
  --data-urlencode 'limit=20'
```

Gamma may represent `outcomes`, `outcomePrices`, and `clobTokenIds` as JSON-encoded strings. Parse those values before indexing them, and match outcomes to token IDs by array position. Check equal array lengths. Preserve `positionIds` and `version` as well when present; CTF token arrays are not the whole protocol-neutral mapping. Keep all IDs as strings: conversion to a JavaScript `Number` can corrupt the identifier. A sample of one market is discovery, not a complete active-market catalogue. [Official market discovery guide](https://docs.polymarket.com/market-data/discover-markets)

## Endpoint reference and current limits

All routes below use `GET` and the Data API host. Parameters are query parameters. Arrays use comma-separated values; booleans use `true` / `false`; timestamps use Unix seconds. Omit optional filters you do not want. Where both exist, `market` and `eventId` are mutually exclusive.

The following values are transcribed from the official specification retrieved on September 7, 2026. They are documented limits, not load-test results. A supported maximum is a ceiling, not a recommended page size. Use a positive `limit` even where the schema permits zero.

| Endpoint | Purpose | Required input | Default / max limit | Max offset |
| --- | --- | --- | --- | --- |
| [`/positions`](#endpoint-positions) | Current positions | `user` | 100 / 500 | 10000 |
| [`/closed-positions`](#endpoint-closed-positions) | Closed positions | `user` | 10 / 50 | 100000 |
| [`/trades`](#endpoint-trades) | Public trade history | None | 100 / 10000 | 10000 |
| [`/activity`](#endpoint-activity) | Wallet activity, deposits, and withdrawals | `user` | 100 / 500 | 5000 |
| [`/holders`](#endpoint-holders) | Top holders by outcome token | `market` | 20 / 20 | — |
| [`/value`](#endpoint-value) | Total position value | `user` | — | — |
| [`/v1/market-positions`](#endpoint-v1-market-positions) | Paginated positions for a market | `market` | 50 / 500 | 10000 |
| [`/oi`](#endpoint-oi) | Open interest | None | — | — |
| [`/live-volume`](#endpoint-live-volume) | Event volume | `id` | — | — |
| [`/traded`](#endpoint-traded) | Number of markets traded | `user` | — | — |
| [`/v1/leaderboard`](#endpoint-v1-leaderboard) | Trader leaderboard | None | 25 / 50 | 1000 |
| [`/v1/builders/leaderboard`](#endpoint-v1-builders-leaderboard) | Builder leaderboard | None | 25 / 50 | 1000 |
| [`/v1/builders/volume`](#endpoint-v1-builders-volume) | Daily builder volume | None | — | — |
| [`/v1/accounting/snapshot`](#endpoint-v1-accounting-snapshot) | Accounting CSV export | `user` | — | — |
| [`/v1/positions/combos`](#endpoint-v1-positions-combos) | Combo positions and incremental sync | `user` | 20 / 1000 | 100000 |
| [`/v1/activity/combos`](#endpoint-v1-activity-combos) | Combo lifecycle activity | `user` | 50 / 500 | 10000 |
| [`/v1/approvals`](#endpoint-v1-approvals) | Token approval state | `user` | — | — |
| [`/revisions`](#endpoint-revisions) | Question revisions | `questionID` | 100 / 500 | — |
| [`/other`](#endpoint-other) | Augmented negative-risk Other size | `id`, `user` | — | — |
| [`/`](#endpoint-health) | Health check | None | — | — |

<a id="endpoint-positions"></a>

### GET `/positions` — Current positions

Returns `Position[]`. Use `sizeThreshold=0` when small holdings matter. Sort by `CURRENT` for exposure or `CASHPNL` for the API's cash P&L field; neither is a complete account ledger.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |
| `market` | CSV string | CSV condition IDs; exclude eventId. |
| `eventId` | CSV integer | CSV numeric event IDs; exclude market. |
| `sizeThreshold` | number | Default `1.0`; min 0; Minimum position size. |
| `redeemable` | boolean | Default `false` |
| `mergeable` | boolean | Default `false` |
| `includeArchived` | boolean | Default `false`; Include still-active positions in archived markets. |
| `limit` | integer | Default `100`; min 0; max 500 |
| `offset` | integer | Default `0`; min 0; max 10000 |
| `sortBy` | string | Default `TOKENS`; `CURRENT`, `INITIAL`, `TOKENS`, `CASHPNL`, `PERCENTPNL`, `TITLE`, `RESOLVING`, `PRICE`, `AVGPRICE` |
| `sortDirection` | string | Default `DESC`; `ASC`, `DESC` |
| `title` | string | max 100 characters |

[Official current positions source](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)

<a id="endpoint-closed-positions"></a>

### GET `/closed-positions` — Closed positions

Returns `ClosedPosition[]`. The default order is realized P&L, not recency. Set `sortBy=TIMESTAMP` for a time-oriented view. A resolved market and a closed position are different concepts; preserve both current and closed datasets.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |
| `market` | CSV string | Condition IDs; CSV. |
| `title` | string | max 100 characters |
| `eventId` | CSV integer | CSV event IDs; exclude market. |
| `limit` | integer | Default `10`; min 0; max 50 |
| `offset` | integer | Default `0`; min 0; max 100000 |
| `sortBy` | string | Default `REALIZEDPNL`; `REALIZEDPNL`, `TITLE`, `PRICE`, `AVGPRICE`, `TIMESTAMP` |
| `sortDirection` | string | Default `DESC`; `ASC`, `DESC` |

[Official closed positions source](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user)

<a id="endpoint-trades"></a>

### GET `/trades` — Public trade history

Returns `Trade[]`. All query parameters are optional. `takerOnly=true` is the default; explicitly set `false` for maker and taker records. Pair `filterType` with `filterAmount`. This endpoint documents a maximum limit of 10,000, superseding the older gist's 500.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `limit` | integer | Default `100`; min 0; max 10000 |
| `offset` | integer | Default `0`; min 0; max 10000 |
| `takerOnly` | boolean | Default `true` |
| `filterType` | string | `CASH`, `TOKENS`; Requires filterAmount. |
| `filterAmount` | number | min 0; Requires filterType. |
| `market` | CSV string | Condition IDs; CSV. |
| `eventId` | CSV integer | CSV event IDs; exclude market. |
| `user` | string | Optional |
| `side` | string | `BUY`, `SELL` |
| `start` | integer | min 0; Epoch seconds; positive start enables older user-scoped history. See history section. |
| `end` | integer | min 0; Epoch seconds; freezes the upper time bound. |

[Official public trade history source](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets)

<a id="endpoint-activity"></a>

### GET `/activity` — Wallet activity, deposits, and withdrawals

Returns `Activity[]`. For deposits/withdrawals, set `excludeDepositsWithdrawals=false` even when `type=DEPOSIT,WITHDRAWAL`. Trade-only history misses redemptions, splits, merges, and other cash/inventory changes. See the pagination section for default history windows.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `limit` | integer | Default `100`; min 0; max 500 |
| `offset` | integer | Default `0`; min 0; max 5000 |
| `user` | string | **Required** |
| `market` | CSV string | Condition IDs; CSV. |
| `eventId` | CSV integer | CSV event IDs; exclude market. |
| `type` | CSV string | `TRADE`, `SPLIT`, `MERGE`, `REDEEM`, `REWARD`, `CONVERSION`, `DEPOSIT`, `WITHDRAWAL`, `YIELD`, `MAKER_REBATE`, `TAKER_REBATE`, `REFERRAL_REWARD`; CSV activity types; deposits/withdrawals also need exclusion flag false. |
| `excludeDepositsWithdrawals` | boolean | Default `true`; Set false to include deposits and withdrawals. |
| `start` | integer | min 0; Epoch seconds; see default-window behavior below. |
| `end` | integer | min 0; Epoch seconds. |
| `sortBy` | string | Default `TIMESTAMP`; `TIMESTAMP`, `TOKENS`, `CASH` |
| `sortDirection` | string | Default `DESC`; `ASC`, `DESC` |
| `side` | string | `BUY`, `SELL` |

[Official wallet activity, deposits, and withdrawals source](https://docs.polymarket.com/api-reference/core/get-user-activity)

<a id="endpoint-holders"></a>

### GET `/holders` — Top holders by outcome token

Returns `[{token, holders:[...]}]`, grouped by outcome token. The cap is 20 holders per token and there is no offset parameter. This is a top-holder view; use market positions for a paginated participation view.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `limit` | integer | Default `20`; min 0; max 20; Per token, maximum 20. |
| `market` | CSV string | **Required**; Condition IDs; CSV. |
| `minBalance` | integer | Default `1`; min 0; max 999999; Minimum holder balance. |

[Official top holders by outcome token source](https://docs.polymarket.com/api-reference/core/get-top-holders-for-markets)

<a id="endpoint-value"></a>

### GET `/value` — Total position value

Returns an array such as `[{"user":"0x…","value":123.45}]` (illustrative). Position value is not automatically available cash, total deposited capital, or lifetime profit. Preserve the requested market scope in your dashboard.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |
| `market` | CSV string | Condition IDs; CSV. |

[Official total position value source](https://docs.polymarket.com/api-reference/core/get-total-value-of-a-users-positions)

<a id="endpoint-v1-market-positions"></a>

### GET `/v1/market-positions` — Paginated positions for a market

Returns `[{token, positions:[...]}]`; limit and offset apply per outcome token. `OPEN` means size > 0.01; `CLOSED` means size <= 0.01. These are endpoint-specific size classifications. The schema uses `currPrice` here, while `/positions` uses `curPrice`.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `market` | string | **Required**; Condition ID. |
| `user` | string | Optional |
| `status` | string | Default `ALL`; `OPEN`, `CLOSED`, `ALL` |
| `sortBy` | string | Default `TOTAL_PNL`; `TOKENS`, `CASH_PNL`, `REALIZED_PNL`, `TOTAL_PNL` |
| `sortDirection` | string | Default `DESC`; `ASC`, `DESC` |
| `limit` | integer | Default `50`; min 0; max 500; Per outcome token. |
| `offset` | integer | Default `0`; min 0; max 10000; Per outcome token. |

[Official paginated positions for a market source](https://docs.polymarket.com/api-reference/core/get-positions-for-a-market)

<a id="endpoint-oi"></a>

### GET `/oi` — Open interest

Returns `[{market, value}]`. The market filter is optional. Keep open interest separate from traded volume: they answer different questions. The response schema does not define a general historical-series interface.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `market` | CSV string | Condition IDs; CSV. |

[Official open interest source](https://docs.polymarket.com/api-reference/misc/get-open-interest)

<a id="endpoint-live-volume"></a>

### GET `/live-volume` — Event volume

Requires the numeric event `id`; returns an array containing `total` and per-market `markets` data. Do not assume this is a 24-hour metric solely from the endpoint name: the retrieved response schema does not establish a 24-hour window.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `id` | integer | **Required**; min 1 |

[Official event volume source](https://docs.polymarket.com/api-reference/misc/get-live-volume-for-an-event)

<a id="endpoint-traded"></a>

### GET `/traded` — Number of markets traded

Returns an object with `user` and `traded`. This is a market count, not a trade count or a win rate.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |

[Official number of markets traded source](https://docs.polymarket.com/api-reference/misc/get-total-markets-a-user-has-traded)

<a id="endpoint-v1-leaderboard"></a>

### GET `/v1/leaderboard` — Trader leaderboard

Returns ranked trader rows with wallet, volume (`vol`), P&L (`pnl`), and profile metadata. Specify category, period, and ordering explicitly in reproducible research. A leaderboard is a selected population, not an unbiased sample of all traders.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `category` | string | Default `OVERALL`; `OVERALL`, `POLITICS`, `SPORTS`, `ESPORTS`, `CRYPTO`, `CULTURE`, `MENTIONS`, `WEATHER`, `ECONOMICS`, `TECH`, `FINANCE` |
| `timePeriod` | string | Default `DAY`; `DAY`, `WEEK`, `MONTH`, `ALL` |
| `orderBy` | string | Default `PNL`; `PNL`, `VOL` |
| `limit` | integer | Default `25`; min 1; max 50 |
| `offset` | integer | Default `0`; min 0; max 1000 |
| `user` | string | Optional |
| `userName` | string | Optional |

[Official trader leaderboard source](https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings)

<a id="endpoint-v1-builders-leaderboard"></a>

### GET `/v1/builders/leaderboard` — Builder leaderboard

Returns aggregate builder entries for a selected period. Builder-routed activity and a trader's own account activity have different scopes; do not combine the rankings as though they were the same population.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `timePeriod` | string | Default `DAY`; `DAY`, `WEEK`, `MONTH`, `ALL` |
| `limit` | integer | Default `25`; min 0; max 50 |
| `offset` | integer | Default `0`; min 0; max 1000 |

[Official builder leaderboard source](https://docs.polymarket.com/api-reference/builders/get-aggregated-builder-leaderboard)

<a id="endpoint-v1-builders-volume"></a>

### GET `/v1/builders/volume` — Daily builder volume

Returns daily builder volume records. `timePeriod` is the documented query control; the retrieved schema does not provide limit/offset parameters for this route.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `timePeriod` | string | Default `DAY`; `DAY`, `WEEK`, `MONTH`, `ALL` |

[Official daily builder volume source](https://docs.polymarket.com/api-reference/builders/get-daily-builder-volume-time-series)

<a id="endpoint-v1-accounting-snapshot"></a>

### GET `/v1/accounting/snapshot` — Accounting CSV export

Returns a ZIP containing `positions.csv` and `equity.csv`, not JSON. Save the response as a file, inspect the actual CSV headers, and retain the acquisition time. This route is a snapshot export, not a promise of an all-time transaction archive.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |

[Official accounting csv export source](https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs)

<a id="endpoint-v1-positions-combos"></a>

### GET `/v1/positions/combos` — Combo positions and incremental sync

Returns `{combos: [...], pagination: {...}}`. Follow the opaque `pagination.next_cursor` with unchanged filters and sort. `updatedAfter` / `updatedBefore` use epoch seconds. The documented sync mode has an approximately 90-second visibility lag; overlap watermarks and upsert by `(combo_condition_id, combo_position_id)`. Decimal monetary strings must remain precision-preserving.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |
| `status` | CSV string | `OPEN`, `PARTIAL`, `RESOLVED_PARTIAL`, `RESOLVED_WIN`, `RESOLVED_LOSS` |
| `sort` | string | Default `current_value_desc`; `current_value_desc`, `first_entry_desc`, `entry_cost_desc`, `resolved_at_desc`, `updated_asc` |
| `market_id` | CSV string | CSV combo condition IDs. |
| `limit` | integer | Default `20`; min 0; max 1000 |
| `offset` | integer | Default `0`; min 0; max 100000 |
| `updatedAfter` | integer | Inclusive sync lower bound, epoch seconds. |
| `updatedBefore` | integer | Inclusive upper bound; must be >= updatedAfter; safety lag applies. |
| `cursor` | string | Opaque next_cursor; supersedes offset. |

[Official combo positions and incremental sync source](https://docs.polymarket.com/api-reference/core/get-user-combo-positions)

<a id="endpoint-v1-activity-combos"></a>

### GET `/v1/activity/combos` — Combo lifecycle activity

Returns `{activity: [...], pagination: {...}}`. Use `market_id` for combo condition IDs; it is not named `market` here. Follow `pagination.next_cursor`; do not decode or construct cursor values. The schema includes transaction/log details and leg breakdowns. Our smoke check returned an empty activity array, so populated combo rows were not verified.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |
| `market_id` | CSV string | CSV combo condition IDs. |
| `limit` | integer | Default `50`; min 0; max 500 |
| `offset` | integer | Default `0`; min 0; max 10000 |
| `cursor` | string | Opaque next_cursor; supersedes offset. |

[Official combo lifecycle activity source](https://docs.polymarket.com/api-reference/core/get-user-combo-activity)

<a id="endpoint-v1-approvals"></a>

### GET `/v1/approvals` — Token approval state

The specification includes this read endpoint with `{address, chainId, checkedAt, contracts}`. Our sampled request returned HTTP 500. Treat availability as unverified. `checkedAt` describes response generation, not a fresh onchain allowance read. This GET does not grant approvals.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `user` | string | **Required** |

[Official token approval state source](https://docs.polymarket.com/api-spec/data-openapi.yaml)

<a id="endpoint-revisions"></a>

### GET `/revisions` — Question revisions

The specification lists this route for moderated question revisions. Its input is `questionID`, not `conditionId`. Returns revision payloads; live behavior was not tested for this guide.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `questionID` | string | **Required** |
| `limit` | integer | Default `100`; min 0; max 500 |

[Official question revisions source](https://docs.polymarket.com/api-spec/data-openapi.yaml)

<a id="endpoint-other"></a>

### GET `/other` — Augmented negative-risk Other size

The specification lists this specialized event/user lookup and a response containing `id`, `user`, and `size`. Use it only when your integration models the corresponding augmented negative-risk event. Live behavior was not tested.

| Parameter | Type | Default and allowed values |
| --- | --- | --- |
| `id` | integer | **Required**; min 1 |
| `user` | string | **Required** |

[Official augmented negative-risk other size source](https://docs.polymarket.com/api-spec/data-openapi.yaml)

<a id="endpoint-health"></a>

### GET `/` — Health check

The specification documents the root route and `{data: "OK"}`. Our root request succeeded. The rate-limit documentation separately names `/ok`; this guide's health example deliberately uses the route verified here.

No query parameters are documented.

[Official health check source](https://docs.polymarket.com/api-spec/data-openapi.yaml)

## Response fields, amounts, and PnL

### Positions: identity, valuation, and fee basis

| Fields | Interpretation and implementation rule |
| --- | --- |
| `proxyWallet`, `conditionId`, `asset` | Wallet, market condition, outcome asset; retain as strings and preserve protocol metadata. |
| `size`, `avgPrice`, `curPrice` | Remaining shares, average entry price, current price field. Do not confuse shares with collateral. |
| `initialValue`, `currentValue` | API-provided position entry/value measures; store the original fields for reconciliation. |
| `cashPnl`, `percentPnl`, `realizedPnl`, `percentRealizedPnl` | Separate reported P&L measures. Do not sum percentages across positions. |
| `grossInitialValue`, `entryFeesUsdc` | Optional remaining gross entry basis and its attributed BUY-fee component. Missing means unavailable, not zero. |
| `totalBought` | Cumulative bought quantity; it can differ from current size. |
| `redeemable`, `mergeable`, `negativeRisk` | Position/market flags; a read response does not execute the corresponding operation. |
| `outcome`, `outcomeIndex`, `oppositeAsset`, `oppositeOutcome` | Outcome mapping; validate against market metadata. |
| `title`, `slug`, `eventSlug`, `icon`, `endDate` | Display metadata; render text safely and tolerate missing values. |

For the documented optional fee fields, the fee-exclusive remaining basis is `grossInitialValue - entryFeesUsdc`. SELL fees are outside that entry-fee component. Avoid inventing zeros when a deployment omits optional fields. The live sample included both fee fields and an additional `eventId` field, illustrating why clients should tolerate additive response fields. [Position schema](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)

For an **illustrative mark-to-price calculation**, 100 shares bought at 0.40 and marked at 0.55 have a fee-exclusive basis of 40, marked value of 55, and unrealized difference of 15 before other adjustments. This arithmetic explains a simple position; it is not a replacement for the API's accounting conventions, partial-sales accounting, or executable liquidation pricing.

### Trades and activity are different records

A trade record supplies `side`, `size`, `price`, `timestamp`, `asset`, `conditionId`, and `transactionHash` along with wallet/display metadata. `size * price` is a simple trade-notional calculation, not guaranteed net cash movement after fees. Retain API source values and acquisition timestamps for reconciliation. [Trade schema](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets)

Activity additionally distinguishes transfers, splits, merges, redemptions, rewards, and other lifecycle events. On documented redemption rows, `size` is the outcome-token quantity burned and `usdcSize` is that outcome's payout. One redemption can produce multiple rows; losing-outcome rows can have zero payout. `outcomeIndex=999` means unknown, and some non-token rows can have an empty `asset` or `side`. Do not coerce these into a Yes/No trade. [Activity schema](https://docs.polymarket.com/api-reference/core/get-user-activity)

**A transaction hash alone is not a unique row key.** Multiple fills, outcomes, or operations may share a transaction. Prefer an actual record ID or transaction/log identity where supplied. Ordinary trade/activity schemas do not expose a universal unique event ID: preserve raw records and document the limitations of any composite deduplication key. Dropping every repeated hash loses valid data.

### Precision, timestamps, and collateral terminology

- Keep token IDs and hashes as strings end to end.
- Parse Unix-second timestamps explicitly: JavaScript dates need `timestamp * 1000`.
- Parse decimal strings directly with a decimal library; in Python use `Decimal` at JSON ingestion for numeric amounts when precision matters.
- Preserve `null`, missing, empty string, and numeric zero as different states.
- Existing response names such as `usdcSize` and `entryFeesUsdc` are API field names. Current collateral documentation describes pUSD on Polygon. Do not infer the transferred token contract from a field suffix; use chain/contract metadata for settlement reconciliation. [Official pUSD documentation](https://docs.polymarket.com/concepts/pusd)

## Pagination and complete history exports

### Offset pagination has endpoint-specific caps

`/positions`, `/closed-positions`, `/trades`, and `/activity` return arrays. Pass explicit `limit` and `offset`, keep filters fixed, advance by the returned row count, and stop on a short/empty page. A full page at your request budget or offset cap is **incomplete**, not a successful full export. The supplied Python pager raises in this situation.

| Route | Max limit | Max offset | Deeper-history approach |
| --- | --- | --- | --- |
| `/positions` | 500 | 10,000 | Narrow market/event filters; current state is not a historical archive. |
| `/closed-positions` | 50 | 100,000 | Narrow market/event filters; no start/end parameters in the retrieved schema. |
| `/trades` | 10,000 | 10,000 | Use supported start/end windows, with scope limits below. |
| `/activity` | 500 | 5,000 | Use supported start/end windows. |

Do not reuse these array rules for `/holders`, market-position groups, or combo response objects. For `/v1/market-positions`, paginate each token's group consistently and stop only when every returned token group is short. For combo endpoints, use the opaque next cursor until exhausted; keep query scope and sort unchanged. [Market-position pagination](https://docs.polymarket.com/api-reference/core/get-positions-for-a-market), [combo pagination](https://docs.polymarket.com/api-reference/core/get-user-combo-positions)

### Default history windows can hide older records

The retrieved trade specification says an omitted or zero `start` uses approximately the most recent three years. A positive start such as `1` permits older history for **user-scoped** trade requests. Market/event-scoped trade requests retain the approximately three-year floor even with an earlier start. This is a documented behavior, not a completeness guarantee for every account.

For activity, omitted/zero `start` also normally uses approximately three years; a positive start requests earlier history. The documented exception is `sortDirection=ASC` without `start`, which reads from the beginning of account history. Use an explicit start/end and sort in reproducible exports. [Trade window specification](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets), [activity window specification](https://docs.polymarket.com/api-reference/core/get-user-activity)

### A defensible historical export procedure

1. Record wallet, filters, UTC extraction time, and an explicit fixed `end` time.
2. Request a bounded `start`/`end` window and paginate within that window.
3. If you reach the offset/page budget with full pages, split the window and restart the subranges. Save only ranges whose completion is established.
4. Reconcile boundary timestamps. Verify endpoint inclusivity before using disjoint second ranges; if overlap is needed, retain row identity and multiplicity rather than deduplicating by transaction hash.
5. If a single-second bucket still exceeds the endpoint's accessible pagination, stop and label the export incomplete. Add market filters or use an appropriate indexed onchain dataset; do not silently skip the bucket.
6. Store raw responses plus normalized rows. For incremental ingestion, overlap the last watermark to catch delayed indexing, upsert safely, and periodically reconcile.

A changing current-position collection is not an atomic snapshot across pages. An API index can also lag the chain or UI. Record what you observed; an empty result does not establish that a wallet never traded.

## Python: read positions with bounded retries

The repository includes a standard-library Python client with timeouts, bounded retry/backoff, `Retry-After` handling, decimal parsing, CSV query arrays, and an explicit incomplete-result error. It does not need API credentials.

```bash
python3 examples/data_api.py
python3 examples/data_api.py --user "$POLY_WALLET"
python3 -m unittest discover -s tests -v
```

A minimal single-page example:

```python
import json
import os
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

query = urlencode({
    "user": os.environ["POLY_WALLET"],
    "sizeThreshold": 0,
    "includeArchived": "true",
    "limit": 100,
})
request = Request(
    "https://data-api.polymarket.com/positions?" + query,
    headers={"Accept": "application/json"},
)
with urlopen(request, timeout=20) as response:
    positions = json.load(response, parse_float=Decimal)
if not isinstance(positions, list):
    raise TypeError("Expected positions array")
for position in positions:
    print(position.get("title"), position.get("outcome"),
          position.get("size"), position.get("currentValue"))
```

This snippet intentionally reads one page. Use the [full Python client](https://github.com/geenes/polymarket-data-api-guide/blob/main/examples/data_api.py) for bounded pagination. The CLI serializes Decimal values as strings to preserve precision; account for that if consuming its output.

## JavaScript: fetch trades with Node.js

Requires Node.js 22+ for the supplied script. This small example checks HTTP status and applies a timeout. For long-running ingestion add bounded retry, pacing, persistence, and schema validation.

```javascript
const url = new URL("https://data-api.polymarket.com/trades");
url.searchParams.set("limit", "2");
url.searchParams.set("takerOnly", "true");

const response = await fetch(url, {
  headers: { Accept: "application/json" },
  signal: AbortSignal.timeout(20_000),
});
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const trades = await response.json();
if (!Array.isArray(trades)) throw new TypeError("Expected trade array");
for (const trade of trades) {
  console.log({
    assetId: trade.asset, // Keep this string; never Number(trade.asset).
    timestamp: new Date(trade.timestamp * 1000).toISOString(),
    side: trade.side,
    size: trade.size,
    price: trade.price,
  });
}
```

Run the [complete JavaScript example](https://github.com/geenes/polymarket-data-api-guide/blob/main/examples/data-api.mjs) with `node examples/data-api.mjs`. Native JSON parsing uses JavaScript numbers for numeric amounts. Use lossless JSON parsing and decimal arithmetic for accounting; converting an already-rounded float to a decimal cannot recover lost precision.

## Recipes for dashboards and research

### Build a wallet portfolio view

1. Resolve the holding/profile wallet and fetch current positions with an explicit size threshold.
2. Fetch `/value` for the same intended market scope; label the metric **position value**.
3. Fetch closed positions separately. Show realized and unrealized measures with clear definitions.
4. Fetch activity for redemptions, rewards, and other flows; explicitly include deposits/withdrawals if needed.
5. Include combo positions separately when the product supports them. Do not assume vanilla `/positions` describes all combo exposure.
6. Display extraction time and query scope, and flag partial pagination. Reconcile against an accounting snapshot or underlying records before presenting lifetime P&L.

### Export wallet cash-flow activity

```bash
# Set explicit Unix-second bounds suitable for your export.
export POLY_START=1
export POLY_END=$(date +%s)

curl --fail-with-body --max-time 20 --get \
  'https://data-api.polymarket.com/activity' \
  --data-urlencode "user=$POLY_WALLET" \
  --data-urlencode 'excludeDepositsWithdrawals=false' \
  --data-urlencode "start=$POLY_START" \
  --data-urlencode "end=$POLY_END" \
  --data-urlencode 'sortBy=TIMESTAMP' \
  --data-urlencode 'sortDirection=ASC' \
  --data-urlencode 'limit=100'
```

That is the first page, not a complete lifetime export. For only deposits and withdrawals add `type=DEPOSIT,WITHDRAWAL`; keep `excludeDepositsWithdrawals=false`. Separate deposit/withdrawal cash flows from trading returns before computing performance.

### Download accounting CSVs

```bash
curl --fail-with-body --max-time 30 --get \
  'https://data-api.polymarket.com/v1/accounting/snapshot' \
  --data-urlencode "user=$POLY_WALLET" \
  --output polymarket-accounting.zip
unzip -l polymarket-accounting.zip
```

Check the response status and ZIP contents before parsing. Keep the snapshot with its extraction time. The ZIP content type differs from normal JSON responses. [Accounting snapshot reference](https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs)

### Analyze market participation

Join Gamma market metadata to Data API rows by `conditionId`, and to outcome-level CLOB data by explicit asset mappings. Preserve CTF token IDs and PolyV2 position IDs separately. Use `/holders` for the top 20 per token; use `/v1/market-positions` for paginated positions. A wallet is an address, not a verified unique person. A top-holder sample cannot establish the ownership distribution of all participants.

For reproducible trader analysis, freeze leaderboard period/category filters, record sampling criteria, and retain both open and closed exposure. A high P&L rank alone does not establish predictive skill; volume, unrealized exposure, cash flows, and selection effects change the interpretation.

### Add real-time prices or price history

Use CLOB `/book` or `/price` with the endpoint's documented asset parameter for current book/price data; current unified SDKs expose protocol-neutral `assetId` / `asset_id`. For CTF-only direct requests the documented parameter remains `token_id`; `/prices-history` is the adjacent historical-price surface. Use the public market WebSocket for streaming book updates, then reconcile with REST snapshots after disconnects. Data API trade polling is useful for recorded activity, but is not a substitute for an order-book feed. Follow the official stream's current subscription and reconnection protocol. [Polymarket prices and order books](https://docs.polymarket.com/market-data/prices-order-books), [real-time data](https://docs.polymarket.com/market-data/realtime-data)

## Rate limits, errors, and production operation

The official IP-based limits reviewed on September 7, 2026 are:

| Data API scope | Documented ceiling |
| --- | --- |
| General | 1,000 requests / 10 seconds |
| `/trades` | 200 requests / 10 seconds |
| `/positions` | 150 requests / 10 seconds |
| `/closed-positions` | 150 requests / 10 seconds |
| `/ok` health check | 100 requests / 10 seconds |

The provider describes Cloudflare throttling as delaying/queuing excess requests, with sliding windows. Plan below both relevant endpoint and general limits, share budgets across workers on the same public IP, and handle timeouts/429 responses defensively. These figures are not a latency SLA. [Official API rate limits](https://docs.polymarket.com/api-reference/rate-limits)

| Symptom | What to inspect |
| --- | --- |
| HTTP 400 | Wallet/hash formats; `market` vs `eventId`; enum casing; paired trade filters; offset cap; timestamp units. |
| HTTP 401/403 | Correct service/route, actual response body, and access rules. Public Data API calls do not require invented credentials; authenticated CLOB routes do. |
| HTTP 429, growing latency, timeout | Pacing and shared IP budget; honor Retry-After when present; bounded exponential backoff with jitter. |
| HTTP 500/502/503/504 | Retry a bounded number of read requests; preserve evidence and surface failure after the budget. |
| Empty positions | Correct holding wallet; size threshold; archive/filter settings; whether positions are current, closed, or combos. |
| Missing old activity | Default history window, pagination cap, unsupported filter, indexing lag. |
| Repeated or skipped records | Moving datasets, timestamp boundaries, unsafe deduplication, grouped pagination. |
| P&L differs from UI | Query scope, acquisition time, fees, open/closed state, cash flows, combos, valuation source. |
| JSON parser fails | Non-JSON error page or the ZIP snapshot route; check status and Content-Type. |

Recommended client behavior: use timeouts, bounded retries for safe reads, structured error logs, a modest concurrency limit, and caching appropriate to the dataset. Preserve HTTP failures rather than translating them to empty arrays or zero balances. Validate required identifiers while tolerating new response fields. Never ship signing secrets in browser code; public read examples do not need them.

## Frequently asked developer questions

### Does Polymarket have API V2 and V3?

Yes: CLOB V2 and PolyV2/Exchange V3 are official, distinct versioned components. They do not imply a global Data API `/v2` or `/v3` prefix. Use the [version compatibility table](#polymarket-api-versions-v1-v2-polyv2-and-exchange-v3) and the current unified SDKs for the documented V3 routing.

### Which official SDK should I install?

For a new multi-service integration, use `@polymarket/client` for TypeScript/JavaScript or `polymarket-client` for Python. Both were verified at 0.9.0 on the review date. Their runtime requirements and older V2 alternatives appear in the [SDK directory](#official-documentation-and-sdk-directory).

### Is a PolyV2 position ID the same as a CTF token ID?

No. Both can identify assets, but they belong to different position systems. A market can expose both mappings. Preserve the protocol metadata and the IDs as strings, and do not assume the mere presence of a mapped position ID means the V3 market is accepting orders.

### Does the Polymarket Data API need an API key?

The public Data API reads documented here do not require an API key. Our live checks used no authentication headers. Private CLOB account/trading operations have a separate authentication model. [Official API guide](https://docs.polymarket.com/getting-started/api)

### How do I get all positions for a Polymarket wallet?

Use `/positions?user=…&sizeThreshold=0`, add `includeArchived=true` if archived-market holdings belong in scope, and paginate within the documented cap. Fetch `/closed-positions` and combo positions separately when needed. A single page is not all positions.

### How do I find a Polymarket market's condition ID?

Retrieve the market from Gamma and read `conditionId`. For Data API `market`, use that hash rather than Gamma's numeric `id` or the token ID. Parse Gamma's token/outcome arrays before mapping CLOB tokens.

### Why are deposits and withdrawals missing from activity?

They are excluded by default. Pass `excludeDepositsWithdrawals=false`; requesting those `type` values alone is insufficient. [Activity filtering reference](https://docs.polymarket.com/api-reference/core/get-user-activity)

### Can I fetch every trade ever made on Polymarket?

The public trade endpoint has scope-dependent history windows and an offset cap. User-scoped time windows can reach older history as documented; market/event queries retain their documented floor. A market-wide full archive requires a completeness strategy beyond repeatedly increasing offset. Label coverage gaps explicitly.

### Can I get more than 20 holders?

`/holders` caps results at 20 per outcome token and exposes no offset. `/v1/market-positions` offers a paginated market-position view with its own filters and response shape. [Holder reference](https://docs.polymarket.com/api-reference/core/get-top-holders-for-markets)

### Is position value the same as wallet balance or profit?

No. `/value` reports position value. Cash balance, deposited funds, realized profit, current exposure, and marked liquidation value are distinct metrics. Define the desired metric before combining API fields.

### Are API amounts cents, shares, or onchain base units?

Field meanings differ. `size` is a token quantity on ordinary position/trade rows; prices and value fields are separate measures. Combo fields can be decimal strings. Preserve documented response units and do not multiply every returned amount by one million merely because a settlement token has six decimals.

### Why do tutorials disagree on maximum page sizes?

References age and routes differ. In the retrieved specification, trades allow a limit up to 10,000, activity up to 500, closed positions up to 50, and holders up to 20. Pin source dates and endpoint paths rather than applying a single global page size.

## Validation, sources, and maintenance

### What was actually checked

The maintainer's publishing workflow retrieved the official documentation/specification and performed read-only requests on September 7, 2026. The [validation record](https://github.com/geenes/polymarket-data-api-guide/blob/main/VALIDATION.md) records the sampled routes, response shapes, example checks, and limitations. Tiny public samples establish accessibility and observed field shape, not exhaustive correctness, history completeness, or rate-limit capacity.

The live checks observed an additional `eventId` in position rows. The approvals request failed with HTTP 500. Combo routes returned valid empty collections, so populated combo accounting was not validated. Optional schema fields and new routes should be integrated with explicit missing-data handling.

### Primary sources and provenance

- [Official Data API OpenAPI specification](https://docs.polymarket.com/api-spec/data-openapi.yaml): endpoint/parameter inventory and response schema, retrieved September 7, 2026.
- [Official Polymarket API guide](https://docs.polymarket.com/getting-started/api): integration surfaces and authentication.
- [Market discovery](https://docs.polymarket.com/market-data/discover-markets) and [wallet activity](https://docs.polymarket.com/trading/wallet-activity): adjacent workflows.
- [Rate limits](https://docs.polymarket.com/api-reference/rate-limits): dated operational ceilings.
- [Prediction-market changelog](https://docs.polymarket.com/changelog/predictions): a starting point for future reviews.
- [Shaun Lebron's original Data API gist](https://gist.github.com/shaunlebron/0dd3338f7dea06b8e9f8724981bb13bf): inspiration for the compact Markdown reference format and historical comparison. This guide uses independently written explanations and examples grounded in current primary sources; it is not a copy of that gist.

Endpoint-specific citations appear beside each reference section. The retrieved OpenAPI version label is `1.0.0`; this label alone should not be treated as proof that the schema is unchanged. The validation record includes a SHA-256 of the exact source used and the SDK versions checked. The first edition focused on Data API routes; this revision corrects its missing V2/V3 and unified-SDK coverage.

### Corrections and updates

Open an issue with endpoint, sanitized query, UTC observation time, expected behavior, actual status/response shape, and an official source if available. Remove credentials and private information. Keep historical validation dates intact; advance the review date only after rechecking the affected content. When implementation and documentation differ, report both rather than silently rewriting one as the other.
