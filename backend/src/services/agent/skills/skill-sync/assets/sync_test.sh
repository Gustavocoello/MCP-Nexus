#!/bin/bash
# Unit tests for sync.sh
# Run: ./skills/skill-sync/assets/sync_test.sh
#
# shellcheck disable=SC2317
# Reason: Test functions are discovered and called dynamically via declare -F

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/sync.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test environment
TEST_DIR=""

# =============================================================================
# TEST FRAMEWORK
# =============================================================================

setup_test_env() {
    TEST_DIR=$(mktemp -d)

    # Create mock repo structure for agents
    mkdir -p "$TEST_DIR/skills/mock-jarvis-skill"
    mkdir -p "$TEST_DIR/skills/mock-koda-skill"
    mkdir -p "$TEST_DIR/skills/mock-lamar-skill"
    mkdir -p "$TEST_DIR/skills/mock-root-skill"
    mkdir -p "$TEST_DIR/skills/mock-no-metadata"
    mkdir -p "$TEST_DIR/skills/skill-sync/assets"
    mkdir -p "$TEST_DIR/jarvis"
    mkdir -p "$TEST_DIR/Koda"
    mkdir -p "$TEST_DIR/lamar"

    # Create mock SKILL.md files with metadata
    cat > "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md" << 'EOF'
---
name: mock-jarvis-skill
description: >
  Mock Jarvis skill for testing.
  Trigger: When testing Jarvis.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [jarvis]
  auto_invoke: "Testing Jarvis components"
allowed-tools: Read
---

# Mock Jarvis Skill
EOF

    cat > "$TEST_DIR/skills/mock-koda-skill/SKILL.md" << 'EOF'
---
name: mock-koda-skill
description: >
  Mock Koda skill for testing.
  Trigger: When testing Koda.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [koda]
  auto_invoke: "Testing Koda endpoints"
allowed-tools: Read
---

# Mock Koda Skill
EOF

    cat > "$TEST_DIR/skills/mock-lamar-skill/SKILL.md" << 'EOF'
---
name: mock-lamar-skill
description: >
  Mock Lamar skill for testing.
  Trigger: When testing Lamar.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [lamar]
  auto_invoke: "Testing Lamar checks"
allowed-tools: Read
---

# Mock Lamar Skill
EOF

    cat > "$TEST_DIR/skills/mock-root-skill/SKILL.md" << 'EOF'
---
name: mock-root-skill
description: >
  Mock root skill for testing.
  Trigger: When testing root.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [root]
  auto_invoke: "Testing root actions"
allowed-tools: Read
---

# Mock Root Skill
EOF

    cat > "$TEST_DIR/skills/mock-no-metadata/SKILL.md" << 'EOF'
---
name: mock-no-metadata
description: >
  Skill without sync metadata.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
allowed-tools: Read
---

# No Metadata Skill
EOF

    # Create mock AGENT.md files with Skills Reference section
    cat > "$TEST_DIR/AGENTS.md" << 'EOF'
# Root AGENTS

> **Skills Reference**: For detailed patterns, use these skills:
> - [`mock-root-skill`](skills/mock-root-skill/SKILL.md)

## Project Overview

This is the root agents file.
EOF

    cat > "$TEST_DIR/jarvis/AGENT.md" << 'EOF'
# JARVIS AGENT

> **Skills Reference**: For detailed patterns, use these skills:
> - [`mock-jarvis-skill`](../skills/mock-jarvis-skill/SKILL.md)

## CRITICAL RULES
EOF

    cat > "$TEST_DIR/Koda/AGENT.md" << 'EOF'
# KODA AGENT

> **Skills Reference**: For detailed patterns, use these skills:
> - [`mock-koda-skill`](../skills/mock-koda-skill/SKILL.md)

## CRITICAL RULES
EOF

    cat > "$TEST_DIR/lamar/AGENT.md" << 'EOF'
# LAMAR AGENT

> **Skills Reference**: For detailed patterns, use these skills:
> - [`mock-lamar-skill`](../skills/mock-lamar-skill/SKILL.md)

## CRITICAL RULES
EOF

    cp "$SYNC_SCRIPT" "$TEST_DIR/skills/skill-sync/assets/sync.sh"
    chmod +x "$TEST_DIR/skills/skill-sync/assets/sync.sh"
}

