"""
Facebook Ads Dashboard API for Vercel
"""
import json
import os
import requests
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": ["*"]}}, methods=["GET", "POST"])

# Paths - Vercel uses /var/task
BASE_DIR = '/var/task'
DATA_FILE = os.path.join(BASE_DIR, 'data', 'facebook_ads_latest.json')
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')

@app.after_request
def add_headers(r):
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['X-Frame-Options'] = 'DENY'
    return r

def load_json():
    try:
        with open(DATA_FILE, 'r') as f:
            d = json.load(f)
            return {'status': 'success', 'data': d} if isinstance(d, list) else d
    except:
        return {'status': 'error', 'message': 'Arquivo nao encontrado'}

def load_cfg():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_cfg(c):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(c, f, indent=4)

def token_valid(t):
    if not t: return False
    try:
        r = requests.get('https://graph.facebook.com/v18.0/me', params={'access_token': t}, timeout=10)
        return 'id' in r.json()
    except: return False

def calc_metrics(row):
    spend = float(row.get("spend", 0))
    clicks = float(row.get("clicks", 0))
    imp = float(row.get("impressions", 0))
    inline = float(row.get("inline_link_clicks", 0))
    purchases = float(row.get("website_purchases", 0))
    roas = 0
    if row.get("website_purchase_roas"):
        roas = float(row["website_purchase_roas"][0].get("value", 0)) if row["website_purchase_roas"] else 0
    return {
        "cpa": round(spend/purchases, 2) if purchases else 0,
        "roas": roas,
        "ctr": round((clicks/imp)*100, 2) if imp else 0,
        "connect_rate": round((inline/clicks)*100, 2) if clicks else 0
    }

def fetch_data(start=None, end=None):
    cfg = load_cfg()
    token = cfg["facebook"]["access_token"]
    acid = cfg["facebook"]["ad_account_id"]
    
    if not token_valid(token):
        return None, "Token invalido"
    
    url = f"https://graph.facebook.com/v18.0/act_{acid}/insights"
    params = {
        "access_token": token,
        "level": "account",
        "fields": "impressions,clicks,spend,reach,cpc,ctr,cpm,frequency,inline_link_clicks,website_purchase_roas,add_to_cart,initiate_checkout,actions",
        "limit": 500,
        "time_increment": 1
    }
    if start and end:
        params["time_range"] = json.dumps({"since": start, "until": end})
    else:
        params["date_preset"] = "last_30d"
    
    try:
        r = requests.get(url, params=params, timeout=30)
        d = r.json()
        if "error" in d:
            return None, d['error'].get('message', 'Erro API')
        
        processed = []
        for row in d.get("data", []):
            m = calc_metrics(row)
            purchases = 0
            for a in row.get("actions", []):
                if a.get("action_type") == "purchase":
                    purchases = int(float(a.get("value", 0)))
            processed.append({
                "date_start": row.get("date_start", ""),
                "date_stop": row.get("date_stop", ""),
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "spend": row.get("spend", 0),
                "reach": row.get("reach", 0),
                "cpc": row.get("cpc", 0),
                "ctr": row.get("ctr", 0),
                "cpm": row.get("cpm", 0),
                "inline_link_clicks": row.get("inline_link_clicks", 0),
                "add_to_cart": row.get("add_to_cart", 0),
                "initiate_checkout": row.get("initiate_checkout", 0),
                "website_purchases": purchases,
                "roas": m.get("roas", 0),
                "cpa": m.get("cpa", 0),
                "connect_rate": m.get("connect_rate", 0)
            })
        return processed, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'dashboard', 'dashboard', 'index.html'))

@app.route('/api/data')
def get_data():
    return jsonify(load_json())

@app.route('/api/config')
def get_config():
    c = load_cfg()
    return jsonify({'token': c.get('token', {}), 'expires_at': c.get('token', {}).get('expires_at')})

@app.route('/api/salvar-token', methods=['POST'])
def set_token():
    data = request.get_json()
    token = data.get('token', '').strip()
    if not token or not token_valid(token):
        return jsonify({'status': 'error', 'message': 'Token invalido'})
    c = load_cfg()
    c['facebook']['access_token'] = token
    c['token'] = {'expires_at': (datetime.now() + timedelta(days=60)).isoformat()}
    save_cfg(c)
    return jsonify({'status': 'success', 'message': 'Token salvo!'})

@app.route('/api/update', methods=['POST'])
def update():
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    data, err = fetch_data(start, end)
    if err:
        return jsonify({'status': 'error', 'message': err})
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({'status': 'success', 'message': f'{len(data)} registros!'})

def handler(request):
    return app