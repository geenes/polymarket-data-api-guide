"""Official polymarket-client 0.9.0; Python >=3.11. Public reads only."""
import json
import os
from polymarket import PublicClient


def main():
    with PublicClient() as client:
        markets = client.list_markets(closed=False, page_size=2).first_page()
        for market in markets.items:
            print(json.dumps({
                'kind': 'market', 'id': market.id, 'version': market.version,
                'conditionId': market.condition_id,
                'comboStatus': market.state.combo_status,
                'outcomes': market.outcomes.model_dump(mode='json'),
            }))
        trades = client.list_trades(page_size=2).first_page()
        for trade in trades.items:
            print(json.dumps({
                'kind': 'trade', 'conditionId': trade.condition_id,
                'assetId': trade.asset_id, 'price': str(trade.price),
                'size': str(trade.size), 'timestamp': trade.timestamp.isoformat(),
            }))
        print(json.dumps({'kind': 'pagination', 'hasMore': markets.has_more,
                          'nextCursor': markets.next_cursor,
                          'completeCatalogue': False}))
        if asset_id := os.environ.get('POLY_ASSET_ID'):
            book = client.get_order_book(asset_id=asset_id)
            print(json.dumps({'kind': 'book', 'assetId': book.asset_id,
                              'conditionId': book.condition_id,
                              'bids': len(book.bids), 'asks': len(book.asks)}))


if __name__ == '__main__':
    main()
