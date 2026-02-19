#!/bin/bash
# =============================================================================
# Planet Detroit — Build & Test Smoke Tests
#
# Runs all automated tests across the project:
# 1. API endpoint tests (pytest)
# 2. Scraper parsing tests (pytest)
# 3. Frontend build checks (npm run build)
#
# Usage: bash tests/test_all_builds.sh
# Exit code: 0 if all pass, 1 if any fail
# =============================================================================

set -e
PASS=0
FAIL=0
PROJECTS_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo "Planet Detroit — Smoke Test Suite"
echo "========================================"
echo ""

# --- API Tests ---
echo "--- API Tests (pytest) ---"
if (cd "$PROJECTS_DIR/api" && "$PROJECTS_DIR/venv/bin/python" -m pytest tests/ -q 2>&1); then
    echo "✓ API tests passed"
    PASS=$((PASS + 1))
else
    echo "✗ API tests FAILED"
    FAIL=$((FAIL + 1))
fi
echo ""

# --- Scraper Tests ---
echo "--- Scraper Tests (pytest) ---"
if (cd "$PROJECTS_DIR/scrapers" && "$PROJECTS_DIR/venv/bin/python" -m pytest tests/ -q 2>&1); then
    echo "✓ Scraper tests passed"
    PASS=$((PASS + 1))
else
    echo "✗ Scraper tests FAILED"
    FAIL=$((FAIL + 1))
fi
echo ""

# --- Frontend Builds ---
for PROJECT in civic-action-builder newsletter-builder news-brief-generator; do
    PROJECT_DIR="$PROJECTS_DIR/../$PROJECT"
    if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/package.json" ]; then
        echo "--- $PROJECT build ---"
        if (cd "$PROJECT_DIR" && npm run build 2>&1 | tail -5); then
            echo "✓ $PROJECT build passed"
            PASS=$((PASS + 1))
        else
            echo "✗ $PROJECT build FAILED"
            FAIL=$((FAIL + 1))
        fi
        echo ""
    fi
done

# --- Summary ---
echo "========================================"
echo "RESULTS: $PASS passed, $FAIL failed"
echo "========================================"

if [ $FAIL -gt 0 ]; then
    exit 1
fi
