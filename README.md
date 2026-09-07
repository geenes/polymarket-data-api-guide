# Polymarket Data API Guide: Endpoints, Python & JavaScript Examples

Build Polymarket wallet trackers, portfolio dashboards, trade-history exports, and market analytics with the public **Polymarket Data API** at `https://data-api.polymarket.com`. This independent developer guide explains every route in the retrieved Data API specification, how to join Gamma market metadata, and how to avoid incomplete history, incorrect IDs, and misleading P&L calculations.

**Maintainer:** [geenes](https://github.com/geenes) · **Reviewed:** September 7, 2026 · **Scope:** Polymarket prediction-market Data API; Gamma/CLOB integration where needed. This is community documentation, not an official Polymarket product or a Perps/Polymarket US API reference.

**Start here:** no API key or private key is needed for these public read requests. Use Gamma for market discovery, Data API for positions and historical activity, and CLOB for order books and trading. The full guide lives in the [GitHub repository](https://github.com/geenes/polymarket-data-api-guide); report reproducible documentation problems through [repository issues](https://github.com/geenes/polymarket-data-api-guide/issues).

## Contents

- [Quick start: make your first API request](#quick-start-make-your-first-api-request)
- [Data API vs Gamma API vs CLOB API](#data-api-vs-gamma-api-vs-clob-api)
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
curl --fail-with-body --max-time 20 --get   'https://data-api.polymarket.com/trades'   --data-urlencode 'limit=2'   --data-urlencode 'takerOnly=true'
```

To read a wallet, replace the placeholder with its public profile/position-holding address. Do not paste a seed phrase or private key.

```bash
export POLY_WALLET='REPLACE_WITH_0x_WALLET_ADDRESS'

curl --fail-with-body --max-time 20 --get   'https://data-api.polymarket.com/positions'   --data-urlencode "user=$POLY_WALLET"   --data-urlencode 'sizeThreshold=0'   --data-urlencode 'includeArchived=true'   --data-urlencode 'limit=100'
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

## Wallet addresses, condition IDs, event IDs, and token IDs

Polymarket uses multiple identifiers. The Data API `market` filter expects a **condition ID**, not the numeric Gamma market ID, event ID, market slug, or outcome token ID.

| Identifier | Shape | Where to use it |
| --- | --- | --- |
| Profile/holding wallet | `0x` + 40 hexadecimal characters | Data API `user`; commonly returned as `proxyWallet` |
| Condition ID | `0x` + 64 hexadecimal characters | Data API `market`; Gamma `conditionId` |
| Question ID | `0x` + 64 hexadecimal characters | `questionID` for revisions; distinct from condition ID |
| Gamma market ID | Numeric ID, often represented as a string | Gamma market lookup |
| Event ID | Positive integer | `eventId` where supported; `id` on `/live-volume` |
| Outcome token ID | Large decimal string | CLOB `token_id`; Data API `asset` or holder `token` |
| Slug | Human-readable text | Gamma slug lookup and user-facing links |

A signer address and a proxy/deposit wallet need not be the same address. Resolve a supplied wallet through Gamma's public profile endpoint and inspect its `proxyWallet`; check it against a known position or trade before concluding the account is empty. Gamma accepts a proxy wallet or user address as the profile lookup input. [Public profile reference](https://docs.polymarket.com/api-reference/profiles/get-public-profile-by-wallet-address)

```bash
curl --fail-with-body --max-time 20 --get   'https://gamma-api.polymarket.com/public-profile'   --data-urlencode "address=$POLY_WALLET"
```

Discover a market and extract its condition ID with `jq`:

```bash
POLY_MARKET_JSON=$(curl --fail-with-body --max-time 20 --get   'https://gamma-api.polymarket.com/markets'   --data-urlencode 'closed=false' --data-urlencode 'limit=1')
export POLY_CONDITION_ID=$(printf '%s' "$POLY_MARKET_JSON" | jq -er '.[0].conditionId')

curl --fail-with-body --max-time 20 --get   'https://data-api.polymarket.com/holders'   --data-urlencode "market=$POLY_CONDITION_ID"   --data-urlencode 'limit=20'
```

Gamma may represent `outcomes`, `outcomePrices`, and `clobTokenIds` as JSON-encoded strings. Parse those values before indexing them, and match outcomes to token IDs by array position. Check equal array lengths. Keep token IDs as strings: conversion to a JavaScript `Number` can corrupt the identifier. A sample of one market is discovery, not a complete active-market catalogue. [Official market discovery guide](https://docs.polymarket.com/market-data/discover-markets)

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
| `proxyWallet`, `conditionId`, `asset` | Wallet, market condition, outcome token; retain as strings. |
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
    tokenId: trade.asset, // Keep this string; never Number(trade.asset).
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

curl --fail-with-body --max-time 20 --get   'https://data-api.polymarket.com/activity'   --data-urlencode "user=$POLY_WALLET"   --data-urlencode 'excludeDepositsWithdrawals=false'   --data-urlencode "start=$POLY_START"   --data-urlencode "end=$POLY_END"   --data-urlencode 'sortBy=TIMESTAMP'   --data-urlencode 'sortDirection=ASC'   --data-urlencode 'limit=100'
```

That is the first page, not a complete lifetime export. For only deposits and withdrawals add `type=DEPOSIT,WITHDRAWAL`; keep `excludeDepositsWithdrawals=false`. Separate deposit/withdrawal cash flows from trading returns before computing performance.

### Download accounting CSVs

```bash
curl --fail-with-body --max-time 30 --get   'https://data-api.polymarket.com/v1/accounting/snapshot'   --data-urlencode "user=$POLY_WALLET"   --output polymarket-accounting.zip
unzip -l polymarket-accounting.zip
```

Check the response status and ZIP contents before parsing. Keep the snapshot with its extraction time. The ZIP content type differs from normal JSON responses. [Accounting snapshot reference](https://docs.polymarket.com/api-reference/misc/download-an-accounting-snapshot-zip-of-csvs)

### Analyze market participation

Join Gamma market metadata to Data API rows by `conditionId`, and to outcome-level CLOB data by token ID. Use `/holders` for the top 20 per token; use `/v1/market-positions` for paginated positions. A wallet is an address, not a verified unique person. A top-holder sample cannot establish the ownership distribution of all participants.

For reproducible trader analysis, freeze leaderboard period/category filters, record sampling criteria, and retain both open and closed exposure. A high P&L rank alone does not establish predictive skill; volume, unrealized exposure, cash flows, and selection effects change the interpretation.

### Add real-time prices or price history

Use CLOB `/book` or `/price` with an outcome token ID for current book/price data; `/prices-history` is the adjacent historical-price surface. Use the public market WebSocket for streaming book updates, then reconcile with REST snapshots after disconnects. Data API trade polling is useful for recorded activity, but is not a substitute for an order-book feed. Follow the official stream's current subscription and reconnection protocol. [Polymarket prices and order books](https://docs.polymarket.com/market-data/prices-order-books), [real-time data](https://docs.polymarket.com/market-data/realtime-data)

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

Endpoint-specific citations appear beside each reference section. The retrieved OpenAPI version label is `1.0.0`; this label alone should not be treated as proof that the schema is unchanged. The validation record includes a SHA-256 of the exact source used.

### Corrections and updates

Open an issue with endpoint, sanitized query, UTC observation time, expected behavior, actual status/response shape, and an official source if available. Remove credentials and private information. Keep historical validation dates intact; advance the review date only after rechecking the affected content. When implementation and documentation differ, report both rather than silently rewriting one as the other.
