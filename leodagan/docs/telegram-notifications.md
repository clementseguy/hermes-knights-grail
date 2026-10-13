# Notifications Telegram

Léodagan utilisera Telegram comme canal de notification unidirectionnel. Le
bot ne reçoit pas de commandes métier et ne publie jamais sur LinkedIn.

## Préparation manuelle

1. Créer un bot dédié via `@BotFather`, avec un nom et un username propres à
   Léodagan.
2. Récupérer l'identifiant numérique Telegram de Clément Seguy.
3. Copier le token et cet identifiant dans `runtime/.env`, à partir de
   `config/telegram.env.example`. Ce fichier n'est jamais versionné.
4. Ajouter seulement `TELEGRAM_BOT_TOKEN` et `TELEGRAM_ALLOWED_USERS` : ne pas
   activer de webhook, groupe, commande ou utilisateur supplémentaire.
5. Redémarrer le gateway, envoyer un unique message de test, vérifier le refus
   depuis un autre compte, puis supprimer le message de test si souhaité.

## Contrat de notification

Une notification ne part que lorsqu'une édition `PRET_A_RELIRE` a été validée
dans son dossier de revue. Elle contient : le statut, le sujet et le chemin
local du dossier. Elle ne contient jamais le post complet, les sources, un
secret ou un lien de publication.

Les erreurs critiques (premier échec de quota, erreur d'écriture et échec de
livraison) et le rétablissement après quota doivent être notifiés une seule
fois chacun. Lorsque Slack sera configuré, le même événement sera envoyé au
canal Slack autorisé. Les éditions `NON_PUBLIABLE` restent silencieuses, sauf
décision contraire du propriétaire.

## Révocation

En cas de perte du token, le révoquer dans `@BotFather`, arrêter Léodagan,
retirer la valeur de `runtime/.env`, puis créer et tester un nouveau token.
