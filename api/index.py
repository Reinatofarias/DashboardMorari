import json
import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


ROOT_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard" / "dashboard"
DATA_FILE = ROOT_DIR / "data" / "facebook_ads_latest.json"
GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v18.0")

app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": ["*"]}}, methods=["GET", "POST"])


@app.after_request
def add_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


def json_response(status, message=None, data=None, http_status=200, **extra):
    payload = {"status": status}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload), http_status


def get_facebook_config():
    return {
        "access_token": os.environ.get("FB_ACCESS_TOKEN", "").strip(),
        "ad_account_id": os.environ.get("FB_AD_ACCOUNT_ID", "").strip(),
    }


def token_valid(token):
    if not token:
        return False

    try:
        response = requests.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/me",
            params={"access_token": token},
            timeout=10,
        )
        body = response.json()
        return response.ok and "id" in body
    except requests.RequestException:
        return False


def to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def to_int(value):
    return int(to_float(value))


def action_value(actions, names):
    if not actions:
        return 0

    normalized_names = {name.lower() for name in names}
    total = 0
    for action in actions:
        action_type = str(action.get("action_type", "")).lower()
        if action_type in normalized_names or any(action_type.endswith("." + name) for name in normalized_names):
            total += to_float(action.get("value"))
    return total


def roas_value(row):
    roas = row.get("website_purchase_roas")
    if isinstance(roas, list) and roas:
        return to_float(roas[0].get("value"))
    return to_float(roas)


def process_row(row):
    actions = row.get("actions", [])
    action_values = row.get("action_values", [])
    impressions = to_int(row.get("impressions"))
    clicks = to_int(row.get("clicks"))
    spend = to_float(row.get("spend"))
    inline_clicks = to_int(row.get("inline_link_clicks"))

    purchases = action_value(actions, ["purchase", "omni_purchase", "fb_pixel_purchase"])
    purchase_value = action_value(action_values, ["purchase", "omni_purchase", "fb_pixel_purchase"])
    add_to_cart = action_value(actions, ["add_to_cart", "omni_add_to_cart", "fb_pixel_add_to_cart"])
    initiate_checkout = action_value(actions, ["initiate_checkout", "omni_initiated_checkout", "fb_pixel_initiate_checkout"])
    add_payment_info = action_value(actions, ["add_payment_info", "fb_pixel_add_payment_info"])
    complete_registration = action_value(actions, ["complete_registration", "fb_pixel_complete_registration"])
    leads = action_value(actions, ["lead", "onsite_conversion.lead_grouped"])
    landing_page_views = action_value(actions, ["landing_page_view"])
    video_views = action_value(actions, ["video_view"])

    ctr = to_float(row.get("ctr")) or ((clicks / impressions) * 100 if impressions else 0)
    cpa = spend / purchases if purchases else 0
    cpl = spend / leads if leads else 0
    cost_per_landing_page_view = spend / landing_page_views if landing_page_views else 0
    connect_rate = (inline_clicks / clicks) * 100 if clicks else 0
    roas = roas_value(row) or ((purchase_value / spend) if spend and purchase_value else 0)

    return {
        "campaign_id": row.get("campaign_id", ""),
        "campaign_name": row.get("campaign_name", "Todas as campanhas"),
        "adset_id": row.get("adset_id", ""),
        "adset_name": row.get("adset_name", ""),
        "ad_id": row.get("ad_id", ""),
        "ad_name": row.get("ad_name", ""),
        "date_start": row.get("date_start", ""),
        "date_stop": row.get("date_stop", ""),
        "impressions": impressions,
        "clicks": clicks,
        "spend": round(spend, 2),
        "reach": to_int(row.get("reach")),
        "cpc": round(to_float(row.get("cpc")), 2),
        "ctr": round(ctr, 2),
        "cpm": round(to_float(row.get("cpm")), 2),
        "cpp": round(to_float(row.get("cpp")), 2),
        "frequency": round(to_float(row.get("frequency")), 2),
        "inline_link_clicks": inline_clicks,
        "inline_post_engagement": to_int(row.get("inline_post_engagement")),
        "video_views": video_views,
        "add_to_cart": add_to_cart,
        "initiate_checkout": initiate_checkout,
        "add_payment_info": add_payment_info,
        "complete_registration": complete_registration,
        "lead": leads,
        "landing_page_views": landing_page_views,
        "website_purchases": purchases,
        "conversion_value": round(purchase_value, 2),
        "roas": round(roas, 2),
        "cpa": round(cpa, 2),
        "cpl": round(cpl, 2),
        "cost_per_landing_page_view": round(cost_per_landing_page_view, 2),
        "custo_por_resultado": round(cpa, 2),
        "connect_rate": round(connect_rate, 2),
    }


