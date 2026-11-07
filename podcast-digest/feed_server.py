#!/usr/bin/python3
"""Private podcast feed server for podcast-digest.

Serves only podcast-digest/public/, bound to one address (home network or VPN), never the open internet.
Unlike `python3 -m http.server`, it answers byte-range requests (206 Partial Content), which
Apple Podcasts and Overcast need to stream and download episodes. No directory listings.

Usage: feed_server.py <bind-address> <port> <public-dir>
Run by Apple's /usr/bin/python3 from the launchd agent local.podcast-digest.feed.
"""
import http.server
import os
import re
import sys
from functools import partial

TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".xml": "application/rss+xml; charset=utf-8"}


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def list_directory(self, path):  # never list folders
        self.send_error(404)
        return None

    def guess_type(self, path):
        return TYPES.get(os.path.splitext(path)[1].lower()) or super().guess_type(path)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.isfile(path):
            self.send_error(404)
            return None
        size = os.path.getsize(path)
        f = open(path, "rb")
        m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", "").strip())
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:  # suffix range: the last N bytes
                start, end = max(0, size - int(m.group(2))), size - 1
            end = min(end, size - 1)
            if start > end or start >= size:
                f.close()
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            f.seek(start)
            self.send_response(206)
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            length = end - start + 1
        else:
            self.send_response(200)
            length = size
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
        self.end_headers()
        self._remaining = length
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_remaining", None)
        while left is None or left > 0:
            chunk = source.read(65536 if left is None else min(65536, left))
            if not chunk:
                break
            outputfile.write(chunk)
            if left is not None:
                left -= len(chunk)


def main():
    bind, port, root = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    server = http.server.ThreadingHTTPServer((bind, port), partial(Handler, directory=root))
    server.serve_forever()


if __name__ == "__main__":
    main()
