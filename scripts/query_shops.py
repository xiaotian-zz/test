import sqlite3
c = sqlite3.connect('file:F:/rf4_server/rf4_server_simulator/data/rf4server.db?mode=ro&immutable=1', uri=True)
print('shop_item cols', [r[1] for r in c.execute('pragma table_info(shop_item)')])
for sid in ('ny_bazaarStore_012','ny_bazaarStore_006','fishingstore_012','fishingstore_006'):
    try:
        n = c.execute('select count(*) from shop_item where store_id=?', (sid,)).fetchone()[0]
        print(sid, n)
        for row in c.execute('select * from shop_item where store_id=? limit 3', (sid,)):
            print('  ', row)
    except Exception as e:
        print(sid, 'err', e)
