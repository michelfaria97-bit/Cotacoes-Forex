# app.py — COTAÇÕES + NOTÍCIAS AO VIVO (VERSÃO FINAL COM TODAS AS CORREÇÕES)
import streamlit as st
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
from deep_translator import GoogleTranslator
import json
import os

st.set_page_config(
    page_title="Cotações + Notícias ao Vivo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="Chart"
)

# ====================== CSS + SCROLL SUAVE ======================
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .sidebar .sidebar-content { background-color: #161b22; padding-top: 1rem; }
    .news-container { 
        position: relative; 
        overflow: hidden; 
        height: 85vh; 
        margin-top: 10px;
    }
    .news-list { 
        animation: scroll 140s linear infinite;
    }
    @keyframes scroll {
        0%   { transform: translateY(0); }
        100% { transform: translateY(-50%); }
    }
    .news-item {
        padding: 16px 12px;
        border-bottom: 1px solid #30363d;
        transition: all 0.2s;
    }
    .news-item:hover { background:#21262d; padding-left:18px; }
    .news-title a { color:#58a6ff; text-decoration:none; font-weight:600; font-size:15px; line-height:1.45; display:block; }
    .news-title a:hover { color:#79c0ff; text-decoration:underline; }
    .news-meta { font-size:12px; color:#8b949e; margin-top:6px; }
    .news-duplicate { opacity: 0; pointer-events: none; }
    .footer-text { text-align:center; color:#666; font-size:0.8em; margin-top:15px; }
</style>
""", unsafe_allow_html=True)

# ====================== CACHE DE NOTÍCIAS VISTAS ======================
CACHE_FILE = ".streamlit/noticias_vistas.json"
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit", exist_ok=True)

def carregar_vistas():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def salvar_vistas(vistas):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(vistas), f, ensure_ascii=False)
    except:
        pass

vistas = carregar_vistas()

# ====================== ATIVOS ======================
assets = {
    'Forex': {
        'eur-usd': 'Euro/US Dollar', 'gbp-usd': 'British Pound/US Dollar', 'usd-jpy': 'US Dollar/Japanese Yen',
        'aud-usd': 'Australian Dollar/US Dollar', 'usd-cad': 'US Dollar/Canadian Dollar', 'usd-chf': 'US Dollar/Swiss Franc',
        'eur-gbp': 'Euro/British Pound', 'eur-aud': 'Euro/Australian Dollar', 'eur-jpy': 'Euro/Japanese Yen',
        'eur-chf': 'Euro/Swiss Franc', 'eur-nzd': 'Euro/New Zealand Dollar', 'gbp-jpy': 'British Pound/Japanese Yen',
        'gbp-cad': 'British Pound/Canadian Dollar', 'gbp-aud': 'British Pound/Australian Dollar', 'gbp-nzd': 'British Pound/New Zealand Dollar',
        'aud-jpy': 'Australian Dollar/Japanese Yen', 'aud-nzd': 'Australian Dollar/New Zealand Dollar', 'aud-chf': 'Australian Dollar/Swiss Franc',
        'nzd-usd': 'New Zealand Dollar/US Dollar', 'nzd-jpy': 'New Zealand Dollar/Japanese Yen', 'nzd-cad': 'New Zealand Dollar/Canadian Dollar',
        'nzd-chf': 'New Zealand Dollar/Swiss Franc', 'eur-cad': 'Euro/Canadian Dollar', 'gbp-eur': 'British Pound/Euro',
        'gbp-chf': 'British Pound/Swiss Franc', 'aud-eur': 'Australian Dollar/Euro', 'aud-gbp': 'Australian Dollar/British Pound',
        'aud-cad': 'Australian Dollar/Canadian Dollar', 'nzd-aud': 'New Zealand Dollar/Australian Dollar', 'nzd-eur': 'New Zealand Dollar/Euro',
        'nzd-gbp': 'New Zealand Dollar/British Pound', 'cad-aud': 'Canadian Dollar/Australian Dollar', 'usd-aud': 'US Dollar/Australian Dollar',
        'jpy-eur': 'Japanese Yen/Euro', 'chf-aud': 'Swiss Franc/Australian Dollar', 'chf-eur': 'Swiss Franc/Euro',
        'usd-nzd': 'US Dollar/New Zealand Dollar', 'jpy-usd': 'Japanese Yen/US Dollar', 'jpy-gbp': 'Japanese Yen/British Pound',
        'jpy-cad': 'Canadian Dollar/Japanese Yen', 'jpy-chf': 'Japanese Yen/Swiss Franc', 'jpy-nzd': 'Japanese Yen/New Zealand Dollar',
        'cad-usd': 'Canadian Dollar/US Dollar', 'cad-jpy': 'Canadian Dollar/Japanese Yen', 'cad-gbp': 'Canadian Dollar/British Pound',
        'cad-chf': 'Swiss Franc/Canadian Dollar', 'cad-nzd': 'New Zealand Dollar/Canadian Dollar', 'chf-usd': 'Swiss Franc/US Dollar',
        'chf-jpy': 'Swiss Franc/Japanese Yen', 'chf-gbp': 'British Pound/Swiss Franc', 'chf-cad': 'Canadian Dollar/Swiss Franc',
        'chf-nzd': 'New Zealand Dollar/Swiss Franc', 'cad-eur': 'Canadian Dollar/Euro', 'usd-eur': 'US Dollar/Euro', 'usd-gbp': 'US Dollar/British Pound',
        'jpy-aud': 'Australian Dollar/Japanese Yen', 'brl-cad': 'Canadian Dollar/Brazilian Real', 'cny-usd': 'US Dollar/Chinese Yuan',
        'cny-nzd': 'New Zealand Dollar/Chinese Yuan', 'cny-jpy': 'Japanese Yen/Chinese Yuan', 'cny-gbp': 'British Pound/Chinese Yuan',
        'cny-chf': 'Swiss Franc/Chinese Yuan', 'cny-aud': 'Australian Dollar/Chinese Yuan', 'cny-eur': 'Euro/Chinese Yuan',
        'brl-usd': 'US Dollar/Brazilian Real', 'brl-jpy': 'Japanese Yen/Brazilian Real', 'brl-gbp': 'British Pound/Brazilian Real',
        'brl-nzd': 'New Zealand Dollar/Brazilian Real', 'brl-aud': 'Australian Dollar/Brazilian Real', 'brl-eur': 'Euro/Brazilian Real'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30',
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite', 'japan-225-futures': 'Nikkei 225',
                      'ftse-china-25': 'FTSE China', 'india-50-futures': 'Nifty 50', 'australia-200-futures': 'ASX 200'},
    'Europa': {'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40',
               'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35', 'italy-40-futures': 'FTSE MIB', 'euro-stoxx-600': 'STOXX 600'},
    'Commodities': {'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper',
                    'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'},
    'Crypto': {'btc-usd': 'Bitcoin', 'eth-usd': 'Ethereum'},
    'Mag 7': {
        'google-inc-c': 'GOOG', 'microsoft-corp': 'MSFT', 'amazon-com-inc': 'AMZN',
        'apple-computer-inc': 'AAPL', 'facebook-inc': 'META', 'nvidia-corp': 'NVDA', 'tesla-motors': 'TSLA'
    }
}

# ====================== FUNÇÕES DE COTAÇÃO ======================
def clean_price(p):
    if not p or p in ['N/D', '-']: return 'N/D'
    p = p.replace(',', '.')
    parts = p.split('.')
    if len(parts) > 2:
        p = ''.join(parts[:-1]) + '.' + parts[-1]
    try: return str(float(p))
    except: return p

def get_single_forex(symbol, _):
    url = f'https://br.investing.com/currencies/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.find('div', {'data-test': 'instrument-price-last'})
        change = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price_txt = price.text.strip() if price else 'N/D'
        change_txt = change.text.strip() if change else '0%'
        num = re.sub(r'[^\d.-]', '', change_txt.replace(',', '.'))
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': clean_price(price_txt), '1d Change (%)': round(float(num or 0), 2)}
    except:
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': 'Erro', '1d Change (%)': 0.0}

def get_single_non_forex(category, symbol, name):
    if symbol == 'usdollar':
        url = 'https://br.investing.com/indices/usdollar'
    elif symbol in ['btc-usd', 'eth-usd']:
        url = f'https://br.investing.com/crypto/{symbol.split("-")[0]}/{symbol}'
    elif '-futures' in symbol:
        url = f'https://br.investing.com/indices/{symbol}'
    elif category == 'Commodities':
        url = f'https://br.investing.com/commodities/{symbol}'
    elif category == 'Mag 7':
        url = f'https://br.investing.com/equities/{symbol}'
    else:
        url = f'https://br.investing.com/indices/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        if not price_elem or not change_elem:
            return {'Symbol': name, 'Last Price': 'N/D', '1d Change (%)': 0.0}
        price = price_elem.text.strip()
        change_text = change_elem.text.strip()
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        return {'Symbol': name, 'Last Price': clean_price(price), '1d Change (%)': round(float(num or 0), 2)}
    except:
        return {'Symbol': name, 'Last Price': 'Erro', '1d Change (%)': 0.0}

def agrupar_forex(data):
    grupos = { 
        'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
        'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [],
        'Franco Suíço': [], 'Real Brasileiro': [], 'Yuan Chinês': []
    }
    base_map = { 
        'USD': 'Dólar Americano', 'EUR': 'Euro', 'GBP': 'Libra Esterlina', 'JPY': 'Iene Japonês',
        'AUD': 'Dólar Australiano', 'NZD': 'Dólar Neozelandês', 'CAD': 'Dólar Canadense',
        'CHF': 'Franco Suíço', 'BRL': 'Real Brasileiro', 'CNY': 'Yuan Chinês' 
    }
    for item in data:
        if '/' in item['Symbol']:
            base = item['Symbol'].split('/')[0]
            grupo = base_map.get(base)
            if grupo:
                grupos[grupo].append(item)
    return {k: v for k, v in grupos.items() if v}

def grafico_forca(data):
    forex = [i for i in data if '/' in i['Symbol']]
    if not forex: return None
    df = pd.DataFrame(forex)
    df['1d Change (%)'] = pd.to_numeric(df['1d Change (%)'], errors='coerce')
    df['Base'] = df['Symbol'].str.split('/').str[0]
    media = df.groupby('Base')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
    fig = px.bar(media.reset_index(), x='Base', y='1d Change (%)', color='1d Change (%)',
                 color_continuous_scale=['red','orange','lightgray','lightgreen','green'],
                 text='1d Change (%)', title='Força Relativa das Moedas (1 dia)')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False, xaxis={'categoryorder': 'total descending'})
    return fig

def estilizar(df):
    return df.style.format({'1d Change (%)': '{:.2f}%'}) \
        .map(lambda x: f"color: {'#00ff00' if x>0 else '#ff4444' if x<0 else '#cccccc'}; font-weight: bold", subset=['1d Change (%)'])

@st.cache_data(ttl=55)
def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = []
        for symbol, name in assets['Forex'].items():
            futures.append(executor.submit(get_single_forex, symbol, name))
        for cat in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto', 'Mag 7']:
            for symbol, name in assets[cat].items():
                futures.append(executor.submit(get_single_non_forex, cat, symbol, name))
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except:
                pass
    seen = set()
    unique = [r for r in results if r['Symbol'] not in seen and not seen.add(r['Symbol'])]
    return unique

# ====================== NOTÍCIAS ======================
def carregar_noticias_frescas():
    global vistas
    novas = []
    feeds = [
        "https://br.investing.com/rss/market_overview_Technical.rss",
        "https://br.investing.com/rss/stock.rss",
        "https://bmcnews.com.br/feed/",
        "https://www.bloomberglinea.com.br/arc/outboundfeeds/rss.xml",
        "https://einvestidor.estadao.com.br/feed/",
        "https://www.infomoney.com.br/feed/",
        "https://investnews.com.br/feed/",
        "https://br.advfn.com/jornal/rss",
        "https://www.infomoney.com.br/mercados/feed/",
        "https://borainvestir.b3.com.br/noticias/mercado/feed/",
        "https://www.moneytimes.com.br/mercados/feed/",
        "https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/cambio",
        "https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/focus",
        "https://www.bomdiamercado.com.br/feed/",
        "https://br.investing.com/rss/news.rss",
        "https://cms.zerohedge.com/fullrss2.xml",
        "https://valor.globo.com/rss/valor",
        "https://www.seudinheiro.com/feed/",
        "https://feeds.feedburner.com/barchartnews"
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.link.strip()
                if link in vistas: continue
                titulo = entry.title.strip()
                if any(x in url for x in ["zerohedge", "barchart", "investing.com/rss/news"]):
                    try:
                        titulo = GoogleTranslator(source='en', target='pt').translate(titulo)
                    except: pass
                data_raw = entry.get('published') or entry.get('updated') or ""
                try:
                    data = datetime.strptime(data_raw[:19], "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
                except:
                    data = "Agora"
                fonte = feed.feed.get('title', 'Fonte').split('-')[0].strip()
                novas.append({'titulo': titulo, 'link': link, 'fonte': fonte, 'data': data})
                vistas.add(link)
        except:
            continue
    salvar_vistas(vistas)
    novas.sort(key=lambda x: x.get('ts', time.time()), reverse=True)
    return novas[:90]

# ====================== PLACEHOLDERS + LOOP ======================
sidebar_placeholder = st.sidebar.empty()
main_placeholder    = st.empty()

ultimas_noticias = []
proxima_atualizacao_noticias = 0
proxima_atualizacao_cotacoes = 0

while True:
    agora = time.time()

    if agora >= proxima_atualizacao_noticias:
        ultimas_noticias = carregar_noticias_frescas()
        proxima_atualizacao_noticias = agora + 60

    if agora >= proxima_atualizacao_cotacoes:
        dados_cotacoes = fetch_all()
        proxima_atualizacao_cotacoes = agora + 55
    # ====================== RENDERIZAÇÃO ======================
    with sidebar_placeholder.container():
        st.markdown("### 🔄 Atualização Automática")
        st.write(f"**Cotação atualizada:** {datetime.now().strftime('%H:%M:%S')}")

        st.markdown("### 💱 Força das Moedas")
        fig = grafico_forca(dados_cotacoes)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📊 Tabelas por Grupo")
        st.write("Agrupamento automático baseado nas moedas base.")
        grupos = agrupar_forex(dados_cotacoes)

        for nome_grupo, itens in grupos.items():
            st.markdown(f"#### {nome_grupo}")
            df = pd.DataFrame(itens)
            st.dataframe(estilizar(df), use_container_width=True)

    # ====================== NOTÍCIAS ======================
    with main_placeholder.container():
        st.markdown("## 📰 Notícias em Tempo Real")
        st.markdown("Fluxo contínuo das últimas notícias de mercados, economia e ativos globais.")

        st.markdown('<div class="news-container"><div class="news-list">', unsafe_allow_html=True)

        for i, n in enumerate(ultimas_noticias):
            dup = "news-duplicate" if i >= len(ultimas_noticias) // 2 else ""
            st.markdown(f"""
            <div class="news-item {dup}">
                <div class="news-title"><a href="{n['link']}" target="_blank">{n['titulo']}</a></div>
                <div class="news-meta">{n['fonte']} — {n['data']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)
        st.markdown('<p class="footer-text">Atualiza automaticamente • Última atualização: ' +
                    datetime.now().strftime("%H:%M:%S") + '</p>', unsafe_allow_html=True)

    time.sleep(2)
