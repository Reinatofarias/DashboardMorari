import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

def get_base_dir():
    if os.environ.get('VERCEL'):
        return '/var/task'
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(get_base_dir(), "config", "config.json")
DATA_PATH = os.path.join(get_base_dir(), "data")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_access_token():
    return ensure_valid_token()

def get_ad_account_id():
    config = load_config()
    return config["facebook"]["ad_account_id"]

def get_app_id():
    config = load_config()
    return config["facebook"]["app_id"]

def get_app_secret():
    config = load_config()
    return config["facebook"]["app_secret"]

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

def get_long_lived_token(short_lived_token):
    url = f"https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": get_app_id(),
        "client_secret": get_app_secret(),
        "fb_exchange_token": short_lived_token
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if "access_token" in data:
            return data["access_token"], data.get("expires_in", 0)
    except Exception as e:
        print(f"Error getting long-lived token: {e}")
    return None, 0

def refresh_token():
    print("Token expired! Você precisa gerar um novo token manualmente.")
    print("Acesse: https://developers.facebook.com/tools/explorer/")
    print("1. Selecione seu app")
    print("2. Adicione permissão: ads_read, ads_management")
    print("3. Clique em 'Get Token'")
    print("4. Cole o novo token no arquivo config/config.json")
    return None

def ensure_valid_token():
    config = load_config()
    current_token = config["facebook"].get("access_token", "")
    expires_at = config.get("token", {}).get("expires_at")
    
    if current_token and is_token_valid(current_token):
        if expires_at:
            try:
                exp_date = datetime.fromisoformat(expires_at)
                if exp_date > datetime.now() + timedelta(hours=1):
                    print(f"Token valido ate {expires_at}")
                    return current_token
            except:
                pass
        
        print("Token existente valido, usando...")
        return current_token
    
    print("Token invalido ou expirado!")
    new_token = refresh_token()
    if new_token:
        return new_token
    
    if current_token and is_token_valid(current_token):
        return current_token
    
    raise Exception("Token invalido! Gere um novo token em https://developers.facebook.com/tools/explorer/")

def get_insights(account_id=None, date_preset="last_30d", level="account", start_date=None, end_date=None, time_increment=None):
    token = ensure_valid_token()
    if account_id is None:
        account_id = get_ad_account_id()
    
    url = f"https://graph.facebook.com/v18.0/act_{account_id}/insights"
    params = {
        "access_token": token,
        "level": level,
        "fields": "impressions,clicks,spend,reach,cpc,ctr,cpm,frequency,inline_link_clicks,inline_post_engagement,video_play_actions,website_purchase_roas,add_to_cart,initiate_checkout,add_payment_info,complete_registration,lead,actions",
        "limit": 500
    }
    
    if start_date and end_date:
        params["time_range"] = json.dumps({"since": start_date, "until": end_date})
    else:
        params["date_preset"] = date_preset
    
    if time_increment:
        params["time_increment"] = time_increment
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"API Error: {data['error']}")
        return []
    
    return data.get("data", [])

def extract_purchases(actions):
    """Extract purchase count from actions"""
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
    purchases_value = float(row.get("website_purchases_value", 0))
    
    roas = 0
    if "website_purchase_roas" in row and row["website_purchase_roas"]:
        if isinstance(row["website_purchase_roas"], list) and len(row["website_purchase_roas"]) > 0:
            roas = float(row["website_purchase_roas"][0].get("value", 0))
    elif spend > 0 and purchases_value > 0:
        roas = round(purchases_value / spend, 2)
    
    metrics = {
        "cpa": round(spend / purchases, 2) if purchases > 0 else 0,
        "custo_por_resultado": round(spend / purchases, 2) if purchases > 0 else 0,
        "roas": roas,
        "ctr": round((clicks / impressions) * 100, 2) if impressions > 0 else 0,
        "connect_rate": round((inline_clicks / clicks) * 100, 2) if clicks > 0 else 0,
        "custo_por_initiate_checkout": round(spend / init_checkouts, 2) if init_checkouts > 0 else 0
    }
    
    return metrics

def run_full_extraction(start_date=None, end_date=None):
    print("Starting Facebook Ads extraction...")
    
    account_id = get_ad_account_id()
    print(f"Fetching insights for account: {account_id}")
    
    insights = get_insights(account_id, start_date=start_date, end_date=end_date, time_increment=1)
    
    if not insights:
        print("No insights data found")
        return
    
    processed_data = []
    
    for row in insights:
        calc_metrics = calculate_metrics(row)
        purchases = extract_purchases(row.get("actions", []))
        
        processed_row = {
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
            "inline_post_engagement": row.get("inline_post_engagement", 0),
            "video_play_actions": row.get("video_play_actions", 0),
            "add_to_cart": row.get("add_to_cart", 0),
            "initiate_checkout": row.get("initiate_checkout", 0),
            "add_payment_info": row.get("add_payment_info", 0),
            "complete_registration": row.get("complete_registration", 0),
            "lead": row.get("lead", 0),
            "website_purchases": purchases,
            "website_purchases_value": purchases * calc_metrics.get("roas", 0) if calc_metrics.get("roas", 0) > 0 else 0,
            "roas": calc_metrics.get("roas", 0),
            "cpa": calc_metrics.get("cpa", 0),
            "custo_por_resultado": calc_metrics.get("custo_por_resultado", 0),
            "connect_rate": calc_metrics.get("connect_rate", 0),
            "custo_por_initiate_checkout": calc_metrics.get("custo_por_initiate_checkout", 0)
        }
        
        processed_data.append(processed_row)
    
    df = pd.DataFrame(processed_data)
    
    output_excel = os.path.join(DATA_PATH, "facebook_ads_latest.xlsx")
    output_csv = os.path.join(DATA_PATH, "facebook_ads_latest.csv")
    output_json = os.path.join(DATA_PATH, "facebook_ads_latest.json")
    
    df.to_excel(output_excel, index=False)
    df.to_csv(output_csv, index=False)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data exported to {output_excel}")
    print(f"Data exported to {output_csv}")
    print(f"JSON exported to {output_json}")
    print("Extraction complete!")
    return processed_data

if __name__ == "__main__":
    start_date = None
    end_date = None
    
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == '--start_date' and i + 1 < len(sys.argv):
                start_date = sys.argv[i + 1]
            elif arg == '--end_date' and i + 1 < len(sys.argv):
                end_date = sys.argv[i + 1]
    
    run_full_extraction(start_date=start_date, end_date=end_date)
