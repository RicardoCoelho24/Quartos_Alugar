from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Esta é a resposta que o Render vai ler para saber que está tudo OK
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"O Bot dos Quartos esta vivo e a correr!")

def run():
    # O Render exige que usemos a porta que eles nos dão na variável PORT
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

def manter_vivo():
    # Corre o servidor fantasma numa thread secundária para não bloquear o bot
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()