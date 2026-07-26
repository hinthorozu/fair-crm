#!/usr/bin/env bash
#
# Unit checks for Node.js version comparison helpers used by server deploy.
# Does not install packages or touch production servers.
#
# Usage:
#   bash scripts/server/test-node-version.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

assert_meets() {
  local current="$1"
  local required="$2"
  if ! node_version_meets_minimum "$current" "$required"; then
    echo "FAIL: expected ${current} >= ${required}" >&2
    exit 1
  fi
  echo "OK: ${current} >= ${required}"
}

assert_below() {
  local current="$1"
  local required="$2"
  if node_version_meets_minimum "$current" "$required"; then
    echo "FAIL: expected ${current} < ${required}" >&2
    exit 1
  fi
  echo "OK: ${current} < ${required} (upgrade required)"
}

main() {
  local min="${REQUIRED_NODEJS_VERSION}"
  echo "REQUIRED_NODEJS_VERSION=${min}"

  assert_below "18.19.1" "$min"
  assert_below "v18.19.1" "$min"
  assert_below "20.19.0" "$min"
  assert_below "20.18.0" "$min"
  assert_below "22.11.0" "$min"
  assert_below "v22.11.9" "$min"

  assert_meets "22.12.0" "$min"
  assert_meets "v22.12.0" "$min"
  assert_meets "22.12.1" "$min"
  assert_meets "22.13.0" "$min"
  assert_meets "24.0.0" "$min"
  assert_meets "v24.1.0" "$min"

  # normalize strips pre-release suffix consistently
  local normalized
  normalized="$(normalize_node_version "v22.12.0-rc.1")"
  [[ "$normalized" == "22.12.0" ]] || {
    echo "FAIL: normalize_node_version got ${normalized}" >&2
    exit 1
  }
  echo "OK: normalize_node_version v22.12.0-rc.1 -> ${normalized}"

  echo ""
  echo "All Node.js version comparison checks passed."
}

main "$@"