teardown_test_env() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

run_sync() {
    (cd "$TEST_DIR/skills/skill-sync/assets" && bash sync.sh "$@" 2>&1)
}

# Assertions
assert_equals() {
    local expected="$1" actual="$2" message="$3"
    if [ "$expected" = "$actual" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    Expected: $expected"
    echo "    Actual:   $actual"
    return 1
}

assert_contains() {
    local haystack="$1" needle="$2" message="$3"
    if echo "$haystack" | grep -q -F -- "$needle"; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    String not found: $needle"
    return 1
}

assert_not_contains() {
    local haystack="$1" needle="$2" message="$3"
    if ! echo "$haystack" | grep -q -F -- "$needle"; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    String should not be found: $needle"
    return 1
}

assert_file_contains() {
    local file="$1" needle="$2" message="$3"
    if grep -q -F -- "$needle" "$file" 2>/dev/null; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    File: $file"
    echo "    String not found: $needle"
    return 1
}

assert_file_not_contains() {
    local file="$1" needle="$2" message="$3"
    if ! grep -q -F -- "$needle" "$file" 2>/dev/null; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    File: $file"
    echo "    String should not be found: $needle"
    return 1
}

# =============================================================================
# TESTS: FLAG PARSING
# =============================================================================

test_flag_help_shows_usage() {
    local output
    output=$(run_sync --help)
    assert_contains "$output" "Usage:" "Help should show usage" && \
    assert_contains "$output" "--dry-run" "Help should mention --dry-run" && \
    assert_contains "$output" "--scope" "Help should mention --scope"
}

test_flag_unknown_reports_error() {
    local output
    output=$(run_sync --unknown 2>&1) || true
    assert_contains "$output" "Unknown option" "Should report unknown option"
}

test_flag_dryrun_shows_changes() {
    local output
    output=$(run_sync --dry-run)
    assert_contains "$output" "[DRY RUN]" "Should show dry run marker" && \
    assert_contains "$output" "Would update" "Should say would update"
}

test_flag_dryrun_no_file_changes() {
    run_sync --dry-run > /dev/null
    assert_file_not_contains "$TEST_DIR/jarvis/AGENT.md" "### Auto-invoke Skills" \
        "AGENT.md should not be modified in dry run"
}

test_flag_scope_filters_correctly() {
    local output
    output=$(run_sync --scope jarvis)
    assert_contains "$output" "Processing: jarvis" "Should process jarvis scope" && \
    assert_not_contains "$output" "Processing: koda" "Should not process koda scope"
}

# =============================================================================
# TESTS: METADATA EXTRACTION
# =============================================================================

test_metadata_extracts_scope() {
    local output
    output=$(run_sync --dry-run)
    assert_contains "$output" "Processing: jarvis" "Should detect jarvis scope" && \
    assert_contains "$output" "Processing: koda" "Should detect koda scope" && \
    assert_contains "$output" "Processing: lamar" "Should detect lamar scope" && \
    assert_contains "$output" "Processing: root" "Should detect root scope"
}

test_metadata_extracts_auto_invoke() {
    local output
    output=$(run_sync --dry-run)
    assert_contains "$output" "Testing Jarvis components" "Should extract Jarvis auto_invoke" && \
    assert_contains "$output" "Testing Koda endpoints" "Should extract Koda auto_invoke" && \
    assert_contains "$output" "Testing Lamar checks" "Should extract Lamar auto_invoke"
}

test_metadata_missing_reports_skills() {
    local output
    output=$(run_sync --dry-run)
    assert_contains "$output" "Skills missing sync metadata" "Should report missing metadata section" && \
    assert_contains "$output" "mock-no-metadata" "Should list skill without metadata"
}

test_metadata_skips_without_scope_in_processing() {
    local output
    output=$(run_sync --dry-run)
    local processing_lines
    processing_lines=$(echo "$output" | grep "Processing:")
    assert_not_contains "$processing_lines" "mock-no-metadata" "Should not process skill without scope"
}

test_generate_creates_table() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "### Auto-invoke Skills" \
        "Should create Auto-invoke section" && \
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "| Action | Skill |" \
        "Should create table header"
}

