from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import urllib
import mimetypes
import socket
from multiprocessing import Process
import json
import urllib.parse

BASE_DIR = Path(__file__).parent
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = "0.0.0.0"
SOCKET_HOST = "localhost"
SOCKET_PORT = 5000

try:
    with open(BASE_DIR / "storage/data.json", 'r') as file:
        STORAGE_DATA = json.load(file)
except json.decoder.JSONDecodeError:
    STORAGE_DATA = []

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)

        match route.path:
            case "/":
                self._send_html(BASE_DIR / "index.html")
            case "/message":
                self._send_html(BASE_DIR / "message.html")
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self._send_static(file)
                else:
                    self._send_html(BASE_DIR / "error.html", 404)

    def do_POST(self):
        size = self.headers.get("Content-Length")
        data = self.rfile.read(int(size))

        self._send_data_to_socket_server(data)

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def _send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def _send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type = mimetypes.guess_type(filename)
        self.send_header("content-type", mime_type[0])
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def _send_data_to_socket_server(self, data: bytes):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))


def run_http_server():
    http_server = HTTPServer((HTTP_HOST, HTTP_PORT), MyHTTPRequestHandler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def run_socket_server():
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((SOCKET_HOST, SOCKET_PORT))

    while True:
        message, _ = socket_server.recvfrom(BUFFER_SIZE)
        with open(BASE_DIR / "storage/data.json", "w") as file:
            process_data(message.decode())
            json.dump(STORAGE_DATA, file, indent=4, ensure_ascii=False)


def process_data(data: str) -> dict:
    curr_datetime = str(datetime.now())
    curr_data = {curr_datetime: {}}
    data = urllib.parse.unquote_plus(data)

    for param in data.split("&"):
        key, value = param.split("=")
        curr_data[str(curr_datetime)][key] = value

    STORAGE_DATA.append(curr_data)


if __name__ == "__main__":
    socket_server_process = Process(target=run_socket_server)
    http_server_process = Process(target=run_http_server)

    socket_server_process.start()
    http_server_process.start()
