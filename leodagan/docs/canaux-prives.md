# Mettre en service les canaux privés

Les jetons et les IDs d'exploitation sont dans `~/Library/Application Support/HermesLeodagan/`, **hors du dépôt Git**. Ne les envoyer ni dans Slack, ni dans Telegram, ni dans une issue. Le dossier est en mode `700` et chaque fichier de jeton en mode `600`.

## Slack : permettre la reprise des fils

L'application `Hermes — Leodagan` est reliée par Socket Mode ; le bot a `chat:write`, `app_mentions:read`, `channels:history` et `groups:history`, et l'événement `app_mention` a fonctionné. **Le 24 octobre, l'appel réel `conversations.replies` sur un fil de `#agent-leodagan` a demandé `groups:history`** (`missing_scope`, `needed=groups:history`) malgré l'ID `C…` du canal. Après propagation de ce droit, le même appel a relu trois messages du fil. Les IDs privés déjà configurés correspondent à Clément et à ce canal ; ne pas les remplacer.

1. Ouvrir [Your Apps](https://api.slack.com/apps), choisir **Hermes — Leodagan**, puis **OAuth & Permissions** dans le menu de gauche.
2. Descendre à **Scopes → Bot Token Scopes**. Cliquer **Add an OAuth Scope**, rechercher et sélectionner `groups:history`. Ne pas l'ajouter dans **User Token Scopes**. `channels:history` a déjà été accordé et vérifié. `channels:read` n'est pas nécessaire pour reprendre un fil lorsque son ID est déjà connu.
3. Remonter à **OAuth Tokens for Your Workspace**, cliquer **Reinstall to Workspace** (ou **Install to Workspace**) et approuver l'accès. Un changement de scopes ne modifie pas les jetons déjà installés sans réinstallation.
4. Dans **Event Subscriptions**, vérifier **Enable Events** et **Subscribe to bot events → app_mention** ; cliquer **Save Changes** si nécessaire. Dans **Socket Mode**, vérifier **Enable Socket Mode**. Dans **Basic Information → App-Level Tokens**, vérifier que le jeton d'application possède `connections:write`. Aucun **Request URL** public n'est nécessaire avec Socket Mode.
5. Dans Slack, ouvrir `#agent-leodagan` et vérifier que le bot est membre ; sinon saisir `/invite @Hermes — Leodagan` en sélectionnant l'application proposée par Slack. Après réinstallation, vérifier les fichiers privés `slack-leodagan-bot.token` et `slack-leodagan-app.token` ; si Slack a renouvelé un jeton, remplacer uniquement son fichier, mode `600`.
6. Une fois la reconnexion confirmée par `./leodagan/scripts/leodagan.sh logs 100`, envoyer **depuis le compte de Clément**, dans un nouveau message ou fil du canal, une vraie mention du bot. Le texte envoyé par une application tierce est ignoré par Hermes. Pour tester la reprise, répondre dans un fil inconnu avec une mention et demander de résumer le contexte du fil ; vérifier l'absence de `missing_scope` dans les journaux.

Si Slack affiche un **nouveau** jeton `xoxb-` après réinstallation, le déposer sans l'écrire dans l'historique du shell :

```sh
python3 - <<'PY'
from getpass import getpass
from pathlib import Path
import os
path = Path.home() / 'Library/Application Support/HermesLeodagan/slack-leodagan-bot.token'
token = getpass('Nouveau Bot User OAuth Token xoxb- : ').strip()
if not token.startswith('xoxb-') or path.is_symlink():
    raise SystemExit('Jeton bot invalide ou lien symbolique refusé')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
try:
    os.fchmod(fd, 0o600)
    os.write(fd, (token + '\n').encode())
finally:
    os.close(fd)
print('Jeton bot privé mis à jour.')
PY
```

Le jeton d'application `xapp-` est distinct ; le remplacer dans `slack-leodagan-app.token` uniquement si l'App-Level Token a lui aussi été régénéré. Après tout remplacement, redémarrer Léodagan de façon contrôlée puis vérifier la reconnexion.

Ce scope donne au bot accès aux messages des canaux publics dont il est membre. La protection de Léodagan repose aussi sur son invitation au seul canal prévu et sur ses allowlists Hermes/Slack.

## Telegram : créer le bot dédié

1. Dans Telegram, ouvrir [@BotFather](https://t.me/BotFather) et vérifier qu'il s'agit du bot officiel. Envoyer `/newbot`.
2. Donner un nom visible, par exemple **Hermes — Léodagan**, puis un nom d'utilisateur unique qui se termine par `bot`, par exemple `hermes_leodagan_bot` si disponible. BotFather remet un jeton. **Ne pas le coller dans le dépôt ni dans ce chat.**
3. Toujours dans BotFather, envoyer `/setjoingroups`, choisir ce bot, puis **Disable**. La configuration Hermes refuse déjà les groupes ; ce réglage Telegram réduit encore l'exposition. Ne pas activer l'inline mode ou un webhook.
4. Dans le Terminal du Mac, exécuter le bloc suivant. La saisie du jeton est masquée et le fichier créé hors dépôt en mode `600` :

   ```sh
   python3 - <<'PY'
   from getpass import getpass
   from pathlib import Path
   import os
   directory = Path.home() / 'Library/Application Support/HermesLeodagan'
   directory.mkdir(mode=0o700, parents=True, exist_ok=True)
   os.chmod(directory, 0o700)
   token = getpass('Jeton donné par BotFather : ').strip()
   if not token or '\n' in token:
       raise SystemExit('Jeton vide ou invalide')
   path = directory / 'telegram-leodagan-bot.token'
   if path.is_symlink():
       raise SystemExit('Lien symbolique refusé')
   fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
   try:
       os.fchmod(fd, 0o600)
       os.write(fd, (token + '\n').encode())
   finally:
       os.close(fd)
   print('Jeton enregistré dans le dossier privé (mode 600).')
   PY
   ```

5. Ouvrir le nouveau bot dans Telegram, appuyer sur **Démarrer** ou envoyer `/start`, puis lui envoyer en **message privé** une phrase unique, par exemple `verification-leodagan-23octobre`. Le bot ne répond pas encore : c'est normal.
6. Pendant que le canal Telegram Hermes est encore désactivé, exécuter depuis la racine du dépôt :

   ```sh
   python3 leodagan/scripts/telegram-identity.py 'verification-leodagan-23octobre'
   ```

   Ce lecteur appelle uniquement `getUpdates` de l'API officielle, cherche la phrase exacte dans un DM dont l'auteur et le chat portent le même ID, et affiche **seulement** `TELEGRAM_ALLOWED_USERS=<ID numérique>`. Il ne confirme ni n'efface les mises à jour. Si aucun ID n'apparaît, renvoyer une phrase neuve au bot et recommencer. Ne pas utiliser ce lecteur une fois Hermes en cours de polling Telegram.
7. Ouvrir `~/Library/Application Support/HermesLeodagan/channels.env` dans un éditeur local et renseigner uniquement `TELEGRAM_ALLOWED_USERS=<ID obtenu>`. Laisser `TELEGRAM_BOT_TOKEN=` vide : le script charge le jeton depuis le fichier séparé. Ne pas toucher aux deux allowlists Slack. Vérifier `chmod 600 "$HOME/Library/Application Support/HermesLeodagan/channels.env"`.

Le 24 octobre, `getMe`, l'absence de webhook, `can_join_groups=false` et le DM de vérification lié à l'ID autorisé ont été vérifiés. `telegram.enabled: true` est déployé ; le polling et la connexion Slack sont confirmés dans le journal privé du gateway. Une nouvelle demande a produit `rempart-agent` v1 avec post, prompt et lecture critique ; le registre l'a retrouvé après sauvegarde et redémarrage. Le refus d'un autre compte reste à tester. Les messages envoyés avant le premier démarrage peuvent être ignorés par le polling Hermes. Aucun port entrant ni groupe Telegram n'est nécessaire. Hermes peut afficher au premier contact « No home channel is set for Telegram » : ce canal d'accueil sert aux livraisons planifiées et aux notifications ; il est volontairement absent pour Léodagan, qui fonctionne à la demande.

Si un jeton est exposé, révoquer celui de Telegram avec `/revoke` dans BotFather, ou renouveler le jeton Slack correspondant dans le portail Slack, puis remplacer le fichier privé concerné et redémarrer le conteneur. Ne pas publier l'ancien jeton pour diagnostiquer l'incident.
