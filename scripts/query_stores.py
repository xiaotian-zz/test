import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else 'F:/rf4_server/rf4_server_simulator/data/rf4server.db'
c = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
tables = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
print('tables:', tables)
if 'shop_item' in tables:
    rows = list(c.execute(
        "select distinct store_id from shop_item where store_id like '%bazaar%' or store_id like '%baazar%' "
        "or store_id like '%christmas%' order by store_id"))
    print('bazaar stores:', len(rows))
    for r in rows:
        print('  ', r[0])
    print('all store count:', c.execute('select count(distinct store_id) from shop_item').fetchone()[0])
