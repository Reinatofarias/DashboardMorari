# MORARI PROJECT DASHBOARD

Dashboard profissional para análise de campanhas do Meta Ads (Facebook/Instagram) com design darkmode em preto e dourado.

## Funcionalidades

- ✅ **KPIs Principais**: Impressões, Cliques, Alcance, Finalização de Compras, CPA, Custo por Resultado, Valor Usado, CTR, Connect Rate
- ✅ **Gráficos Interativos**: Tendência de impressões/cliques, Gastos por dia, CTR por dia, Conversões
- ✅ **Tabela Detalhada** com dados diários formatados
- ✅ **Seletor de Período** - Consulte dados específicos via API do Meta
- ✅ **Botão Atualizar Dados** - Puxa dados reais da API diretamente no dashboard
- ✅ **Design Responsivo** - Adapta-se a qualquer tamanho de tela
- ✅ **Darkmode Elegante** - Preto com detalhes em dourado

## Tecnologias Utilizadas

- **Backend**: Python (Flask)
- **Frontend**: HTML5, CSS3, JavaScript (Chart.js)
- **API**: Meta Ads Graph API v18.0
- **Deploy**: Vercel (Python Runtime)

## Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/morari-project-dashboard.git
   cd morari-project-dashboard
   ```

2. Instale as dependências:
   ```bash
   pip install -r scripts/requirements.txt
   ```

3. Configure suas credenciais do Meta Ads:
   - Copie `config/config.example.json` para `config/config.json`
   - Preencha com seus dados reais (App ID, App Secret, Access Token, Ad Account ID)

4. Execute o servidor:
   ```bash
   cd scripts
   python server.py
   ```

5. Acesse no navegador:
   - http://localhost:5000

## Deploy no Vercel

1. Faça push do projeto para o GitHub
2. No [Vercel](https://vercel.com), importe o repositório
3. Configure as variáveis de ambiente (ou use o arquivo config.json)
4. Deploy automático!

## Estrutura do Projeto

```
PowerBI - META/
├── config/
│   ├── config.json (ignorado no git)
│   └── config.example.json
├── scripts/
│   ├── server.py (Flask backend)
│   ├── facebook_ads_extractor.py (Extrator da API)
│   └── requirements.txt
├── dashboard/
│   └── dashboard/
│       ├── index.html
│       ├── styles.css
│       └── dashboard.js
├── data/ (ignorado no git)
└── README.md
```

## Observações

- O token de acesso do Meta Ads expira após 2 horas. Gere um novo em: https://developers.facebook.com/tools/explorer/
- Certifique-se de não comitar o arquivo `config.json` com dados reais
- O projeto foi desenvolvido para ser executado localmente ou em servidor Python (Vercel)

## Licença

MIT
