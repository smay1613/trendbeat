import http.server
import os
import socketserver

# Получаем порт из переменной окружения, требуется Render
PORT = int(os.getenv("PORT", 8080))

class MinimalHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик HTTP-запросов, отвечающий 'OK'."""
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")  # Ответ "OK" на любой запрос

def run_web_server():
    """Запуск веб-сервера в фоне."""
    with socketserver.TCPServer(("", PORT), MinimalHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()