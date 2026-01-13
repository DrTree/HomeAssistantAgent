import http.server
import socketserver

PORT = 5050


class StubHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Stub Home Assistant add-on server is running.\n")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), StubHandler) as httpd:
        print(f"Serving stub add-on on port {PORT}")
        httpd.serve_forever()
