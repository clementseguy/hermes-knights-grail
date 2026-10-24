# Recettes restantes au 24 octobre 2026

- [x] Auditer l'application Slack existante, les scopes `app_mentions:read`, `chat:write`, `channels:history` et `groups:history`, Socket Mode et les allowlists ; conserver les jetons dans deux fichiers privés séparés, hors dépôt. `conversations.replies` a relu le fil réel après propagation de `groups:history`.
- [x] Authentifier `openai-codex` dans le seul volume Léodagan ; vérifier un appel réel à `gpt-5.6-terra` effort `medium` et l'absence de bascule fournisseur. Le renouvellement et les limites de quota à long terme restent à surveiller.
- [x] Livrer `silex-bleu` v1 par Slack, puis retrouver post et prompt après redémarrage ; sauvegarder et restaurer le brouillon dans un volume isolé.
- [x] Créer le bot Telegram dédié, fournir token/ID en privé, activer Telegram et confirmer le polling sans webhook ni groupes.
- [x] Tester un nouveau DM Telegram autorisé : `rempart-agent` v1, post et prompt livrés, sauvegardés et retrouvés après redémarrage.
- [x] Retrouver depuis Slack le brouillon Telegram `rempart-agent` v1 avec post et prompt exacts après correction du skill.
- [ ] Tester le refus d'une autre identité Telegram ou Slack et d'un groupe Telegram.
- [ ] Compléter T-CANAL (refus d'une autre identité et d'un autre canal), T-STYLE (5 sujets notés par Clément), T-CRIT (second article), T-MEM entre sessions réelles, T-ISO dynamique et T-OPS (panne de livraison et reprise).
- [ ] Si la voix éditoriale doit être recalibrée sur les sept posts du corpus, obtenir un export remis par Clément : les trois premiers liens publics testés le 18 octobre n'ont pas fourni leur contenu (`Cache miss`) ; ne pas contourner LinkedIn. La grille de notation est dans `docs/grille-recette-editoriale.md`.
- [ ] Tester le cycle d'un post final réellement publié, sa comparaison et les métriques fournies ; demander les droits LinkedIn de lecture seule uniquement si Clément choisit ce niveau d'accès.
- [ ] Éprouver l'update et le retour arrière en staging ; fixer le traitement des sauvegardes lors d'une suppression ciblée.

Voir `docs/traceability.md` pour l'état détaillé. Aucun cron ne doit être créé ni repris.