test_generate_correct_skill_in_jarvis() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "mock-jarvis-skill" \
        "Jarvis AGENT should contain mock-jarvis-skill" && \
    assert_file_not_contains "$TEST_DIR/jarvis/AGENT.md" "mock-koda-skill" \
        "Jarvis AGENT should not contain mock-koda-skill"
}

test_generate_correct_skill_in_koda() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/Koda/AGENT.md" "mock-koda-skill" \
        "Koda AGENT should contain mock-koda-skill" && \
    assert_file_not_contains "$TEST_DIR/Koda/AGENT.md" "mock-jarvis-skill" \
        "Koda AGENT should not contain mock-jarvis-skill"
}

test_generate_correct_skill_in_lamar() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/lamar/AGENT.md" "mock-lamar-skill" \
        "Lamar AGENT should contain mock-lamar-skill" && \
    assert_file_not_contains "$TEST_DIR/lamar/AGENT.md" "mock-jarvis-skill" \
        "Lamar AGENT should not contain mock-jarvis-skill"
}

test_generate_correct_skill_in_root() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/AGENTS.md" "mock-root-skill" \
        "Root AGENTS should contain mock-root-skill" && \
    assert_file_not_contains "$TEST_DIR/AGENTS.md" "mock-jarvis-skill" \
        "Root AGENTS should not contain mock-jarvis-skill"
}

test_generate_includes_action_text() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "Testing Jarvis components" \
        "Should include auto_invoke action text"
}

test_generate_splits_multi_action_auto_invoke_list() {
    # Change UI skill to use list auto_invoke (two actions)
    cat > "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md" << 'EOF'
---
name: mock-jarvis-skill
description: Mock Jarvis skill with multi-action auto_invoke list.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [jarvis]
  auto_invoke:
    - "Action B"
    - "Action A"
allowed-tools: Read
---
EOF

    run_sync > /dev/null

    # Both actions should produce rows
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "| Action A | \`mock-jarvis-skill\` |" \
        "Should create row for Action A" && \
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "| Action B | \`mock-jarvis-skill\` |" \
        "Should create row for Action B"
}

test_generate_orders_rows_by_action_then_skill() {
    # Two skills, intentionally out-of-order actions, same scope
    cat > "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md" << 'EOF'
---
name: mock-jarvis-skill
description: Mock Jarvis skill.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [jarvis]
  auto_invoke:
    - "Z action"
    - "A action"
allowed-tools: Read
---
EOF

    mkdir -p "$TEST_DIR/skills/mock-jarvis-skill-2"
    cat > "$TEST_DIR/skills/mock-jarvis-skill-2/SKILL.md" << 'EOF'
---
name: mock-jarvis-skill-2
description: Second Jarvis skill.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [jarvis]
  auto_invoke: "A action"
allowed-tools: Read
---
EOF

    run_sync > /dev/null

    # Verify order within the table is: "A action" rows first, then "Z action"
    local table_segment
    table_segment=$(awk '
        /^\| Action \| Skill \|/ { in_table=1 }
        in_table && /^---$/ { next }
        in_table && /^\|/ { print }
        in_table && !/^\|/ { exit }
    ' "$TEST_DIR/jarvis/AGENT.md")

    local first_a_index first_z_index
    first_a_index=$(echo "$table_segment" | awk '/\| A action \|/ { print NR; exit }')
    first_z_index=$(echo "$table_segment" | awk '/\| Z action \|/ { print NR; exit }')

    # Both must exist and A must come before Z
    [ -n "$first_a_index" ] && [ -n "$first_z_index" ] && [ "$first_a_index" -lt "$first_z_index" ]
}

# =============================================================================
# TESTS: AGENTS.MD UPDATE
# =============================================================================

test_update_preserves_header() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "# JARVIS AGENT" \
        "Should preserve original header"
}

