"""Build the hosted-artifact fragment from web/index.html (HANDOFF section 3).

The claude.ai artifact service wraps whatever we publish in its own
<html><head>...<body> skeleton, so the page we hand it is a FRAGMENT:
the <title>, the <style> block (plus two rules that pin the dark page
background and the centered 720px column inside the host's body), and
everything between our <body> tags. This is byte-identical to the
fragment that was live at v0.9.1.

Usage:
    python tools/artifact_fragment.py <out.html>

Then publish <out.html> with the Artifact tool to the SAME url (see
HANDOFF.md section 3 / section 6).
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "web", "index.html")


def build_fragment(src):
    style = re.search(r"<style>(.*?)</style>", src, re.S)
    body = re.search(r"<body>\n(.*)</body>", src, re.S)
    if not style or not body:
        raise SystemExit("web/index.html: could not find <style> or <body> blocks")
    return (
        "<title>DelveForge</title>\n<style>\nhtml,body{background:#14141b;}"
        + style.group(1)
        + "#df-root{max-width:720px;margin:1rem auto;font-family:system-ui,sans-serif;}\n</style>\n"
        + body.group(1)
    )


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = argv[1]
    with io.open(HTML, encoding="utf-8", newline="") as f:
        src = f.read()
    frag = build_fragment(src)
    with io.open(out, "w", encoding="utf-8", newline="") as f:
        f.write(frag)
    print("wrote %s (%d bytes)" % (out, len(frag.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
