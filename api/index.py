"""
Facebook Ads Dashboard API for Vercel 
Version simplified for debugging
"""
import json
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

VERCEL_PROJECT = "dashboard-morari"

# Simple Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["*"]}}, methods=["GET", "POST"])

# Paths
BASE_DIR = os.environ.get('VERCEL_PROJECT', '/var/task')
DATA_FILE = os.path.join(BASE_DIR, 'data', 'facebook_ads_latest.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'config.json')

@app.after_request
def add_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

def load_json():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
            return {'status': 'success', 'data': d} if isinstance(d, list) else d
    except FileNotFoundError:
        return {'status': 'error', 'message': 'Arquivo nao encontrado'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(c):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(c, f, indent=4)

def token_is_valid(t):
    if not t:
        return False
    try:
        r = requests.get('https://graph.facebook.com/v18.0/me', params={'access_token': t}, timeout=5)
        return 'id' in r.json()
    except:
        return False

def calculate_metrics(row):
    spend = float(row.get("spend", 0))
    clicks = float(row.get("clicks", 0))
    impressions = float(row.get("impressions", 0))
    inline_clicks = float(row.get("inline_link_clicks", 0))
    purchases = float(row.get("website_purchases", 0))
    
    roas = 0
    if row.get("website_purchase_roas"):
        roas = float(row["website_purchase_roas"][0].get("value", 0)) if row["website_purchase_roas"] else 0
    
    return {
        "cpa": round(spend / purchases, 2) if purchases else 0,
        "roas": roas,
        "ctr": round((clicks / impressions) * 100, 2) if impressions else 0,
        "connect_rate": round((inline_clicks / clicks) * 100, 2) if clicks else 0
    }

def fetch_facebook_data(start_date=None, end_date=None):
    try:
        cfg = load_config()
    except:
        return None, "Config nao encontrado"
    
    token = cfg.get("facebook", {}).get("access_token", "")
    ad_account_id = cfg.get("facebook", {}).get("ad_account_id", "")
    
    if not token or not ad_account_id:
        return None, "Token ou Ad Account nao configurado"
    
    if not token_is_valid(token):
        return None, "Token invalido"
    
    url = f"https://graph.facebook.com/v18.0/act_{ad_account_id}/insights"
    params = {
        "access_token": token,
        "level": "account",
        "fields": "impressions,clicks,spend,reach,cpc,ctr,cpm,frequency,inline_link_clicks,website_purchase_roas,add_to_cart,initiate_checkout,actions",
        "limit": 500,
        "time_increment": 1
    }
    
    if start_date and end_date:
        params["time_range"] = json.dumps({"since": start_date, "until": end_date})
    else:
        params["date_preset"] = "last_30d"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if "error" in data:
            return None, data['error'].get('message', 'Erro API Facebook')
        
        processed = []
        for row in data.get("data", []):
            metrics = calculate_metrics(row)
            purchases = 0
            for action in row.get("actions", []):
                if action.get("action_type") == "purchase":
                    purchases = int(float(action.get("value", 0)))
            
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
                "roas": metrics.get("roas", 0),
                "cpa": metrics.get("cpa", 0),
                "connect_rate": metrics.get("connect_rate", 0)
            })
        
        return processed, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'Dashboard API running', 'endpoints': ['/api/data', '/api/update', '/api/config', '/api/salvar-token']})

@app.route('/api/data')
def get_data():
    return jsonify(load_json())

@app.route('/api/config')
def get_config():
    try:
        c = load_config()
        return jsonify({
            'configured': bool(c.get('facebook', {}).get('access_token')),
            'expires_at': c.get('token', {}).get('expires_at')
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/salvar-token', methods=['POST'])
def save_token():
    data = request.get_json()
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({'status': 'error', 'message': 'Token vazio'})
    
    if not token_is_valid(token):
        return jsonify({'status': 'error', 'message': 'Token invalido'})
    
    try:
        c = load_config()
        c['facebook']['access_token'] = token
        c['token'] = {'expires_at': (datetime.now() + timedelta(days=60)).isoformat()}
        save_config(c)
        return jsonify({'status': 'success', 'message': 'Token salvo'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/update', methods=['POST'])
def update_data():
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    
    data, error = fetch_facebook_data(start, end)
    
    if error:
        return jsonify({'status': 'error', 'message': error})
    
    if not data:
        return jsonify({'status': 'error', 'message': 'Nenhum dado encontrado'})
    
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return jsonify({'status': 'success', 'message': f'{len(data)} registros atualizados'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Vercel handler
def handler(request):
    return app