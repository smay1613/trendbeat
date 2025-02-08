import http.server
import os
import socketserver

# Получаем порт из переменной окружения, требуется Render
PORT = int(os.getenv("PORT", 8080))

class MinimalHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")  # Ответ "OK" на любой запрос

def run_web_server():
    with socketserver.TCPServer(("", PORT), MinimalHandler) as httpd:
        httpd.serve_forever()