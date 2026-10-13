# Politique opérationnelle — Père Blaise

## Décision

Actions autonomes : inventaire de métadonnées, proposition, suivi local de `a_trier`, expiration des exemples et analyse hebdomadaire non destructive.

Action soumise à validation : seul `range <id>` applique un plan, une fois, dans les douze heures.

Interdits : sortir de `Downloads`/`Documents`, lire un contenu de document (hors empreinte locale), modifier `Documents` hors plan, supprimer définitivement, utiliser un canal ou un utilisateur hors allowlist.

Succès : un plan valide est proposé ou appliqué avec copie vérifiée et original en quarantaine. Échec : le service renvoie un code non sensible et ne déplace rien. Blocage/escalade : absence de téléchargement, plan expiré, authentification, quota ou indisponibilité du planificateur : arrêter au plan proposé et prévenir le propriétaire via le canal demandeur.

## Exception planificateur HTTP

Cette exception ne prescrit **pas** une clé API OpenAI. Le planificateur est Hermes, local sur `127.0.0.1:8643`, authentifié par l’abonnement ChatGPT/Codex via OAuth dans son `auth.json` privé. Le fournisseur choisi est `openai-codex` et le modèle par défaut est `gpt-5.4` ; le catalogue réel du compte reste l’autorité. La clé privée `PERE_BLAISE_API_KEY` protège uniquement l’API locale entre le relais et le conteneur. Le coût est inclus dans l’abonnement Codex, sous réserve de ses limites d’usage. Sans quota ou si le service est indisponible, l’analyse échoue sans plan ni déplacement et aucun repli automatique n’est autorisé. Revue : 13 janvier 2027.
