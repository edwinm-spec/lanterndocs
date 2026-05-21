#!/bin/bash
# Verification script for LanternDocs debugging task

set -e

echo "=== Running LanternDocs build ==="
cd /repo
python3 -m lanterndocs build --content src/content --theme src/theme --out output/site

echo "=== Checking output files ==="
if [ ! -f "output/site/index.html" ]; then
    echo "FAIL: index.html not found"
    exit 1
fi

if [ ! -f "output/site/search_index.json" ]; then
    echo "FAIL: search_index.json not found"
    exit 1
fi

echo "=== Checking draft pages are excluded ==="
if grep -q "Incident Playbook" output/site/index.html; then
    echo "FAIL: Draft page 'Incident Playbook' appears in navigation"
    exit 1
fi

if [ -f "output/site/incident-playbook.html" ]; then
    echo "FAIL: Draft page was rendered as HTML"
    exit 1
fi

echo "=== Checking draft links have correct class ==="
if ! grep -q 'class="draft-link"' output/site/troubleshooting.html; then
    echo "FAIL: Draft link missing 'draft-link' class"
    exit 1
fi

echo "=== Checking wiki-style links ==="
if grep -q '\[\[Incident Playbook\]\]' output/site/troubleshooting.html; then
    echo "FAIL: Wiki-style link [[Incident Playbook]] not converted to HTML"
    exit 1
fi

echo "=== Checking search index schema ==="
python3 -c "import json; json.load(open('output/site/search_index.json')); print('✓ JSON valid')"

echo "=== Checking search index has required fields ==="
python3 << 'PYEOF'
import json
with open('output/site/search_index.json') as f:
    data = json.load(f)
assert "generated_at" in data, "Missing generated_at"
assert "pages" in data, "Missing pages"
for page in data["pages"]:
    assert "slug" in page, "Missing slug"
    assert "title" in page, "Missing title"
    assert "summary" in page, "Missing summary"
    assert "headings" in page, "Missing headings"
    assert "source_path" in page, "Missing source_path"
print("✓ Search index schema valid")
PYEOF

echo "=== Checking internal links resolve ==="
if ! grep -q 'href="ops/alerting.html"' output/site/getting-started.html; then
    echo "FAIL: Link from getting-started to ops/alerting not found"
    exit 1
fi

echo "=== Checking navigation uses relative paths ==="
if grep -q 'href="/' output/site/runbooks/db/backup.html; then
    echo "FAIL: Navigation uses absolute paths (starts with /)"
    exit 1
fi

echo "PASS: All verifications passed"
exit 0
