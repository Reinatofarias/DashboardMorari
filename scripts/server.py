import os

# Handle both local and Vercel environments
if os.environ.get('VERCEL'):
    BASE_DIR = '/var/task'
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import requests

app = Flask(__name__)

CORS(app, resources={
    r"/api/*": {"origins": ["*"]}
}, methods=["GET", "POST"], headers=["Content-Type"])

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

DATA_FILE = os.path.join(BASE_DIR, 'data', 'facebook_ads_latest.json')

def load_json_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {'status': 'success', 'data': data}
            return data
    except FileNotFoundError:
        return {'status': 'error', 'message': 'Arquivo de dados nao encontrado.'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

def is_token_valid(token):
    if not token:
        return False
    url = "https://graph.facebook.com/v18.0/me"
    params = {"access_token": token}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return "id" in data
    except:
        return False

def extract_purchases(actions):
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == "purchase":
            return int(float(action.get("value", 0)))
    return 0

def calculate_metrics(row):
    spend = float(row.get("spend", 0))
    clicks = float(row.get("clicks", 0))
    impressions = float(row.get("impressions", 0))
    inline_clicks = float(row.get("inline_link_clicks", 0))
    init_checkouts = float(row.get("initiate_checkout", 0))
    purchases = float(row.get("website_purchases", 0))
    
    roas = 0
    if "website_purchase_roas" in row and row["website_purchase_roas"]:
        if isinstance(row["website_purchase_roas"], list) and len(row["website_purchase_roas"]) > 0:
            roas = float(row["website_purchase_roas"][0].get("value", 0))
    
    return {
        "cpa": round(spend / purchases, 2) if purchases > 0 else 0,
        "roas": roas,
        "ctr": round((clicks / impressions) * 100, 2) if impressions > 0 else 0,
        "connect_rate": round((inline_clicks / clicks) * 100, 2) if clicks > 0 else 0
    }

def fetch_facebook_data(start_date=None, end_date=None):
    config = load_config()
    token = config["facebook"]["access_token"]
    account_id = config["facebook"]["ad_account_id"]
    
    if not is_token_valid(token):
        return None, "Token invalido!"
    
    url = f"https://graph.facebook.com/v18.0/act_{account_id}/insights"
    params = {
        "access_token": token,
        "level": "account",
        "fields": "impressions,clicks,spend,reach,cpc,ctr,cpm,frequency,inline_link_clicks,inline_post_engagement,video_play_actions,website_purchase_roas,add_to_cart,initiate_checkout,add_payment_info,complete_registration,lead,actions",
        "limit": 500
    }
    
    if start_date and end_date:
        params["time_range"] = json.dumps({"since": start_date, "until": end_date})
    else:
        params["date_preset"] = "last_30d"
    
    params["time_increment"] = 1
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if "error" in data:
            return None, data['error'].get('message', 'Erro API')
        
        insights = data.get("data", [])
        processed = []
        
        for row in insights:
            calc = calculate_metrics(row)
            purchases = extract_purchases(row.get("actions", []))
            
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
                "frequency": row.get("frequency", 0),
                "inline_link_clicks": row.get("inline_link_clicks", 0),
                "add_to_cart": row.get("add_to_cart", 0),
                "initiate_checkout": row.get("initiate_checkout", 0),
                "website_purchases": purchases,
                "roas": calc.get("roas", 0),
                "cpa": calc.get("cpa", 0),
                "connect_rate": calc.get("connect_rate", 0)
            })
        
        return processed, None
    except Exception as e:
        return None, str(e)

@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'dashboard', 'dashboard', 'index.html'))

@app.route('/api/data')
def get_data():
    try:
        data = load_json_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/config')
def get_config():
    try:
        config = load_config()
        return jsonify({
            'token': config.get('token', {}),
            'expires_at': config.get('token', {}).get('expires_at')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/salvar-token', methods=['POST'])
def salvar_token():
    try:
        data = request.get_json()
        novo_token = data.get('token', '').strip()
        
        if not novo_token:
            return jsonify({'status': 'error', 'message': 'Token vazio!'})
        
        if not is_token_valid(novo_token):
            return jsonify({'status': 'error', 'message': 'Token invalido!'})
        
        config = load_config()
        config['facebook']['access_token'] = novo_token
        config['token'] = {'expires_at': (datetime.now() + timedelta(days=60)).isoformat()}
        
        save_config(config)
        
        return jsonify({'status': 'success', 'message': 'Token salvo!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/update', methods=['POST'])
def update_data():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        data, error = fetch_facebook_data(start_date, end_date)
        
        if error:
            return jsonify({'status': 'error', 'message': error})
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Nenhum dado encontrado'})
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'status': 'success', 'message': f'{len(data)} registros atualizados!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
