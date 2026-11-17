import sqlite3
c = sqlite3.connect('file:F:/rf4_server/rf4_server_simulator/data/rf4server.db?mode=ro&immutable=1', uri=True)
print('22 族:')
for row in c.execute('select main,sub,count(*) from request_receipts where main=22 group by main,sub order by sub'):
    print(row)
print('最近 22:')
for row in c.execute('select main,sub,created_at,status,length(response_body),has_response from request_receipts where main=22 order by rowid desc limit 30'):
    print(row)
