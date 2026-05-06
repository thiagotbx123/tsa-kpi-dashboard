#!/usr/bin/env python3
"""Push the KPI Playbook to Coda Solutions Central with Codex Box styling."""
import sys, os, json, requests, re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYBOOK_PATH = os.path.join(SCRIPT_DIR, 'KPI_PLAYBOOK_FOR_CODA.md')

DOC_ID = 'jfymaxsTtA'
PAGE_ID = 'canvas-j9xbMS1NeD'
API_BASE = 'https://coda.io/apis/v1'

env_path = os.path.join(SCRIPT_DIR, '..', '..', '.env')
TOKEN = None
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('CODA_API_TOKEN='):
                TOKEN = line.strip().split('=', 1)[1]
                break

if not TOKEN:
    print('ERROR: CODA_API_TOKEN not found in .env')
    sys.exit(1)

HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
}

EMOJI_MAP = {
    'OVERVIEW': '🔭',
    'KPI 1 — ETA ACCURACY': '🏹',
    'KPI 2 — IMPLEMENTATION VELOCITY': '🏎️',
    'KPI 3 — IMPLEMENTATION RELIABILITY': '💎',
    'THE TICKET LIFECYCLE — FROM CREATION TO KPI': '🧬',
    'DATA INTEGRITY RULES': '⚖️',
    'STATUS FLOW AND KPI IMPACT': '🚦',
    'CLASSIFICATION RULES': '🗂️',
    'READING THE DASHBOARD': '🖥️',
    'QUICK REFERENCE TABLE': '📌',
    'GLOSSARY': '🗝️',
    'KNOWN LIMITATIONS': '🚧',
    'OPEN QUESTIONS': '💬',
}

SEPARATOR = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'


def style_playbook(raw_md: str) -> str:
    """Apply Codex Box visual style to the playbook markdown."""
    lines = raw_md.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith('## ') and not line.startswith('### '):
            heading = line[3:].strip()
            emoji = ''
            for key, em in EMOJI_MAP.items():
                if key in heading:
                    emoji = em + ' '
                    break
            out.append(f'## {emoji}{heading}')
            out.append('')
            out.append(SEPARATOR)
            i += 1
            continue

        out.append(line)
        i += 1

    return '\n'.join(out)


def md_to_html(md: str) -> str:
    """Convert styled markdown to HTML that Coda preserves (emojis, separators).
    Optimizes by grouping list items and merging consecutive paragraphs."""
    import html as html_mod
    lines = md.split('\n')
    html_parts = []
    in_code = False
    code_buf = []
    list_buf = []
    table_buf = []

    def flush_list():
        nonlocal list_buf
        if list_buf:
            items = ''.join(f'<li>{html_mod.escape(li)}</li>' for li in list_buf)
            html_parts.append(f'<ul>{items}</ul>')
            list_buf = []

    def flush_table():
        nonlocal table_buf
        if table_buf:
            html_parts.append(f'<p>{html_mod.escape(chr(10).join(table_buf))}</p>')
            table_buf = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```') and not in_code:
            flush_list()
            flush_table()
            in_code = True
            code_buf = []
            continue
        if stripped.startswith('```') and in_code:
            in_code = False
            html_parts.append(f'<pre><code>{html_mod.escape(chr(10).join(code_buf))}</code></pre>')
            continue
        if in_code:
            code_buf.append(line)
            continue

        if not stripped:
            flush_list()
            flush_table()
            continue

        if stripped.startswith('- '):
            flush_table()
            list_buf.append(stripped[2:])
            continue

        flush_list()

        if stripped.startswith('| '):
            table_buf.append(stripped)
            continue

        flush_table()

        if stripped.startswith('# ') and not stripped.startswith('## '):
            html_parts.append(f'<h1>{html_mod.escape(stripped[2:])}</h1>')
        elif stripped.startswith('### '):
            html_parts.append(f'<h3>{html_mod.escape(stripped[4:])}</h3>')
        elif stripped.startswith('## '):
            html_parts.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('> '):
            html_parts.append(f'<blockquote>{html_mod.escape(stripped[2:])}</blockquote>')
        elif stripped.startswith(SEPARATOR[:5]):
            html_parts.append(f'<p>{stripped}</p>')
        else:
            html_parts.append(f'<p>{html_mod.escape(stripped)}</p>')

    flush_list()
    flush_table()
    return '\n'.join(html_parts)


def push_to_coda(content_html: str):
    """Push HTML content to the Coda page, replacing existing content."""
    url = f'{API_BASE}/docs/{DOC_ID}/pages/{PAGE_ID}'
    payload = {
        'contentUpdate': {
            'insertionMode': 'replace',
            'canvasContent': {
                'format': 'html',
                'content': content_html,
            }
        }
    }
    resp = requests.put(url, headers=HEADERS, json=payload)
    if resp.status_code in (200, 202):
        print(f'SUCCESS: Content pushed to Coda page {PAGE_ID}')
        print(f'URL: https://coda.io/d/Solutions-Central_djfymaxsTtA/TSAs-KPI_suMS1NeD')
        return True
    else:
        print(f'ERROR {resp.status_code}: {resp.text}')
        return False


def main():
    print('Reading playbook...')
    with open(PLAYBOOK_PATH, 'r', encoding='utf-8') as f:
        raw = f.read()

    print('Applying Codex Box styling...')
    styled = style_playbook(raw)

    styled_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'KPI_PLAYBOOK_STYLED.md')
    with open(styled_path, 'w', encoding='utf-8') as f:
        f.write(styled)
    print(f'Styled version saved: {styled_path}')

    print('Converting to HTML for Coda...')
    html_content = md_to_html(styled)
    
    html_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'KPI_PLAYBOOK_CODA.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'HTML version saved: {html_path}')

    print(f'Pushing to Coda doc={DOC_ID} page={PAGE_ID}...')
    success = push_to_coda(html_content)

    if success:
        print('Done! Check the Coda page.')
    else:
        print('Push failed. Check the error above.')


if __name__ == '__main__':
    main()
