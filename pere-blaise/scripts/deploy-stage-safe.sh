#!/usr/bin/env bash
# Copy only Père Blaise's versioned source through an explicit, reviewed stage.
# It never deletes, follows links, creates services, or starts Docker.
set -euo pipefail

readonly SLUG="pere-blaise"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SOURCE_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
readonly EXPECTED_SOURCE="$(cd -- "$HOME/workspace/my-hermes/$SLUG" && pwd -P)"
EXPECTED_DEPLOY_ROOT="$HOME/Library/Application Support/HermesAgents/deployments"

die() { printf 'deploy-stage-safe: %s\n' "$*" >&2; exit 2; }
usage() {
  cat >&2 <<'EOF'
Usage:
  deploy-stage-safe.sh --deploy-root PATH --budget-kib N --preview
  deploy-stage-safe.sh --deploy-root PATH --budget-kib N --stage --confirmed-total-bytes N
  deploy-stage-safe.sh --deploy-root PATH --activate-stage STAGING_PATH
  deploy-stage-safe.sh --deploy-root PATH --replace-stage STAGING_PATH \
    --archive-current ARCHIVE_PATH --confirm-services-stopped

PATH must be exactly ~/Library/Application Support/HermesAgents/deployments.
The three explicit phases are preview, stage-and-test, then activation. The
activation phase only renames a previously validated staging directory. A
replacement archives the current destination by rename; it never deletes data.
EOF
  exit 2
}

DEPLOY_ROOT=""
BUDGET_KIB=""
ACTION=""
CONFIRMED_TOTAL_BYTES=""
ACTIVATE_STAGE=""
ARCHIVE_CURRENT=""
SERVICES_STOPPED=0
while (($#)); do
  case "$1" in
    --deploy-root) DEPLOY_ROOT="${2:-}"; shift 2 ;;
    --budget-kib) BUDGET_KIB="${2:-}"; shift 2 ;;
    --preview) [[ -z "$ACTION" ]] || usage; ACTION="preview"; shift ;;
    --stage) [[ -z "$ACTION" ]] || usage; ACTION="stage"; shift ;;
    --confirmed-total-bytes) CONFIRMED_TOTAL_BYTES="${2:-}"; shift 2 ;;
    --activate-stage) [[ -z "$ACTION" ]] || usage; ACTION="activate"; ACTIVATE_STAGE="${2:-}"; shift 2 ;;
    --replace-stage) [[ -z "$ACTION" ]] || usage; ACTION="replace"; ACTIVATE_STAGE="${2:-}"; shift 2 ;;
    --archive-current) ARCHIVE_CURRENT="${2:-}"; shift 2 ;;
    --confirm-services-stopped) SERVICES_STOPPED=1; shift ;;
    *) usage ;;
  esac
done

[[ "$SOURCE_DIR" == "$EXPECTED_SOURCE" ]] || die "source is not the canonical $EXPECTED_SOURCE"
[[ -f "$SOURCE_DIR/pyproject.toml" && -f "$SOURCE_DIR/README.md" && -d "$SOURCE_DIR/src" ]] || die "source is incomplete"
if find "$SOURCE_DIR" -type l -print -quit | grep -q .; then
  die "source contains a symbolic link; deployment refuses it"
fi
[[ -n "$DEPLOY_ROOT" && -n "$ACTION" ]] || usage

DEPLOY_ROOT="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=False))' "$DEPLOY_ROOT")"
EXPECTED_DEPLOY_ROOT="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=False))' "$EXPECTED_DEPLOY_ROOT")"
case "$DEPLOY_ROOT" in
  /|"$HOME"|/Users|/System|/Library|/Applications|/Volumes|/private) die "deployment root is too broad" ;;
esac
[[ "$DEPLOY_ROOT" == "$EXPECTED_DEPLOY_ROOT" ]] || die "deployment root is not the approved $EXPECTED_DEPLOY_ROOT"
[[ -d "$DEPLOY_ROOT" ]] || die "approved deployment root does not exist"
[[ ! -L "$DEPLOY_ROOT" ]] || die "deployment root must not be a symlink"

readonly DESTINATION="$DEPLOY_ROOT/$SLUG"
readonly STAGING_PARENT="$DEPLOY_ROOT/.staging"

if [[ "$ACTION" == "activate" || "$ACTION" == "replace" ]]; then
  [[ -n "$ACTIVATE_STAGE" ]] || usage
  ACTIVATE_STAGE="$(python3 -c '
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve(strict=True)
stage = Path(sys.argv[2]).resolve(strict=True)
if stage.parent != root / ".staging":
    raise SystemExit("staging path is outside the approved staging directory")
