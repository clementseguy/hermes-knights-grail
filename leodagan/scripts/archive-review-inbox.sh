#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
archive_dir=${LEODAGAN_REVIEW_ARCHIVE_DIR:-}

if [[ -z "$archive_dir" ]]; then
  echo 'Set LEODAGAN_REVIEW_ARCHIVE_DIR to a dedicated encrypted archive directory.' >&2
  exit 1
fi

if [[ ${1:-} != --apply ]]; then
  echo 'Dry-run: no review edition is moved. Re-run with --apply after choosing a retention date.'
  find "$root_dir/review-inbox" -mindepth 1 -maxdepth 1 -type d -print | sort
  exit 0
fi

echo 'Refusing to archive without an explicit, approved retention rule.' >&2
echo 'Document the retention date in docs/operations.md before implementing a move.' >&2
exit 1