test_update_preserves_skills_reference() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "Skills Reference" \
        "Should preserve Skills Reference section"
}

test_update_preserves_content_after() {
    run_sync > /dev/null
    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "## CRITICAL RULES" \
        "Should preserve content after Auto-invoke section"
}

test_update_replaces_existing_section() {
    # First run creates section
    run_sync > /dev/null

    # Portable way to update file using sed (avoids macOS BSD vs Linux GNU sed -i conflicts)
    sed 's/Testing Jarvis components/Modified Jarvis action/' "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md" > "$TEST_DIR/skills/mock-jarvis-skill/SKILL.tmp"
    mv "$TEST_DIR/skills/mock-jarvis-skill/SKILL.tmp" "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md"

    # Second run should replace
    run_sync > /dev/null

    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "Modified Jarvis action" \
        "Should update with new auto_invoke text" && \
    assert_file_not_contains "$TEST_DIR/jarvis/AGENT.md" "Testing Jarvis components" \
        "Should remove old auto_invoke text"
}

# =============================================================================
# TESTS: IDEMPOTENCY
# =============================================================================

test_idempotent_multiple_runs() {
    run_sync > /dev/null
    local first_content
    first_content=$(cat "$TEST_DIR/jarvis/AGENT.md")

    run_sync > /dev/null
    local second_content
    second_content=$(cat "$TEST_DIR/jarvis/AGENT.md")

    assert_equals "$first_content" "$second_content" \
        "Multiple runs should produce identical output"
}

test_idempotent_no_duplicate_sections() {
    run_sync > /dev/null
    run_sync > /dev/null
    run_sync > /dev/null

    local count
    count=$(grep -c "### Auto-invoke Skills" "$TEST_DIR/jarvis/AGENT.md")
    assert_equals "1" "$count" "Should have exactly one Auto-invoke section"
}

# =============================================================================
# TESTS: MULTI-SCOPE SKILLS
# =============================================================================

test_multiscope_skill_appears_in_multiple() {
    # Create a skill with multiple scopes
    cat > "$TEST_DIR/skills/mock-jarvis-skill/SKILL.md" << 'EOF'
---
name: mock-jarvis-skill
description: Mock skill with multiple scopes.
license: Apache-2.0
metadata:
  author: test
  version: "1.0"
  scope: [jarvis, koda]
  auto_invoke: "Multi-scope action"
allowed-tools: Read
---
EOF

    run_sync > /dev/null

    assert_file_contains "$TEST_DIR/jarvis/AGENT.md" "mock-jarvis-skill" \
        "Multi-scope skill should appear in Jarvis" && \
    assert_file_contains "$TEST_DIR/Koda/AGENT.md" "mock-jarvis-skill" \
        "Multi-scope skill should appear in Koda"
}

# =============================================================================
# TEST RUNNER
# =============================================================================

run_all_tests() {
    local test_functions current_section=""

    test_functions=$(declare -F | awk '{print $3}' | grep '^test_' | sort)

    for test_func in $test_functions; do
        local section
        section=$(echo "$test_func" | sed 's/^test_//' | cut -d'_' -f1)
        section="$(echo "${section:0:1}" | tr '[:lower:]' '[:upper:]')${section:1}"

        if [ "$section" != "$current_section" ]; then
            [ -n "$current_section" ] && echo ""
            echo -e "${YELLOW}${section} tests:${NC}"
            current_section="$section"
        fi

        local test_name
        test_name=$(echo "$test_func" | sed 's/^test_//' | tr '_' ' ')

        TESTS_RUN=$((TESTS_RUN + 1))
        echo -n "  $test_name... "

        setup_test_env

        if $test_func; then
            echo -e "${GREEN}PASS${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi

        teardown_test_env
    done
}

# =============================================================================
# MAIN
# =============================================================================

echo ""
echo "🧪 Running sync.sh unit tests"
echo "=============================="
echo ""

run_all_tests

echo ""
echo "=============================="
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All $TESTS_RUN tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED of $TESTS_RUN tests failed${NC}"
    exit 1
fi