def fetch_facebook_data(start_date=None, end_date=None, level="campaign"):
    config = get_facebook_config()
    token = config["access_token"]
    account_id = config["ad_account_id"].replace("act_", "")

    if not token:
        return None, "FB_ACCESS_TOKEN nao configurado no Vercel."
    if not account_id:
        return None, "FB_AD_ACCOUNT_ID nao configurado no Vercel."
    if not token_valid(token):
        return None, "Token invalido ou expirado."

    params = {
        "access_token": token,
        "level": level,
        "fields": ",".join(
            [
                "campaign_id",
                "campaign_name",
                "adset_id",
                "adset_name",
                "ad_id",
                "ad_name",
                "date_start",
                "date_stop",
                "impressions",
                "clicks",
                "spend",
                "reach",
                "cpc",
                "ctr",
                "cpm",
                "cpp",
                "frequency",
                "inline_link_clicks",
                "inline_post_engagement",
                "actions",
                "action_values",
                "website_purchase_roas",
            ]
        ),
        "limit": 500,
        "time_increment": 1,
    }

    if start_date and end_date:
        params["time_range"] = json.dumps({"since": start_date, "until": end_date})
    else:
        params["date_preset"] = "last_30d"

    try:
        response = requests.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/act_{account_id}/insights",
            params=params,
            timeout=30,
        )
        body = response.json()
    except requests.RequestException as exc:
        return None, str(exc)

    if "error" in body:
        return None, body["error"].get("message", "Erro na API da Meta.")

    return [process_row(row) for row in body.get("data", [])], None


def load_cached_data():
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else data.get("data", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


@app.route("/")
def index():
    return send_file(DASHBOARD_DIR / "index.html")


@app.route("/config-token")
def config_token():
    return send_file(DASHBOARD_DIR / "config-token.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_file(DASHBOARD_DIR / filename)


@app.route("/api/data")
def data():
    cached = load_cached_data()
    return json_response("success", data=cached, updated_at=datetime.utcnow().isoformat() + "Z")


@app.route("/api/config")
def config_status():
    config = get_facebook_config()
    return jsonify(
        {
            "configured": bool(config["access_token"] and config["ad_account_id"]),
            "ad_account_id": config["ad_account_id"],
            "environment": "vercel" if os.environ.get("VERCEL") else "local",
        }
    )


@app.route("/api/salvar-token", methods=["POST"])
def save_token_not_available():
    return json_response(
        "error",
        "No Vercel, configure o token nas variaveis de ambiente FB_ACCESS_TOKEN e FB_AD_ACCOUNT_ID.",
        http_status=400,
    )


@app.route("/api/update", methods=["POST"])
def update():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    level = request.args.get("level", "campaign")
    if level not in {"account", "campaign", "adset", "ad"}:
        level = "campaign"

    data, error = fetch_facebook_data(start_date, end_date, level)

    if error:
        return json_response("error", error, http_status=400)
    if not data:
        return json_response("error", "Nenhum dado encontrado para o periodo.", http_status=404)

    return json_response("success", f"{len(data)} registros carregados.", data=data)


def handler(request):
    return app
