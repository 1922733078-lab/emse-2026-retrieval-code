#!/usr/bin/env bash
# check_release_secrets.sh — scan candidate release for potential secrets.
set -euo pipefail

CANDIDATE_ROOT="${1:-.}"

echo "=== Secrets Scan ==="
VIOLATIONS=0

# Patterns that indicate secrets
while IFS= read -r -d '' file; do
    # Skip binary files
    if file "$file" | grep -q "image\|PDF\|binary"; then
        continue
    fi
    if grep -lE "(api_key|api-key|bearer)\s*[:=]\s*['\"]?[^\s'\"]{16,}" "$file" 2>/dev/null; then
        echo "  FLAGGED: $file (possible API key)"
        VIOLATIONS=1
    fi
    if grep -lE "sk-[A-Za-z0-9]{20,}" "$file" 2>/dev/null; then
        echo "  FLAGGED: $file (possible secret key)"
        VIOLATIONS=1
    fi
done < <(find "$CANDIDATE_ROOT" -type f -print0)

if [ "$VIOLATIONS" -eq 0 ]; then
    echo "  PASS: no obvious secrets detected"
else
    echo "  WARNING: potential secrets found — review before release"
    exit 1
fi

# Check for .env files
if find "$CANDIDATE_ROOT" -name ".env" -type f 2>/dev/null | grep -q .; then
    echo "  WARNING: .env files found in candidate"
    exit 1
fi

echo "=== Scan complete ==="