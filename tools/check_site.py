
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import sys

class SrcParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href'):
            value = attrs.get(key)
            if value and not value.startswith(('http://', 'https://', '#', 'mailto:', 'tel:', 'data:')):
                self.refs.append(value)

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('.').resolve()
index = root / 'index.html'
assert index.exists(), 'index.html not found'
parser = SrcParser()
parser.feed(index.read_text(encoding='utf-8'))
missing = []
for ref in parser.refs:
    path = (root / ref).resolve()
    if not path.exists():
        missing.append(ref)
if missing:
    raise SystemExit('Missing references: ' + ', '.join(missing))
print('OK: all local references exist')
