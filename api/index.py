"""
Facebook Ads Dashboard API for Vercel 
"""
import json
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["*"]}}, methods=["GET", "POST"])

BASE_DIR = '/var/task'
DATA_FILE = os.path.join(BASE_DIR, 'data', 'facebook_ads_latest.json')

@app.after_request
def add_headers(r):
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['X-Frame-Options'] = 'DENY'
    return r

def get_config():
    return {
        "facebook": {
            "access_token": os.environ.get('FB_ACCESS_TOKEN', ''),
            "ad_account_id": os.environ.get('FB_AD_ACCOUNT_ID', '306248590758956')
        }
    }

def load_json():
    try:
        with open(DATA_FILE, 'r') as f:
            d = json.load(f)
            return {'status': 'success', 'data': d} if isinstance(d, list) else d
    except: return {'status': 'error', 'message': 'Nao encontrado'}

def token_valid(t):
    if not t: return False
    try:
        r = requests.get('https://graph.facebook.com/v18.0/me', params={'access_token': t}, timeout=5)
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
    return {"cpa": round(spend/purchases,2) if purchases else 0, "roas": roas, "ctr": round((clicks/imp)*100,2) if imp else 0, "cr": round((inline/clicks)*100,2) if clicks else 0}

def fetch_data(start=None, end=None):
    cfg = get_config()
    token = cfg["facebook"]["access_token"]
    acid = cfg["facebook"]["ad_account_id"]
    
    if not token:
        return None, "Token nao configurado. Configure FB_ACCESS_TOKEN como variavel de ambiente."
    if not token_valid(token):
        return None, "Token invalido"
    if not acid:
        return None, "Ad Account ID nao configurado"
    
    url = f"https://graph.facebook.com/v18.0/act_{acid}/insights"
    p = {"access_token": token, "level": "account", "fields": "impressions,clicks,spend,reach,cpc,ctr,cpm,frequency,inline_link_clicks,website_purchase_roas,add_to_cart,initiate_checkout,actions", "limit": 500, "time_increment": 1}
    if start and end:
        p["time_range"] = json.dumps({"since": start, "until": end})
    else:
        p["date_preset"] = "last_30d"
    
    try:
        r = requests.get(url, params=p, timeout=30)
        d = r.json()
        if "error" in d:
            return None, d['error'].get('message', 'Erro')
        
        processed = []
        for row in d.get("data", []):
            m = calc_metrics(row)
            purchases = 0
            for a in row.get("actions", []):
                if a.get("action_type") == "purchase":
                    purchases = int(float(a.get("value", 0)))
            processed.append({"date_start": row.get("date_start", ""), "date_stop": row.get("date_stop", ""), "impressions": row.get("impressions", 0), "clicks": row.get("clicks", 0), "spend": row.get("spend", 0), "reach": row.get("reach", 0), "cpc": row.get("cpc", 0), "ctr": row.get("ctr", 0), "cpm": row.get("cpm", 0), "inline_link_clicks": row.get("inline_link_clicks", 0), "add_to_cart": row.get("add_to_cart", 0), "initiate_checkout": row.get("initiate_checkout", 0), "website_purchases": purchases, "roas": m.get("roas", 0), "cpa": m.get("cpa", 0), "connect_rate": m.get("cr", 0)})
        return processed, None
    except Exception as e:
        return None, str(e)

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard Meta Ads</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:#0a0a0a;color:#fff}.container{max-width:1400px;margin:0 auto;padding:20px}.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:30px;flex-wrap:wrap;gap:15px}.header h1{color:#FFD700;font-size:24px}.date-range{display:flex;gap:15px;align-items:center}.date-range input{padding:10px;border-radius:5px;border:1px solid #333;background:#1a1a1a;color:#fff}.btn{padding:10px 20px;background:#FFD700;color:#000;border:none;border-radius:5px;cursor:pointer;font-weight:bold}.btn:hover{background:#ffdd00}.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:30px}.kpi-card{background:#1a1a1a;padding:20px;border-radius:10px}.kpi-label{color:#888;font-size:14px;display:block;margin-bottom:5px}.kpi-value{color:#FFD700;font-size:24px;font-weight:bold}.charts-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin-bottom:30px}.chart-card{background:#1a1a1a;padding:20px;border-radius:10px}.chart-card.full-width{grid-column:span 2}.chart-card h2{font-size:16px;margin-bottom:15px;color:#FFD700}.info{background:#1a1a1a;padding:20px;border-radius:10px;text-align:center;color:#888}.error{background:#300;padding:15px;border-radius:10px;color:#f88;text-align:center}</style></head>
<body><div class="container">
<div class="header"><h1>MORARI DASHBOARD</h1><div class="date-range"><input type="date" id="startDate"><input type="date" id="endDate"><button class="btn" onclick="atualizar()">Atualizar Dados</button></div></div>
<div class="kpi-grid">
<div class="kpi-card"><span class="kpi-label">Impressões</span><span class="kpi-value" id="impressions">0</span></div>
<div class="kpi-card"><span class="kpi-label">Cliques</span><span class="kpi-value" id="clicks">0</span></div>
<div class="kpi-card"><span class="kpi-label">Alcance</span><span class="kpi-value" id="reach">0</span></div>
<div class="kpi-card"><span class="kpi-label">Compras</span><span class="kpi-value" id="purchases">0</span></div>
<div class="kpi-card"><span class="kpi-label">Gasto</span><span class="kpi-value" id="spend">R$ 0</span></div>
<div class="kpi-card"><span class="kpi-label">CPA</span><span class="kpi-value" id="cpa">R$ 0</span></div>
<div class="kpi-card"><span class="kpi-label">CTR</span><span class="kpi-value" id="ctr">0%</span></div>
<div class="kpi-card"><span class="kpi-label">ROAS</span><span class="kpi-value" id="roas">0</span></div>
</div>
<div class="charts-grid">
<div class="chart-card"><h2>Impressões e Cliques</h2><canvas id="chart1"></canvas></div>
<div class="chart-card"><h2>Gastos por Dia</h2><canvas id="chart2"></canvas></div>
<div class="chart-card full-width"><h2>Conversões</h2><canvas id="chart3"></canvas></div>
</div>
<div class="info" id="info">Selecione período e clique em "Atualizar Dados"</div>
<div class="error" id="error" style="display:none"></div></div>
<script>let c1,c2,c3;async function load(){try{var r=await fetch('/api/data');var d=await r.json();if(d.status==='success'&&d.data&&d.data.length){var kpis=d.data.reduce((a,b)=>({im:a.im+parseInt(b.impressions||0),cl:a.cl+parseInt(b.clicks||0),re:a.re+parseInt(b.reach||0),pu:a.pu+parseInt(b.website_purchases||0),sp:a.sp+parseFloat(b.spend||0)}),{im:0,cl:0,re:0,pu:0,sp:0});document.getElementById('impressions').innerText=kpis.im.toLocaleString();document.getElementById('clicks').innerText=kpis.cl.toLocaleString();document.getElementById('reach').innerText=kpis.re.toLocaleString();document.getElementById('purchases').innerText=kpis.pu.toLocaleString();document.getElementById('spend').innerText='R$ '+kpis.sp.toLocaleString();document.getElementById('cpa').innerText='R$ '+(kpis.pu?Math.round(kpis.sp/kpis.pu):0).toString();document.getElementById('ctr').innerText=(kpis.im?(kpis.cl/kpis.im*100).toFixed(2):0)+'%';document.getElementById('roas').innerText=kpis.sp?'2.0':'0';document.getElementById('info').style.display='none';updateCharts(d.data)}else document.getElementById('info').style.display='block'}catch(e){showError('Erro: '+e.message)}}function showError(msg){document.getElementById('error').innerText=msg;document.getElementById('error').style.display='block'}function updateCharts(d){var sd=[...d].sort((a,b)=>new Date(a.date_start)-new Date(b.date_start));var labels=sd.map(x=>new Date(x.date_start).toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'}));var imp=sd.map(x=>parseInt(x.impressions||0));var cl=sd.map(x=>parseInt(x.clicks||0));var sp=sd.map(x=>parseFloat(x.spend||0));var atc=sd.map(x=>parseInt(x.add_to_cart||0));var chk=sd.map(x=>parseInt(x.initiate_checkout||0));var pur=sd.map(x=>parseInt(x.website_purchases||0));if(c1)c1.destroy();c1=new Chart(document.getElementById('chart1'),{type:'line',data:{labels:labels,datasets:[{label:'Impressões',data:imp,borderColor:'#FFD700',tension:0.4},{label:'Cliques',data:cl,borderColor:'#C5A028',tension:0.4}]}});if(c2)c2.destroy();c2=new Chart(document.getElementById('chart2'),{type:'bar',data:{labels:labels,datasets:[{label:'Gasto R$',data:sp,backgroundColor:'rgba(255,215,0,0.6)'}]}});if(c3)c3.destroy();c3=new Chart(document.getElementById('chart3'),{type:'bar',data:{labels:labels,datasets:[{label:'Add to Cart',data:atc,backgroundColor:'rgba(197,160,40,0.6)'},{label:'Checkout',data:chk,backgroundColor:'rgba(255,215,0,0.6)'},{label:'Compras',data:pur,backgroundColor:'rgba(255,215,0,0.8)'}]}})}async function atualizar(){var s=document.getElementById('startDate').value;var e=document.getElementById('endDate').value;if(!s||!e)return alert('Selecione as datas!');document.getElementById('info').innerText='Atualizando...';document.getElementById('info').style.display='block';var res=await fetch('/api/update?start_date='+s+'&end_date='+e,{method:'POST'});var data=await res.json();if(data.status==='error'){showError(data.message);return}await load()}load()</script></body></html>'''

@app.route('/')
def index():
    return DASHBOARD_HTML, 200, {'Content-Type': 'text/html'}

@app.route('/api/data')
def get_data():
    return jsonify(load_json())

@app.route('/api/config')
def get_config():
    cfg = get_config()
    return jsonify({'configured': bool(cfg['facebook']['access_token'])})

@app.route('/api/update', methods=['POST'])
def update():
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    data, err = fetch_data(start, end)
    if err:
        return jsonify({'status': 'error', 'message': err})
    if not data:
        return jsonify({'status': 'error', 'message': 'Nenhum dado'})
    return jsonify({'status': 'success', 'message': f'{len(data)} registros!'})

def handler(request):
    return app