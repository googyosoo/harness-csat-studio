# Copyright 2026 Google LLC / Jinwoo CSAT AI Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Single-command launcher for Harness² CSAT Studio."""

import socket
import sys
import threading
import time
import webbrowser
import uvicorn


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_browser(url: str):
    time.sleep(1.2)
    print(f"\n[Browser] Opening Harness² CSAT Studio in your browser: {url}")
    webbrowser.open(url)


def main():
    port = 8000
    while is_port_in_use(port):
        port += 1

    url = f"http://127.0.0.1:{port}"
    print("=" * 70)
    print("  🚀 Harness² CSAT Studio — Autonomous Question Generation Platform")
    print(f"  🔗 Local Studio URL: {url}")
    print("  📖 Reading Killers: Grammar, Blank, Order, Insertion")
    print("  🎧 Listening Killers: Responses, Math Calc, Table, Long Dialogue")
    print("  📄 Formats: Student/Teacher HWPX Worksheets & Neural MP3 Audio")
    print("=" * 70)

    # Launch browser in separate thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Run uvicorn server
    uvicorn.run("studio.server:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
