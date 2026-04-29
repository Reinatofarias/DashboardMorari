# MORARI PROJECT DASHBOARD

Dashboard para analise de campanhas do Meta Ads, com backend Flask, frontend HTML/CSS/JavaScript e deploy preparado para Vercel.

## Funcionalidades

- KPIs principais: Impressoes, Cliques, Alcance, Finalizacao de Compras, CPA, Custo por Resultado, Valor Usado, CTR e Connect Rate.
- Graficos interativos com Chart.js.
- Tabela diaria com os dados retornados pela API.
- Seletor de periodo para consultar a Meta Ads API.
- Atualizacao direta pelo dashboard.
- Layout responsivo em dark mode.

## Como rodar localmente

1. Instale as dependencias:

```bash
pip install -r requirements.txt
```

2. Configure `config/config.json` com suas credenciais locais:

```json
{
  "facebook": {
    "app_id": "SEU_APP_ID",
    "app_secret": "SEU_APP_SECRET",
    "access_token": "SEU_ACCESS_TOKEN",
    "ad_account_id": "SEU_AD_ACCOUNT_ID"
  }
}
```

3. Inicie o servidor:

```bash
python scripts/server.py
```

4. Acesse:

```text
http://localhost:5000
```

## Deploy no Vercel

No Vercel, configure estas variaveis de ambiente no projeto:

```text
FB_ACCESS_TOKEN=seu_token_da_meta
FB_AD_ACCOUNT_ID=id_da_conta_sem_act_
META_GRAPH_VERSION=v18.0
```

`META_GRAPH_VERSION` e opcional. O dashboard usa `v18.0` por padrao.

Depois, faca push para o GitHub e deixe o Vercel executar o deploy com o `vercel.json` existente.

## Rotas

- `/` - Dashboard principal.
- `/config-token` - Tela auxiliar para token local.
- `/api/data` - Dados locais/cacheados.
- `/api/update?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` - Consulta a API da Meta e retorna os dados atualizados.
- `/api/config` - Status de configuracao.

## Observacoes

- Nao versionar `config/config.json` com token real.
- Em producao, use variaveis de ambiente no Vercel.
- O arquivo `data/facebook_ads_latest.json` e apenas cache local; no Vercel a atualizacao retorna os dados diretamente para o frontend.
