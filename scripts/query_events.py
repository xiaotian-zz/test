import sqlite3
db = r'F:\rf4_server\rf4_server_simulator\data\rf4server.db'
c = sqlite3.connect('file:F:/rf4_server/rf4_server_simulator/data/rf4server.db?mode=ro&immutable=1', uri=True)
c.execute('pragma busy_timeout=3000')
for (name,) in c.execute("select name from sqlite_master where type='table'"):
    print('T', name)
for row in c.execute("select * from tunables where key like '%event%' or key like '%newyear%'"):
    print(row)
