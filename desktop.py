"""Windowed entry point for the standalone Windows distribution."""
import json
import logging
import sys
import threading
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

import app


def smoke_test():
    import tempfile
    import webview
    with tempfile.TemporaryDirectory() as directory:
        application = app.Application(directory)
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.make_handler(application))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            for path in ('/', '/app.js', '/planner.js', '/planner.css'):
                with urllib.request.urlopen(base + path) as response:
                    assert response.status == 200 and response.read()
            with urllib.request.urlopen(base + '/api/state') as response:
                state = json.load(response)
            assert not state['courses'] and state['planner']['courses']
        finally:
            server.shutdown(); server.server_close(); application.pool.shutdown()


def main():
    if '--smoke-test' in sys.argv:
        smoke_test()
        return
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CS.Tracker.Desktop')
    from tracker.store import data_directory
    directory = data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=directory / 'desktop.log', level=logging.ERROR)
    # Windowed executables have no stdout/stderr handles.
    log = (directory / 'desktop.log').open('a', encoding='utf-8')
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log
    try:
        sys.argv = [sys.argv[0], '--desktop']
        app.main()
    except Exception:
        logging.exception('Desktop startup failed')
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f'CS Tracker could not start. See {directory / "desktop.log"} for details.\n\nMake sure Microsoft Edge WebView2 Runtime is installed.', 'CS Tracker', 0x10)
        raise
    finally:
        log.close()


if __name__ == '__main__':
    main()
