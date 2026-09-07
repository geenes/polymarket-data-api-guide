// Read-only Node.js 22+ example. Token IDs remain strings.
const DATA_API = 'https://data-api.polymarket.com';

export async function getData(path, params = {}) {
  const url = new URL(path, DATA_API);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, Array.isArray(value) ? value.join(',') : String(value));
    }
  }
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  return response.json();
}

const trades = await getData('/trades', { limit: 2, takerOnly: true });
if (!Array.isArray(trades)) throw new TypeError('Expected trade array');
console.log(trades.map(row => ({
  wallet: row.proxyWallet,
  conditionId: row.conditionId,
  tokenId: row.asset, // Never Number(row.asset).
  time: new Date(row.timestamp * 1000).toISOString(),
  side: row.side,
  size: row.size,
  price: row.price,
})));
// JavaScript numbers are adequate for display, but use a lossless JSON parser
// and decimal arithmetic for accounting. This short example does not retry.
