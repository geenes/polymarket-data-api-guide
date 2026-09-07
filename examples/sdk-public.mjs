// Official @polymarket/client 0.9.0; Node.js >=24. Public reads only.
// Install in this directory with: npm install --ignore-scripts
import { createPublicClient } from '@polymarket/client';

const client = createPublicClient();
const markets = await client.listMarkets({ closed: false, pageSize: 2 }).firstPage();
for (const market of markets.items) {
  console.log(JSON.stringify({
    kind: 'market', id: market.id, version: market.version,
    conditionId: market.conditionId, comboStatus: market.state.comboStatus,
    // Keep both IDs. A mapped positionId can exist on a v1 market.
    outcomes: market.outcomes,
  }));
}
const trades = await client.listTrades({ pageSize: 2 }).firstPage();
for (const trade of trades.items) {
  console.log(JSON.stringify({
    kind: 'trade', conditionId: trade.conditionId, assetId: trade.assetId,
    price: trade.price, size: trade.size,
    // SDK timestamps are milliseconds; raw Data API trade timestamps are seconds.
    timestamp: new Date(trade.timestamp).toISOString(),
  }));
}
console.log(JSON.stringify({ kind: 'pagination', hasMore: markets.hasMore,
  nextCursor: markets.nextCursor ?? null, completeCatalogue: false }));
// Optional public book read for a known, currently supported asset ID.
if (process.env.POLY_ASSET_ID) {
  const book = await client.fetchOrderBook({ assetId: process.env.POLY_ASSET_ID });
  console.log(JSON.stringify({ kind: 'book', assetId: book.assetId,
    conditionId: book.conditionId, bids: book.bids.length, asks: book.asks.length }));
}
// Exceptions propagate and the process exits nonzero; errors are never empty data.
