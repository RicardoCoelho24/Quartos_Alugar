from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class Handler(BaseHTTPRequestHandler):
    # Responde quando se abre a página no navegador
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"O Bot dos Quartos esta vivo e a correr!")

    # Responde quando o UptimeRobot "bate à porta" furtivamente
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def run():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

def manter_vivo():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()