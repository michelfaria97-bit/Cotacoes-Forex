# app.py — VERSÃO FINAL PERFEITA: 3 COLUNAS + NOTÍCIAS NO TOPO DA SIDEBAR
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

# ====================== CONFIGURAÇÃO ======================
st.set_page_config(
    page_title="Cotações + Notícias ao Vivo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="Chart"
)

# ====================== ESTILO ======================
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .sidebar .sidebar-content { background-color: #161b22; }
    .news-item {
        padding: 14px;
        border-bottom: 1px solid #30363d;
        transition: all 0.2s;
    }
    .news-item:hover { background-color: #21262d; padding-left: 18px; }
    .news-title a { 
        color: #58a6ff; 
        text-decoration: none; 
        font-weight: 600; 
        font-size: 15px; 
        line-height: 1.4;
    }
    .news-title a:hover { color: #79c0ff; text-decoration: underline; }
    .news-meta { font-size: 12px; color: #8b949e; margin-top: 6px; }
    .stDataFrame { width: 100% !important; }
    [data-testid="column"] { padding: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ====================== CACHE DE NOTÍCIAS ======================
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

# ====================== ATIVOS (completo) ======================
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
        'jpy-cad': 'Japanese Yen/Canadian Dollar', 'jpy-chf': 'Japanese Yen/Swiss Franc', 'jpy-nzd': 'Japanese Yen/New Zealand Dollar',
        'cad-usd': 'Canadian Dollar/US Dollar', 'cad-jpy': 'Canadian Dollar/Japanese Yen', 'cad-gbp': 'Canadian Dollar/British Pound',
        'cad-chf': 'Canadian Dollar/Swiss Franc', 'cad-nzd': 'Canadian Dollar/New Zealand Dollar', 'chf-usd': 'Swiss Franc/US Dollar',
        'chf-jpy': 'Swiss Franc/Japanese Yen', 'chf-gbp': 'Swiss Franc/British Pound', 'chf-cad': 'Swiss Franc/Canadian Dollar',
        'chf-nzd': 'Swiss Franc/New Zealand Dollar', 'cad-eur': 'Canadian Dollar/Euro', 'usd-eur': 'US Dollar/Euro', 'usd-gbp': 'US Dollar/British Pound',
        'jpy-aud': 'Japanese Yen/Australian Dollar', 'brl-cad': 'Brazilian Real/Canadian Dollar', 'cny-usd': 'Chinese Yuan/US Dollar',
        'cny-nzd': 'Chinese Yuan/New Zealand Dollar', 'cny-jpy': 'Chinese Yuan/Japanese Yen', 'cny-gbp': 'Chinese Yuan/British Pound',
        'cny-chf': 'Chinese Yuan/Swiss Franc', 'cny-aud': 'Chinese Yuan/Australian Dollar', 'cny-eur': 'Chinese Yuan/Euro',
        'brl-usd': 'Brazilian Real/US Dollar', 'brl-jpy': 'Brazilian Real/Japanese Yen', 'brl-gbp': 'Brazilian Real/British Pound',
        'brl-nzd': 'Brazilian Real/New Zealand Dollar', 'brl-aud': 'Brazilian Real/Australian Dollar', 'brl-eur': 'Brazilian Real/Euro'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30',
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite', 'japan-225-futures': 'Nikkei 225',
                 'ftse-china-25': 'FTSE China', 'india-50-futures': 'Nifty 50', 'australia-200-futures': 'ASX 200'},
    'Europa': {'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40',
               'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35', 'italy-40-futures': 'FTSE MIB', 'euro-stoxx-600': 'STOXX 600'},
    'Commodities': {'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper',
                    'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'},
    'Crypto': {'btc-usd': 'Bitcoin', 'eth-usd': 'Ethereum'}
}

# ====================== FUNÇÕES (todas funcionando) ======================
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
        url = f'https://br.investing.com/crypto/{symbol.split("-")[0]}/{symbol.split("-")[1]}'
    elif category in ['USA', 'Asia/Pacifico', 'Europa']:
        url = f'https://br.investing.com/indices/{symbol}'
    else:
        url = f'https://br.investing.com/commodities/{symbol}'
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.find('div', {'data-test': 'instrument-price-last'})
        change = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        if not price or not change:
            return {'Symbol': name, 'Last Price': 'N/D', '1d Change (%)': 0.0}
        price_txt = price.text.strip()
        change_txt = change.text.strip()
        num = re.sub(r'[d.-]', '', change_txt.replace(',', '.'))
        return {'Symbol': name, 'Last Price': clean_price(price_txt), '1d Change (%)': round(float(num or 0), 2)}
    except:
        return {'Symbol': name, 'Last Price': 'Erro', '1d Change (%)': 0.0}

def agrupar_forex(data):
    grupos = { 'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
        'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [],
        'Franco Suíço': [], 'Real Brasileiro': [], 'Yuan Chinês': [] }
    base_map = { 'USD': 'Dólar Americano', 'EUR': 'Euro', 'GBP': 'Libra Esterlina', 'JPY': 'Iene Japonês',
        'AUD': 'Dólar Australiano', 'NZD': 'Dólar Neozelandês', 'CAD': 'Dólar Canadense',
        'CHF': 'Franco Suíço', 'BRL': 'Real Brasileiro', 'CNY': 'Yuan Chinês' }
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
        .map(lambda x: f"color: {'green' if x>0 else 'red' if x<0 else 'gray'}; font-weight: bold", subset=['1d Change (%)'])

@st.cache_data(ttl=55)
def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = []
        for symbol, name in assets['Forex'].items():
            futures.append(executor.submit(get_single_forex, symbol, name))
        for cat in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']:
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

# ====================== NOTÍCIAS (MAIS NOVAS NO TOPO) ======================
@st.cache_data(ttl=60, show_spinner=False)
def carregar_noticias():
    global vistas
    novas = []
    feeds = [
        "https://www.infomoney.com.br/feed/",
        "https://www.moneytimes.com.br/mercados/feed/",
        "https://valor.globo.com/rss",
        "https://www.seudinheiro.com/feed/",
        "https://br.investing.com/rss/news.rss",
        "https://einvestidor.estadao.com.br/feed/",
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:12]:
                link = entry.link.strip()
                if link in vistas: continue
                titulo = entry.title.strip()
                try:
                    if any(kw in titulo.lower() for kw in ["fed", "cpi", "powell", "ecb"]):
                        titulo = GoogleTranslator(source='en', target='pt').translate(titulo)
                except: pass
                data = entry.get('published', 'Agora')[:16].replace('T', ' ')
                fonte = feed.feed.get('title', 'Fonte').split('-')[0].strip()
                novas.append({'titulo': titulo, 'link': link, 'fonte': fonte, 'data': data})
                vistas.add(link)
        except: continue
    salvar_vistas(vistas)
    # ORDENA POR DATA (MAIS NOVA PRIMEIRO)
    novas.sort(key=lambda x: x['data'], reverse=True)
    return novas[:20]

# ====================== LOOP PRINCIPAL ======================
placeholder = st.empty()
tz_brasil = timedelta(hours=-3)

while True:
    inicio = time.time()

    # === SIDEBAR COM NOTÍCIAS (MAIS NOVAS NO TOPO!) ===
    noticias = carregar_noticias()
    with st.sidebar:
        st.markdown("<h2 style='color:#58a6ff;text-align:center;'>Notícias ao Vivo</h2>", unsafe_allow_html=True)
        if not noticias:
            st.info("Carregando...")
        else:
            st.success(f"{len(noticias)} novas")
            for n in noticias:  # já vem ordenado!
                st.markdown(f"""
                <div class="news-item">
                    <div class="news-title"><a href="{n['link']}" target="_blank">{n['titulo']}</a></div>
                    <div class="news-meta">{n['fonte']} • {n['data']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.caption("Atualiza a cada minuto")

    # === CONTEÚDO PRINCIPAL (3 COLUNAS!) ===
    with placeholder.container():
        dados = fetch_all()
        agora = datetime.now() + tz_brasil

        st.markdown(f"<h1 style='text-align:center;color:#58a6ff;'>COTAÇÕES AO VIVO</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:#8b949e;font-size:18px;'>Atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')} • {time.time()-inicio:.1f}s</p>", unsafe_allow_html=True)
        st.markdown("---")

        # Gráfico
        fig = grafico_forca(dados)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

        # Forex — AGORA COM 3 COLUNAS
        st.markdown("<h2 style='color:#79c0ff;'>Forex - Pares de Moedas</h2>", unsafe_allow_html=True)
        forex_data = [x for x in dados if '/' in x['Symbol']]
        grupos = agrupar_forex(forex_data)
        cols = st.columns(3)  # MUDOU DE 4 PARA 3!
        ordem = ['Dólar Americano', 'Euro', 'Libra Esterlina', 'Iene Japonês', 'Dólar Australiano', 'Dólar Neozelandês', 'Dólar Canadense', 'Franco Suíço', 'Real Brasileiro', 'Yuan Chinês']
        i = 0
        for titulo in ordem:
            if titulo in grupos and grupos[titulo]:
                with cols[i % 3]:  # 3 colunas!
                    df = pd.DataFrame(grupos[titulo])[ ['Symbol','Last Price','1d Change (%)'] ].set_index('Symbol')
                    st.subheader(titulo)
                    st.dataframe(estilizar(df), use_container_width=True)
                i += 1
        st.markdown("---")

        # Outros ativos — TAMBÉM COM 3 COLUNAS
        st.markdown("<h2 style='color:#79c0ff;'>Outros Ativos</h2>", unsafe_allow_html=True)
        outros = [x for x in dados if '/' not in x['Symbol']]
        cols2 = st.columns(3)  # 3 colunas!
        cats = {'USA':[], 'Asia/Pacifico':[], 'Europa':[], 'Commodities':[], 'Crypto':[]}
        for item in outros:
            for c, itens in assets.items():
                if c == 'Forex': continue
                if item['Symbol'] in itens.values():
                    cats[c].append(item)
                    break
        i = 0
        for cat in ['USA','Asia/Pacifico','Europa','Commodities','Crypto']:
            if cats[cat]:
                with cols2[i % 3]:
                    df = pd.DataFrame(cats[cat])[ ['Symbol','Last Price','1d Change (%)'] ].set_index('Symbol')
                    st.subheader(cat.replace('/', ' / '))
                    st.dataframe(estilizar(df), use_container_width=True)
                i += 1

        # Download
        csv = pd.DataFrame(dados).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar todos os dados (CSV)",
            data=csv,
            file_name=f"cotacoes_{agora.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key=f"dl_{int(time.time())}"
        )

    time.sleep(60)
