#!/usr/bin/env bash
set -euo pipefail

slug=leodagan
source_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
repo_dir=$(cd "$source_dir/.." && pwd -P)
deploy_root="$repo_dir/.deployments/$slug"
private_dir="${LEODAGAN_PRIVATE_DIR:-$HOME/Library/Application Support/HermesLeodagan}"
env_file="$private_dir/channels.env"
bot_token_file="$private_dir/slack-leodagan-bot.token"
app_token_file="$private_dir/slack-leodagan-app.token"
telegram_token_file="$private_dir/telegram-leodagan-bot.token"
export LEODAGAN_OUTBOX="$source_dir/outbox"
image='nousresearch/hermes-agent@sha256:9774f4f39a9bb8c2f68ce728ed5e99ddbad282163be56764afacf88ed952b784'
export HERMES_IMAGE="${HERMES_IMAGE:-$image}"

fail() { printf 'ERREUR: %s\n' "$*" >&2; exit 1; }
check_paths() {
  [[ "$source_dir" == "$repo_dir/$slug" ]] || fail "source hors du slug"
  [[ "$repo_dir" == "$HOME/workspace/hermes-knights-grail" ]] || fail "dépôt inattendu"
  [[ -f "$source_dir/README.md" && -f "$source_dir/compose.yaml" && -f "$source_dir/config/config.yaml" ]] || fail "source incomplète"
  [[ "$deploy_root" == "$repo_dir/.deployments/$slug" ]] || fail "destination hors périmètre"
  [[ ! -L "$repo_dir/.deployments" && ! -L "$deploy_root" && ! -L "$deploy_root/releases" ]] || fail "lien symbolique dans la destination"
  if [[ -d "$repo_dir/.deployments" ]]; then
    [[ "$(cd "$repo_dir/.deployments" && pwd -P)" == "$repo_dir/.deployments" ]] || fail "destination physique hors périmètre"
  fi
  if [[ -d "$deploy_root" ]]; then
    [[ "$(cd "$deploy_root" && pwd -P)" == "$deploy_root" ]] || fail "destination physique hors périmètre"
  fi
  [[ "$private_dir" == "$HOME/Library/Application Support/HermesLeodagan" ]] || fail "répertoire privé inattendu"
  [[ ! -L "$private_dir" && ! -L "$LEODAGAN_OUTBOX" ]] || fail "lien symbolique dans les données privées ou livrables"
  if [[ -d "$private_dir" ]]; then
    [[ "$(cd "$private_dir" && pwd -P)" == "$private_dir" ]] || fail "répertoire privé physique inattendu"
  fi
  if [[ -d "$LEODAGAN_OUTBOX" ]]; then
    [[ "$(cd "$LEODAGAN_OUTBOX" && pwd -P)" == "$LEODAGAN_OUTBOX" ]] || fail "livrables physiques hors périmètre"
  fi
  printf 'Source physique : %s\nDestination physique autorisée : %s\n' "$source_dir" "$deploy_root"
}
compose() {
  [[ -L "$deploy_root/current" ]] || fail "installation absente"
  local release
  release=$(cd "$deploy_root/current" && pwd -P)
  [[ "$release" == "$deploy_root"/releases/*/leodagan ]] || fail "release hors périmètre"
  load_channel_tokens
  if [[ -f "$env_file" ]]; then
    docker compose --env-file "$env_file" -f "$release/compose.yaml" "$@"
  else
    docker compose -f "$release/compose.yaml" "$@"
  fi
}
load_channel_tokens() {
  if [[ -f "$bot_token_file" && -f "$app_token_file" ]]; then
    export SLACK_BOT_TOKEN="$(tr -d '\r\n' < "$bot_token_file")"
    export SLACK_APP_TOKEN="$(tr -d '\r\n' < "$app_token_file")"
  fi
  if [[ -s "$telegram_token_file" ]]; then
    export TELEGRAM_BOT_TOKEN="$(tr -d '\r\n' < "$telegram_token_file")"
  fi
}
source_fingerprint() {
  python3 - "$1" <<'PY'
import hashlib, os, stat, sys
root = os.path.realpath(sys.argv[1])
digest = hashlib.sha256()
excluded_roots = {'runtime', 'review-inbox', 'outbox', '.private'}
for base, dirs, files in os.walk(root, followlinks=False):
    relative_base = os.path.relpath(base, root)
    dirs[:] = sorted(name for name in dirs if name != '__pycache__' and
                     not (relative_base == '.' and name in excluded_roots))
    entries = sorted(files + [name for name in dirs if os.path.islink(os.path.join(base, name))])
    dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(base, name))]
    for name in entries:
        if name.endswith('.pyc'):
            continue
        path = os.path.join(base, name)
        relative = os.path.relpath(path, root).encode()
        digest.update(relative + b'\0')
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode):
            digest.update(b'L' + os.readlink(path).encode() + b'\0')
        elif stat.S_ISREG(mode):
            digest.update(b'F')
            with open(path, 'rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
        else:
            raise SystemExit('source non régulière refusée : ' + os.fsdecode(relative))
print(digest.hexdigest())
PY
}
provision_config() {
  local mode="${1:-initial}" release
  [[ -L "$deploy_root/current" ]] || fail "release absente"
  release=$(cd "$deploy_root/current" && pwd -P)
  [[ "$release" == "$deploy_root"/releases/*/leodagan ]] || fail "release hors périmètre"
  [[ -z "$(docker ps -q --filter name='^/hermes-leodagan$')" ]] || fail "config non modifiable pendant l'exécution"
  docker volume create hermes-leodagan-data >/dev/null
  if [[ "$mode" == replace ]]; then
    docker run --rm --network none --entrypoint sh -v "$release/config/config.yaml:/source/config.yaml:ro" -v "$release/skills/leodagan/SKILL.md:/source/SKILL.md:ro" -v hermes-leodagan-data:/data "$HERMES_IMAGE" -c 'cp /source/config.yaml /data/config.yaml.next && cp /source/SKILL.md /data/SOUL.md.next && chown 1000:1000 /data/config.yaml.next /data/SOUL.md.next && chmod 600 /data/config.yaml.next /data/SOUL.md.next && mv -f /data/config.yaml.next /data/config.yaml && mv -f /data/SOUL.md.next /data/SOUL.md'
  else
    docker run --rm --network none --entrypoint sh -v "$release/config/config.yaml:/source/config.yaml:ro" -v "$release/skills/leodagan/SKILL.md:/source/SKILL.md:ro" -v hermes-leodagan-data:/data "$HERMES_IMAGE" -c 'if test ! -s /data/config.yaml; then cp /source/config.yaml /data/config.yaml && chown 1000:1000 /data/config.yaml && chmod 600 /data/config.yaml; fi; if test ! -s /data/SOUL.md; then cp /source/SKILL.md /data/SOUL.md && chown 1000:1000 /data/SOUL.md && chmod 600 /data/SOUL.md; fi'
  fi
}
install() {
  check_paths
  command -v rsync >/dev/null || fail "rsync manquant"
  if [[ -L "$deploy_root/current" ]]; then
    local current_release
    current_release=$(cd "$deploy_root/current" && pwd -P)
    [[ "$current_release" == "$deploy_root"/releases/*/leodagan ]] || fail "release courante hors périmètre"
    if [[ "$(source_fingerprint "$source_dir")" == "$(source_fingerprint "$current_release")" ]]; then
      printf 'Release déjà identique : %s\n' "$current_release"
      return 0
    fi
  fi
  [[ -z "$(docker ps -q --filter name='^/hermes-leodagan$')" ]] || fail "arrêter Léodagan avant une nouvelle installation"
  local stamp stage size preview
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  stage="$deploy_root/releases/$stamp/leodagan"
  [[ ! -e "$stage" ]] || fail "release déjà présente"
  mkdir -p "$stage" "$LEODAGAN_OUTBOX" "$private_dir"
  [[ "$(cd "$deploy_root/releases" && pwd -P)" == "$deploy_root/releases" ]] || fail "staging physique hors périmètre"
  [[ "$(cd "$stage" && pwd -P)" == "$stage" ]] || fail "staging physique hors périmètre"
  chmod 700 "$private_dir" "$LEODAGAN_OUTBOX"
  printf 'Aperçu de la copie versionnée :\n'
  preview=$(rsync -a --dry-run --stats --exclude=/runtime --exclude=/review-inbox --exclude=/outbox --exclude=/.private --exclude='__pycache__' --exclude='*.pyc' "$source_dir/" "$stage/")
  printf '%s\n' "$preview"
  size=$(printf '%s\n' "$preview" | awk -F: '/Total file size:/{gsub(/[^0-9]/,"",$2); print $2}')
  [[ "$size" =~ ^[0-9]+$ ]] || fail "volume dry-run illisible"
  (( size <= 52428800 )) || fail "budget de 50 Mio dépassé : ${size} octets"
  rsync -a --exclude=/runtime --exclude=/review-inbox --exclude=/outbox --exclude=/.private --exclude='__pycache__' --exclude='*.pyc' "$source_dir/" "$stage/"
  LEODAGAN_OUTBOX="$LEODAGAN_OUTBOX" docker compose -f "$stage/compose.yaml" config --quiet
  docker run --rm --init --network none --entrypoint hermes -v "$stage/plugins/leodagan-editorial:/tmp/leodagan-editorial:ro" "$HERMES_IMAGE" plugins validate /tmp/leodagan-editorial
  ln -s "releases/$stamp/leodagan" "$deploy_root/current.new"
  python3 - "$deploy_root/current.new" "$deploy_root/current" <<'PY'
import os, sys
os.replace(sys.argv[1], sys.argv[2])
PY
  provision_config initial
  printf 'Release préparée : %s\n' "$stage"
}
backup() {
  [[ -f "$private_dir/backup.pass" ]] || fail "phrase secrète absente : $private_dir/backup.pass (mode 600)"
  [[ $(stat -f '%Lp' "$private_dir/backup.pass" 2>/dev/null || stat -c '%a' "$private_dir/backup.pass") == 600 ]] || fail "backup.pass doit être en mode 600"
  [[ -n "$(docker volume ls -q --filter name='^hermes-leodagan-data$')" ]] || fail "volume Léodagan absent"
  compose stop leodagan
  mkdir -p "$private_dir/backups"
  chmod 700 "$private_dir/backups"
  local target
  target="$private_dir/backups/leodagan-$(date -u +%Y%m%dT%H%M%SZ).tar.enc"
  docker run --rm --network none --read-only --entrypoint sh -v hermes-leodagan-data:/data:ro "$HERMES_IMAGE" -c 'cd /data && tar -cf - .' |
    openssl enc -aes-256-cbc -pbkdf2 -salt -pass "file:$private_dir/backup.pass" -out "$target"
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$private_dir/backup.pass" -in "$target" | tar -tf - >/dev/null
  shasum -a 256 "$target" > "$target.sha256"
  chmod 600 "$target" "$target.sha256"
  printf 'Sauvegarde chiffrée vérifiée : %s\n' "$target"
}
restore() {
  local archive="${2:-}"
  [[ -f "$archive" && -f "$archive.sha256" ]] || fail "archive et somme requis"
  [[ -f "$private_dir/backup.pass" ]] || fail "backup.pass absent"
  [[ -z "$(docker ps -aq --filter name='^/hermes-leodagan$')" ]] || fail "conteneur Léodagan encore présent"
  [[ -z "$(docker volume ls -q --filter name='^hermes-leodagan-data$')" ]] || fail "restauration uniquement vers un volume absent"
  shasum -a 256 -c "$archive.sha256"
  stage=$(mktemp -d "${TMPDIR:-/private/tmp}/leodagan-restore.XXXXXXXX")
  chmod 700 "$stage"
  trap 'rm -rf -- "$stage"' EXIT
  openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$private_dir/backup.pass" -in "$archive" -out "$stage/volume.tar"
  python3 - "$stage/volume.tar" <<'PY'
import sys, tarfile
from pathlib import PurePosixPath
total = 0
with tarfile.open(sys.argv[1], 'r:') as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit('Archive non sûre : chemin ou lien refusé')
        total += member.size
        if total > 1073741824:
            raise SystemExit('Archive non sûre : budget de 1 Gio dépassé')
print(f'Archive validée : {total} octets, aucun lien suivi')
PY
  docker volume create hermes-leodagan-data >/dev/null
  docker run --rm --network none --entrypoint sh -i -v hermes-leodagan-data:/data "$HERMES_IMAGE" -c 'cd /data && tar -xf -' < "$stage/volume.tar"
  printf 'Volume restauré, service toujours arrêté. Vérifier les données avant start.\n'
}
configure() {
  check_paths
  mkdir -p "$private_dir" "$LEODAGAN_OUTBOX"
  chmod 700 "$private_dir" "$LEODAGAN_OUTBOX"
  if [[ ! -e "$env_file" ]]; then
    (umask 077; cat > "$env_file" <<'EOF'
SLACK_ALLOWED_USERS=
SLACK_ALLOWED_CHANNELS=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
EOF
    )
  fi
  if [[ -L "$deploy_root/current" && -n "$(docker volume ls -q --filter name='^hermes-leodagan-data$')" ]]; then
    provision_config replace
  fi
  printf 'Fichier privé à compléter : %s\nAucune valeur affichée.\n' "$env_file"
}
preflight() {
  [[ -f "$env_file" ]] || fail "configurer d'abord $env_file"
  [[ -s "$bot_token_file" && -s "$app_token_file" ]] || fail "fichiers de token Slack absents"
  [[ $(stat -f '%Lp' "$bot_token_file" 2>/dev/null || stat -c '%a' "$bot_token_file") == 600 ]] || fail "token bot : mode 600 requis"
  [[ $(stat -f '%Lp' "$app_token_file" 2>/dev/null || stat -c '%a' "$app_token_file") == 600 ]] || fail "token app : mode 600 requis"
  [[ ! -L "$telegram_token_file" ]] || fail "token Telegram : lien symbolique refusé"
  if [[ -e "$telegram_token_file" ]]; then
    [[ -s "$telegram_token_file" ]] || fail "token Telegram vide"
    [[ $(stat -f '%Lp' "$telegram_token_file" 2>/dev/null || stat -c '%a' "$telegram_token_file") == 600 ]] || fail "token Telegram : mode 600 requis"
  fi
  python3 - "$env_file" "$telegram_token_file" <<'PY'
import sys
from pathlib import Path
data={}
for line in Path(sys.argv[1]).read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1); data[k.strip()]=v.strip()
for k in ('SLACK_ALLOWED_USERS','SLACK_ALLOWED_CHANNELS'):
    if not data.get(k): raise SystemExit('Paramètre privé absent : '+k)
telegram_token_present = bool(data.get('TELEGRAM_BOT_TOKEN')) or Path(sys.argv[2]).is_file()
if bool(data.get('TELEGRAM_BOT_TOKEN')) and Path(sys.argv[2]).is_file():
    raise SystemExit('Telegram : choisir un seul emplacement pour le token')
if telegram_token_present != bool(data.get('TELEGRAM_ALLOWED_USERS')):
    raise SystemExit('Telegram : token et ID autorisé doivent être fournis ensemble')
if ',' in data['SLACK_ALLOWED_USERS'] or ',' in data['SLACK_ALLOWED_CHANNELS']:
    raise SystemExit('Un seul utilisateur et un seul canal Slack sont autorisés')
import re
if not re.fullmatch(r'[UW][A-Z0-9]+',data['SLACK_ALLOWED_USERS']):
    raise SystemExit('SLACK_ALLOWED_USERS doit être un ID Slack U… ou W…')
if not re.fullmatch(r'[CG][A-Z0-9]+',data['SLACK_ALLOWED_CHANNELS']):
    raise SystemExit('SLACK_ALLOWED_CHANNELS doit être un ID Slack C… ou G…')
if data.get('TELEGRAM_ALLOWED_USERS') and not re.fullmatch(r'[0-9]+',data['TELEGRAM_ALLOWED_USERS']):
    raise SystemExit('TELEGRAM_ALLOWED_USERS doit être un seul ID numérique')
PY
  [[ $(stat -f '%Lp' "$env_file" 2>/dev/null || stat -c '%a' "$env_file") == 600 ]] || fail "permissions du fichier privé : 600 requis"
  [[ -n "$(docker volume ls -q --filter name='^hermes-leodagan-data$')" ]] || fail "volume Léodagan absent"
  docker run --rm --network none --entrypoint sh -v hermes-leodagan-data:/data:ro "$HERMES_IMAGE" -c 'test -s /data/auth.json' || fail "authentification Codex privée absente"
  docker run --rm --network bridge --entrypoint python -v "$bot_token_file:/run/bot.token:ro" "$HERMES_IMAGE" -c 'from pathlib import Path; from urllib.request import Request,urlopen; import json,sys; token=Path("/run/bot.token").read_text().strip(); req=Request("https://slack.com/api/auth.test",headers={"Authorization":"Bearer "+token});
with urlopen(req,timeout=10) as response:
    data=json.load(response); scopes=set(response.headers.get("x-oauth-scopes","").split(","))
if not data.get("ok") or not {"chat:write","app_mentions:read","groups:history"}.issubset(scopes):
    sys.exit("Scopes Slack requis absents ou bot invalide (chat:write, app_mentions:read, groups:history)")' || fail "audit Slack bot non concluant"
}
await_health() {
  local state
  for _ in {1..24}; do
    state=$(docker inspect hermes-leodagan --format '{{.State.Health.Status}}' 2>/dev/null || true)
    [[ "$state" == healthy ]] && return 0
    [[ "$state" == unhealthy ]] && return 1
    sleep 5
  done
  return 1
}
update() {
  preflight
  [[ -L "$deploy_root/current" ]] || fail "release active absente"
  local previous
  previous=$(readlink "$deploy_root/current")
  backup
  install
  provision_config replace
  if compose up -d --no-build leodagan && await_health; then
    printf 'Nouvelle release saine : %s\n' "$(readlink "$deploy_root/current")"
  else
    compose down || true
    ln -s "$previous" "$deploy_root/current.rollback"
    python3 - "$deploy_root/current.rollback" "$deploy_root/current" <<'PY'
import os, sys
os.replace(sys.argv[1], sys.argv[2])
PY
    provision_config replace
    fail "update échouée : image et configuration précédentes rétablies, service arrêté ; restaurer la sauvegarde si le schéma a changé"
  fi
}
case "${1:-}" in
  install) install ;;
  configure) configure ;;
  start) preflight; compose up -d --no-build leodagan; await_health || fail "gateway non sain"; compose ps leodagan ;;
  stop) compose stop leodagan ;;
  restart) preflight; compose restart leodagan; await_health || fail "gateway non sain après redémarrage"; compose ps leodagan ;;
  status) compose ps leodagan ;;
  logs) compose logs --tail "${2:-100}" leodagan | sed -E 's/xox[bap]-[A-Za-z0-9-]+/[REDACTED]/g; s/xapp-[A-Za-z0-9-]+/[REDACTED]/g; s/[0-9]{8,}:[A-Za-z0-9_-]{20,}/[REDACTED]/g; s/Bearer [A-Za-z0-9._-]+/Bearer [REDACTED]/g' ;;
  backup) backup ;;
  restore) restore "$@" ;;
  update) update ;;
  uninstall) compose down; printf 'Conservés : volume hermes-leodagan-data, %s, %s\n' "$private_dir" "$LEODAGAN_OUTBOX" ;;
  purge)
    check_paths
    printf 'Cibles de purge :\n'; du -sh "$deploy_root" "$private_dir" "$LEODAGAN_OUTBOX" "$source_dir/runtime" "$source_dir/review-inbox" 2>/dev/null || true
    if [[ -d "$private_dir" ]]; then find "$private_dir" -maxdepth 2 -type f -exec du -h {} +; fi
    if docker volume inspect hermes-leodagan-data --format '{{.Name}} {{.Mountpoint}}' 2>/dev/null; then
      docker run --rm --network none --entrypoint du -v hermes-leodagan-data:/data:ro "$HERMES_IMAGE" -sh /data
    fi
    printf 'Confirmer exactement « PURGER hermes-leodagan » : '
    read -r answer
    [[ "$answer" == 'PURGER hermes-leodagan' ]] || fail "purge annulée"
    if [[ -L "$deploy_root/current" ]]; then compose down; fi
    if [[ -n "$(docker volume ls -q --filter name='^hermes-leodagan-data$')" ]]; then
      docker volume rm hermes-leodagan-data >/dev/null || fail "volume non supprimé ; autres chemins conservés"
    fi
    rm -rf -- "$deploy_root" "$private_dir" "$LEODAGAN_OUTBOX" "$source_dir/runtime" "$source_dir/review-inbox"
    printf 'Ressources Léodagan listées supprimées.\n'
    ;;
  *) printf 'Usage: %s {install|configure|start|stop|restart|status|logs|backup|restore ARCHIVE|update|uninstall|purge}\n' "$0"; exit 2 ;;
esac
