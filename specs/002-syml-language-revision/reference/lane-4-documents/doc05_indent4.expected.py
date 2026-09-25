SOURCE = '''server:
    host: localhost
    ports:
        - 80
        - 443
    tls:
        cert: /etc/cert.pem
clients:
    -   name: a
        id: 1
    -   name: b
        id: 2
'''
SPEC = {'server': {'host': 'localhost', 'ports': ['80', '443'], 'tls': {'cert': '/etc/cert.pem'}},
        'clients': [{'name': 'a', 'id': '1'}, {'name': 'b', 'id': '2'}]}
AUTHOR = SPEC
