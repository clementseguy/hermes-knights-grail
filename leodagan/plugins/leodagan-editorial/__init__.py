"""Outils métier à surface bornée pour le gateway Hermes."""
import json
from .store import Store
from .reader import read_public_article
from .review import review_candidate


def _handle(operation):
    def handler(args, **_):
        try:
            store = Store()
            try:
                return json.dumps({"success": True, "result": operation(store, args)}, ensure_ascii=False)
            finally:
                store.db.close()
        except (ValueError, KeyError, RuntimeError) as exc:
            return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)
    return handler


def _schema(name, description, properties, required):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}


def _read(args, **_):
    try:
        return json.dumps({"success": True, "result": read_public_article(args["url"])}, ensure_ascii=False)
    except (ValueError, KeyError) as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _review(args, llm):
    store = Store()
    review_id = None
    try:
        candidate = {"identifier": args["identifier"], "post": args["post"],
                     "image_prompt": args["image_prompt"], "reasoning": args["reasoning"],
                     "sources": args["sources"]}
        prepared = store.prepare_review(**candidate)
        review_id = prepared["review_id"]
        report, provider, model = review_candidate(llm, candidate)
        result = store.complete_review(review_id, report, provider, model)
        return json.dumps({"success": True, "result": result}, ensure_ascii=False)
    except (ValueError, KeyError, RuntimeError) as exc:
        if review_id is not None:
            store.fail_review(review_id, type(exc).__name__)
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        if review_id is not None:
            store.fail_review(review_id, type(exc).__name__)
        return json.dumps({"success": False, "error": "relecture indisponible : " + type(exc).__name__}, ensure_ascii=False)
    finally:
        store.db.close()


def register(ctx):
    text = lambda d: {"type": "string", "description": d}
    review_fields = {
        "thesis": text("Thèse de l'article"),
        "evidence": text("Faits et preuves effectivement lus"),
        "limits": text("Limites, hypothèses et incertitudes de la source"),
        "cto_objection": text("Objection critique du CTO ou DSI"),
        "executive_impact": text("Conséquences opérationnelles pour un dirigeant"),
    }
    source_fields = {
        "url": text("URL HTTPS exacte de l'article demandé"),
        "final_url": text("URL finale après redirection, si différente de l'URL demandée"),
        "access_status": text("read, partial, inaccessible ou user"),
        "accessed_at": text("Horodatage ISO 8601 avec fuseau horaire"),
        "critical_review": {"type": "object", "properties": review_fields,
                            "required": list(review_fields)},
    }
    metric_fields = {
        "type": text("IMPRESSION, REACTION ou LIKE_MANUAL"),
        "value": {"type": "integer", "description": "Nombre entier non négatif fourni ou lu"},
        "origin": text("Provenance de la mesure : API officielle ou Clément"),
    }
    ctx.register_tool("editorial_read_source", "leodagan_editorial",
        _schema("editorial_read_source", "Lire uniquement le texte public d'un article HTTPS, avec limites réseau et sans session authentifiée.",
            {"url": text("URL HTTPS de l'article demandé par Clément")}, ["url"]),
        _read)
    ctx.register_tool("editorial_create", "leodagan_editorial",
        _schema("editorial_create", "Créer un brouillon après réception d'une intention et de liens.",
            {"intent": text("Intention de Clément"), "urls": {"type": "array", "items": {"type": "string"}},
             "platform": text("slack ou telegram"), "thread": text("Identifiant du fil ou DM"),
             "message_key": text("Identifiant unique du message"), "identifier": text("Identifiant à deux mots, facultatif")},
            ["intent", "urls", "platform", "thread", "message_key"]),
        _handle(lambda s, a: s.create(a["intent"], a["urls"], a["platform"], a["thread"], a["message_key"], a.get("identifier", ""))))
    ctx.register_tool("editorial_add_source", "leodagan_editorial",
        _schema("editorial_add_source", "Ajouter un lien à un dossier existant avant une nouvelle version.",
            {"identifier": text("Identifiant du brouillon"), "url": text("Nouveau lien HTTPS fourni ou confirmé par Clément")},
            ["identifier", "url"]),
        _handle(lambda s, a: s.add_source(a["identifier"], a["url"])))
    ctx.register_tool("editorial_review", "leodagan_editorial",
        _schema("editorial_review", "Soumettre le brouillon à une relecture LLM indépendante DSI, CTO, RSSI et CEO avant enregistrement.",
            {"identifier": text("Identifiant du brouillon"), "post": text("Post candidat exact"),
             "image_prompt": text("Prompt image candidat 16:9"), "reasoning": text("Angle et incertitudes"),
             "sources": {"type": "array", "items": {"type": "object",
                                                     "properties": source_fields,
                                                     "required": ["url", "access_status", "accessed_at", "critical_review"]}}},
            ["identifier", "post", "image_prompt", "reasoning", "sources"]),
        lambda args, **_: _review(args, ctx.llm))
    ctx.register_tool("editorial_save", "leodagan_editorial",
        _schema("editorial_save", "Enregistrer uniquement le texte exact approuvé par une relecture indépendante.",
            {"identifier": text("Identifiant du brouillon"),
             "review_id": {"type": "integer", "description": "Identifiant de relecture APPROVED retourné par editorial_review"}},
            ["identifier", "review_id"]),
        _handle(lambda s, a: s.save(a["identifier"], a["review_id"])))
    ctx.register_tool("editorial_get", "leodagan_editorial",
        _schema("editorial_get", "Retrouver un brouillon et ses versions, ou les règles explicites.",
            {"identifier": text("Identifiant ; vide pour les règles")}, []),
        _handle(lambda s, a: s.get(a["identifier"]) if a.get("identifier") else s.rules()))
    ctx.register_tool("editorial_feedback", "leodagan_editorial",
        _schema("editorial_feedback", "Enregistrer texte publié, comparaison, métriques et correction explicite.",
            {"identifier": text("Identifiant"), "final_text": text("Texte publié réellement lu ou fourni"),
             "origin": text("official_api, public_page ou user"), "comparison": text("Différences et explications"),
             "explicit_rule": text("Correction durable explicitement formulée par Clément seulement"),
             "linkedin_url": text("Lien public facultatif"),
             "metrics": {"type": "array", "items": {"type": "object",
                                                    "properties": metric_fields,
                                                    "required": list(metric_fields)}}},
            ["identifier", "final_text", "origin", "comparison"]),
        _handle(lambda s, a: s.feedback(a["identifier"], a["final_text"], a["origin"], a["comparison"], a.get("explicit_rule", ""), a.get("linkedin_url", ""), a.get("metrics", []))))
    ctx.register_tool("editorial_rules", "leodagan_editorial",
        _schema("editorial_rules", "Lister, corriger ou retirer les règles éditoriales explicitement confirmées.",
            {"action": text("list, update ou revoke"), "rule_id": {"type": "integer"},
             "text": text("Nouveau texte pour update")}, ["action"]),
        _handle(lambda s, a: s.rules() if a["action"] == "list" else
            s.update_rule(a["rule_id"], a["text"]) if a["action"] == "update" else
            s.revoke_rule(a["rule_id"]) if a["action"] == "revoke" else
            (_ for _ in ()).throw(ValueError("action invalide"))))
