"""Offline regression tests: python3 -m unittest discover -s tests -v"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'mihomoctl.sh'

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.lib = self.home / 'functions.sh'
        self.lib.write_text(SCRIPT.read_text().rsplit('main "$@"', 1)[0])
        self.env = dict(os.environ, MIHOMO_HOME=str(self.home), MIHOMO_SHELL_RC=str(self.home / 'bashrc'))
        self.env.pop('MIHOMO_SELECTOR', None)
        self.env.pop('MIHOMO_PORT', None)
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.tmp.cleanup()

    def run_shell(self, code, ok=True):
        result = subprocess.run(['bash', '-c', 'source "$1"; ' + code, 'test', str(self.lib)], env=self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def api(self, groups):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/proxies':
                    self.send_error(404)
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'proxies': groups}).encode())
            def log_message(self, *args):
                pass
        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        (self.home / 'config.yaml').write_text(f'external-controller: 127.0.0.1:{self.server.server_port}\nsecret: ""\nmixed-port: 7898\n')

    def test_arbitrary_selector_and_proxy_bypass(self):
        self.api({'Provider A': {'name': 'Provider A', 'type': 'Selector', 'all': ['US 01'], 'now': 'US 01'}})
        self.env.update(HTTP_PROXY='http://127.0.0.1:1', http_proxy='http://127.0.0.1:1', ALL_PROXY='socks5://127.0.0.1:1')
        data = json.loads(self.run_shell('selector_json').stdout)
        self.assertEqual(data['name'], 'Provider A')

    def test_multiple_selectors_require_choice(self):
        self.api({g: {'name': g, 'type': 'Selector', 'all': [], 'now': ''} for g in ['A', 'B']})
        self.assertIn('set-selector', self.run_shell('selector_json', ok=False).stderr)
        self.run_shell('cmd_set_selector B')
        self.assertEqual(json.loads(self.run_shell('selector_json').stdout)['name'], 'B')

    def test_regions_and_exact_match(self):
        for nodes, query, expected in [(['Australia', 'US 01'], 'US', 'US 01'), (['美国 01'], 'US', '美国 01'), (['🇺🇸 01'], 'US', '🇺🇸 01'), (['US 01', 'US 02'], 'US 02', 'US 02')]:
            code = 'resolve_node ' + subprocess.list2cmdline([query]) + ' <<\'DATA\'\n' + json.dumps({'all': nodes}) + '\nDATA'
            self.assertEqual(self.run_shell(code).stdout.strip(), expected)

    def test_profiles_preserve_url_and_settings(self):
        self.run_shell("cmd_set_url 'https://example.test/path/key?x=1&sig=abc'; cmd_profile save old; cmd_profile add new 'https://other.test/private/key'; cmd_profile list")
        self.assertIn('sig=abc', (self.home / 'profiles/old.env').read_text())
        self.assertNotIn('flag=clash', (self.home / 'profiles/old.env').read_text())
        self.assertNotIn('DEFAULT_NODE=US', (self.home / 'profiles/new.env').read_text())
        self.assertEqual((self.home / 'profiles/new.env').stat().st_mode & 0o777, 0o600)
        self.run_shell("cmd_profile add ../bad https://example.test", ok=False)

    def test_failed_profile_fetch_keeps_active_files(self):
        self.run_shell("cmd_set_url https://old.test; cmd_profile save old; cmd_profile add new https://new.test")
        (self.home / 'config.yaml').write_text('mixed-port: 7898\n')
        old_env = (self.home / 'subscription.env').read_text()
        self.run_shell('download_to() { return 1; }; cmd_profile use new', ok=False)
        self.assertEqual((self.home / 'config.yaml').read_text(), 'mixed-port: 7898\n')
        self.assertEqual((self.home / 'subscription.env').read_text(), old_env)

    def test_saved_port_and_hidden_url(self):
        (self.home / 'config.yaml').write_text('mixed-port: 7898\n')
        self.assertEqual(self.run_shell('echo "$MIXED_PORT"').stdout.strip(), '7898')
        self.assertNotIn('private', self.run_shell('mask_url https://example.test/private').stdout)

if __name__ == '__main__':
    unittest.main()
