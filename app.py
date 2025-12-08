import streamlit as st
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Cotações ao Vivo", layout="wide", initial_sidebar_state="collapsed", page_icon="Chart")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    h1, h2 { color: #58a6ff; text-align: center; }
    .stDataFrame { width: 100% !important; }
    [data-testid="column"] { padding: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ====================== ATIVOS ======================
assets = {
    'Forex': {
        'eur-usd': 'EUR/USD', 'gbp-usd': 'GBP/USD', 'usd-jpy': 'USD/JPY',
        'aud-usd': 'AUD/USD', 'usd-cad': 'USD/CAD', 'usd-chf': 'USD/CHF',
        'eur-gbp': 'EUR/GBP', 'eur-aud': 'EUR/AUD', 'eur-jpy': 'EUR/JPY',
        'eur-chf': 'EUR/CHF', 'eur-nzd': 'EUR/NZD', 'gbp-jpy': 'GBP/JPY',
        'gbp-cad': 'GBP/CAD', 'gbp-aud': 'GBP/AUD', 'gbp-nzd': 'GBP/NZD',
        'aud-jpy': 'AUD/JPY', 'aud-nzd': 'AUD/NZD', 'aud-chf': 'AUD/CHF',
        'nzd-usd': 'NZD/USD', 'nzd-jpy': 'NZD/JPY', 'nzd-cad': 'NZD/CAD',
        'nzd-chf': 'NZD/CHF', 'eur-cad': 'EUR/CAD', 'gbp-eur': 'GBP/EUR',
        'gbp-chf': 'GBP/CHF', 'aud-eur': 'AUD/EUR', 'aud-gbp': 'AUD/GBP',
        'aud-cad': 'AUD/CAD', 'nzd-aud': 'NZD/AUD', 'nzd-eur': 'NZD/EUR',
        'nzd-gbp': 'NZD/GBP', 'cad-aud': 'CAD/AUD', 'usd-aud': 'USD/AUD',
        'jpy-eur': 'JPY/EUR', 'chf-aud': 'CHF/AUD', 'chf-eur': 'CHF/EUR',
        'usd-nzd': 'USD/NZD', 'jpy-usd': 'JPY/USD', 'jpy-gbp': 'JPY/GBP',
        'jpy-cad': 'JPY/CAD', 'jpy-chf': 'JPY/CHF', 'jpy-nzd': 'JPY/NZD',
        'cad-usd': 'CAD/USD', 'cad-jpy': 'CAD/JPY', 'cad-gbp': 'CAD/GBP',
        'cad-chf': 'CAD/CHF', 'cad-nzd': 'CAD/NZD', 'chf-usd': 'CHF/USD',
        'chf-jpy': 'CHF/JPY', 'chf-gbp': 'GBP/CHF', 'chf-cad': 'CHF/CAD',
        'chf-nzd': 'CHF/NZD', 'cad-eur': 'CAD/EUR', 'usd-eur': 'USD/EUR', 
        'usd-gbp': 'USD/GBP', 'jpy-aud': 'JPY/AUD', 'brl-usd': 'BRL/USD'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30',
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite', 
                      'japan-225-futures': 'Nikkei 225', 'ftse-china-25': 'FTSE China', 
                      'india-50-futures': 'Nifty 50', 'australia-200-futures': 'ASX 200'},
    'Europa': {'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40',
               'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35', 'italy-40-futures': 'FTSE MIB', 
               'euro-stoxx-600': 'STOXX 600'},
    'Commodities': {'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper',
                    'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'},
    'Crypto': {'bitcoin': 'Bitcoin', 'ethereum': 'Ethereum'},
    'Mag 7': {
        'google-inc-c': 'GOOG', 'microsoft-corp': 'MSFT', 'amazon-com-inc': 'AMZN',
        'apple-computer-inc': 'AAPL', 'facebook-inc': 'META', 'nvidia-corp': 'NVDA', 'tesla-motors': 'TSLA'
    }
}

# ====================== FUNÇÕES ======================
def clean_price(p):
    if not p or p in ['N/D', '-']: return 'N/D'
    p = p.replace(',', '.').replace(' ', '')
    try: return str(float(p))
    except: return p

def get_investing_data(url):
    """Pega dados via API interna do Investing (funciona em 2025)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://br.investing.com/'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Tenta data-test primeiro
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'}) or \
                    soup.find('div', class_=re.compile(r'text-5xl'))
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'}) or \
                     soup.find('span', class_=re.compile(r'text-positive-main|text-negative-main'))
        
        if not price_elem:
            return {'Last Price': 'N/D', '1d Change (%)': 0.0}
            
        price = price_elem.text.strip()
        change_text = change_elem.text.strip() if change_elem else '0%'
        
        # Extrai % da variação
        num = re.search(r'([+-]?\d+(?:[.,]\d+)?)', change_text.replace('%', ''))
        change_pct = float(num.group(1)) if num else 0.0
        
        return {'Last Price': clean_price(price), '1d Change (%)': round(change_pct, 2)}
    except:
        return {'Last Price': 'N/D', '1d Change (%)': 0.0}

def get_cotacao(symbol, category, name):
    if category == 'Forex':
        url = f'https://br.investing.com/currencies/{symbol}'
    elif symbol == 'usdollar':
        url = 'https://br.investing.com/indices/usdollar'
    elif symbol == 'bitcoin':
        url = 'https://br.investing.com/crypto/bitcoin'
    elif symbol == 'ethereum':
        url = 'https://br.investing.com/crypto/ethereum'
    elif '-futures' in symbol or category == 'USA':
        url = f'https://br.investing.com/indices/{symbol}'
    elif category == 'Commodities':
        url = f'https://br.investing.com/commodities/{symbol}'
    elif category == 'Mag 7':
        url = f'https://br.investing.com/equities/{symbol}'
    else:
        url = f'https://br.investing.com/indices/{symbol}'
    
    data = get_investing_data(url)
    return {'Symbol': name, 'Last Price': data['Last Price'], '1d Change (%)': data['1d Change (%)']}

@st.cache_data(ttl=30)
def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        # Forex
        for symbol, name in list(assets['Forex'].items())[:20]:  # Limita pra não travar
            futures.append(executor.submit(get_cotacao, symbol, 'Forex', name))
        
        # Outros
        for cat in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto', 'Mag 7']:
            for symbol, name in assets[cat].items():
                futures.append(executor.submit(get_cotacao, symbol, cat, name))
                
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except:
                pass
    return results

# ====================== DEMAIS FUNÇÕES (igual) ======================
def agrupar_forex(data):
    grupos = { 'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
               'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [],
               'Franco Suíço': [], 'Real Brasileiro': [], 'Yuan Chinês': [] }
    base_map = { 'USD': 'Dólar Americano', 'EUR': 'Euro', 'GBP': 'Libra Esterlina', 
                'JPY': 'Iene Japonês', 'AUD': 'Dólar Australiano', 'NZD': 'Dólar Neozelandês', 
                'CAD': 'Dólar Canadense', 'CHF': 'Franco Suíço', 'BRL': 'Real Brasileiro' }
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
                  text='1d Change (%)', title='Força Relativa das Moedas')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False)
    return fig

def estilizar(df):
    return df.style.format({'1d Change (%)': '{:.2f}%'}) \
        .map(lambda x: f"color: {'green' if x>0 else 'red' if x<0 else 'gray'}; font-weight: bold", 
             subset=['1d Change (%)'])

# ====================== LOOP PRINCIPAL ======================
placeholder = st.empty()
tz_brasil = timedelta(hours=-3)

while True:
    inicio = time.time()
    with placeholder.container():
        dados = fetch_all()
        agora = datetime.now() + tz_brasil
        
        st.markdown(f"<h1 style='text-align:center;color:#58a6ff;'>COTAÇÕES AO VIVO</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:#8b949e;font-size:18px;'>Atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')} • {time.time()-inicio:.1f}s</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        fig = grafico_forca(dados)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")
        
        # Forex
        st.markdown("<h2 style='color:#79c0ff;'>Forex - Pares de Moedas</h2>", unsafe_allow_html=True)
        forex_data = [x for x in dados if '/' in x['Symbol']]
        grupos = agrupar_forex(forex_data)
        cols = st.columns(3)
        ordem = ['Dólar Americano', 'Euro', 'Libra Esterlina', 'Iene Japonês', 'Dólar Australiano',
                 'Dólar Neozelandês', 'Dólar Canadense', 'Franco Suíço']
        i = 0
        for titulo in ordem:
            if titulo in grupos and grupos[titulo]:
                with cols[i % 3]:
                    df = pd.DataFrame(grupos[titulo])[['Symbol','Last Price','1d Change (%)']].set_index('Symbol')
                    st.subheader(titulo)
                    st.dataframe(estilizar(df), use_container_width=True)
                i += 1
        
        # Outros ativos
        st.markdown("---")
        st.markdown("<h2 style='color:#79c0ff;'>Outros Ativos</h2>", unsafe_allow_html=True)
        outros = [x for x in dados if '/' not in x['Symbol']]
        cols2 = st.columns(3)
        cats = {'USA':[], 'Mag 7':[], 'Asia/Pacifico':[], 'Europa':[], 'Commodities':[], 'Crypto':[]}
        for item in outros:
            for c, itens in assets.items():
                if c == 'Forex': continue
                if item['Symbol'] in itens.values():
                    cats[c].append(item)
                    break
        i = 0
        for cat in ['USA', 'Mag 7', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']:
            if cat in cats and cats[cat]:
                with cols2[i % 3]:
                    df = pd.DataFrame(cats[cat])[['Symbol','Last Price','1d Change (%)']].set_index('Symbol')
                    st.subheader(cat.replace('/', ' / '))
                    st.dataframe(estilizar(df), use_container_width=True)
                i += 1
        
        csv = pd.DataFrame(dados).to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV", data=csv, file_name=f"cotacoes_{agora.strftime('%Y%m%d_%H%M')}.csv")
    
    time.sleep(30)
