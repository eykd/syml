SOURCE = '''# Application config
app:
  name: widget-server
  host: 0.0.0.0
  port: 8080 # default port
  debug: false
  base-url: https://example.com:8443/api/v1?x=1&y=2
  data-dir: C:\\Users\\x\\AppData\\widget
  log-dir: /var/log/widget

hosts:
  - web1.example.com
  - web2.example.com
  - 10.0.0.3:8080

database:
  url: postgres://user:p@ss@db:5432/app
  pool:
    min: 1
    max: 10

env:
  - PATH=/usr/local/bin:/usr/bin
  - HOME=/home/widget

environment:
  DATABASE_URL: postgres://user@db/app
  SECRET_KEY: s3cr3t
'''
# `port` keeps the "# default port" text (§4.3). The final `environment:` block uses UPPERCASE keys;
# per §4.5 those lines are prose, so environment's value is the 2-line string. Silent.
SPEC = {
    'app': {
        'name': 'widget-server', 'host': '0.0.0.0', 'port': '8080 # default port', 'debug': 'false',
        'base-url': 'https://example.com:8443/api/v1?x=1&y=2',
        'data-dir': 'C:\\Users\\x\\AppData\\widget', 'log-dir': '/var/log/widget',
    },
    'hosts': ['web1.example.com', 'web2.example.com', '10.0.0.3:8080'],
    'database': {'url': 'postgres://user:p@ss@db:5432/app', 'pool': {'min': '1', 'max': '10'}},
    'env': ['PATH=/usr/local/bin:/usr/bin', 'HOME=/home/widget'],
    'environment': 'DATABASE_URL: postgres://user@db/app\nSECRET_KEY: s3cr3t',
}
AUTHOR = dict(SPEC, app=dict(SPEC['app'], port='8080'),
              environment={'DATABASE_URL': 'postgres://user@db/app', 'SECRET_KEY': 's3cr3t'})