print(stage)
' "$DEPLOY_ROOT" "$ACTIVATE_STAGE")" || die "invalid staging path"
  [[ -d "$ACTIVATE_STAGE" && ! -L "$ACTIVATE_STAGE" ]] || die "staging directory is invalid"
  [[ -f "$ACTIVATE_STAGE/.deployment-validated" ]] || die "staging directory was not validated"
  [[ -f "$ACTIVATE_STAGE/pyproject.toml" && -f "$ACTIVATE_STAGE/README.md" && -d "$ACTIVATE_STAGE/src/pere_blaise" ]] || die "staging validation failed"
  if find "$ACTIVATE_STAGE" -type l -print -quit | grep -q .; then
    die "staging directory contains a symbolic link"
  fi
  if [[ "$ACTION" == "activate" ]]; then
    [[ ! -e "$DESTINATION" ]] || die "destination already exists; use the explicit replacement flow"
  else
    [[ -e "$DESTINATION" && ! -L "$DESTINATION" ]] || die "current destination is missing or a symbolic link"
    [[ "$SERVICES_STOPPED" == 1 && -n "$ARCHIVE_CURRENT" ]] || usage
    ARCHIVE_CURRENT="$(python3 -c '
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve(strict=True)
archive = Path(sys.argv[2]).resolve(strict=False)
if archive.parent != root / ".archive" or not archive.name.startswith("pere-blaise-"):
    raise SystemExit("archive path is outside the approved archive directory")
print(archive)
' "$DEPLOY_ROOT" "$ARCHIVE_CURRENT")" || die "invalid archive path"
    [[ ! -e "$ARCHIVE_CURRENT" ]] || die "archive destination already exists"
    mkdir -p -- "${ARCHIVE_CURRENT%/*}"
    [[ ! -L "${ARCHIVE_CURRENT%/*}" ]] || die "archive parent must not be a symbolic link"
    printf 'Current deployment to archive: %s (%s KiB)\n' "$DESTINATION" "$(du -sk "$DESTINATION" | awk '{print $1}')"
    printf 'Archive destination: %s\n' "$ARCHIVE_CURRENT"
    mv -- "$DESTINATION" "$ARCHIVE_CURRENT"
  fi
  printf 'Staging: %s\nDestination: %s\n' "$ACTIVATE_STAGE" "$DESTINATION"
  mv -- "$ACTIVATE_STAGE" "$DESTINATION"
  printf 'Activated deployment at %s\n' "$DESTINATION"
  printf 'No service, container, volume, secret or LaunchAgent was created or started.\n'
  exit 0
fi

[[ -n "$BUDGET_KIB" && "$BUDGET_KIB" =~ ^[1-9][0-9]*$ ]] || usage
readonly PREVIEW_TARGET="$DEPLOY_ROOT/$SLUG"
preview="$(rsync -a --links --dry-run --stats --itemize-changes \
  --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  "$SOURCE_DIR/" "$PREVIEW_TARGET/" )"
printf 'Source: %s\nDeployment root: %s\nCandidate destination: %s\n' \
  "$SOURCE_DIR" "$DEPLOY_ROOT" "$PREVIEW_TARGET"
printf '%s\n' "$preview"
total_bytes="$(printf '%s\n' "$preview" | awk -F: '/^Total file size:/ {gsub(/[^0-9]/,"",$2); print $2}')"
[[ -n "$total_bytes" ]] || die "rsync did not report a total file size"
(( total_bytes <= BUDGET_KIB * 1024 )) || die "preview exceeds the approved budget (${BUDGET_KIB} KiB)"
printf 'Reviewed total: %s bytes (budget: %s KiB)\n' "$total_bytes" "$BUDGET_KIB"

if [[ "$ACTION" == "preview" ]]; then
  printf 'Nothing was copied. Re-run with --stage --confirmed-total-bytes %s only after human review.\n' "$total_bytes"
  exit 0
fi

[[ "$CONFIRMED_TOTAL_BYTES" =~ ^[1-9][0-9]*$ ]] || usage
[[ "$CONFIRMED_TOTAL_BYTES" == "$total_bytes" ]] || die "confirmed total does not match the current preview"
mkdir -p -- "$STAGING_PARENT"
[[ ! -L "$STAGING_PARENT" ]] || die "staging parent must not be a symlink"
readonly STAGING="$STAGING_PARENT/$SLUG-$(date -u +%Y%m%dT%H%M%SZ)"
[[ ! -e "$STAGING" ]] || die "staging destination already exists"

rsync -a --links --stats --itemize-changes \
  --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  "$SOURCE_DIR/" "$STAGING/"
[[ -f "$STAGING/pyproject.toml" && -f "$STAGING/README.md" && -d "$STAGING/src/pere_blaise" ]] || die "staging validation failed"
if find "$STAGING" -type l -print -quit | grep -q .; then
  die "staging directory contains a symbolic link"
fi
PYTHONPATH="$STAGING/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m unittest discover -s "$STAGING/tests" -v
printf 'validated\n' > "$STAGING/.deployment-validated"
chmod 600 "$STAGING/.deployment-validated"
printf 'Staged and validated at %s\n' "$STAGING"
printf 'Review it, then activate only this path with:\n'
printf '  %s --deploy-root %q --activate-stage %q\n' "$0" "$DEPLOY_ROOT" "$STAGING"
