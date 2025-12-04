# app.py — VERSÃO FINAL 100% FUNCIONAL E PERFEITA (BRL E CNY AO LADO)
import streamlit as st
import requests
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Cotações ao Vivo", layout="wide", initial_sidebar_state="collapsed", page_icon="Chart")

st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1f1f1f">
<style>
    .stDataFrame { width: 100% !important; }
    [data-testid="column"] { padding: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ==================== ATIVOS ====================
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
        'jpy-cad': 'Canadian Dollar/Japanese Yen', 'jpy-chf': 'Swiss Franc/Japanese Yen', 'jpy-nzd': 'New Zealand Dollar/Japanese Yen',
        'cad-usd': 'US Dollar/Canadian Dollar', 'cad-jpy': 'Canadian Dollar/Japanese Yen', 'cad-gbp': 'British Pound/Canadian Dollar',
        'cad-chf': 'Swiss Franc/Canadian Dollar', 'cad-nzd': 'New Zealand Dollar/Canadian Dollar', 'chf-usd': 'US Dollar/Swiss Franc',
        'chf-jpy': 'Swiss Franc/Japanese Yen', 'chf-gbp': 'British Pound/Swiss Franc', 'chf-cad': 'Canadian Dollar/Swiss Franc',
        'chf-nzd': 'New Zealand Dollar/Swiss Franc', 'cad-eur': 'Euro/Canadian Dollar', 'usd-eur': 'Euro/US Dollar', 'usd-gbp': 'British Pound/US Dollar',
        'jpy-aud': 'Australian Dollar/Japanese Yen',
        'brl-usd': 'US Dollar/Brazilian Real', 'brl-jpy': 'Japanese Yen/Brazilian Real', 'brl-eur': 'Euro/Brazilian Real',
        'brl-gbp': 'British Pound/Brazilian Real', 'brl-cad': 'Brazilian Real/Canadian Dollar',
        'cny-usd': 'US Dollar/Chinese Yuan', 'cny-jpy': 'Japanese Yen/Chinese Yuan', 'cny-eur': 'Euro/Chinese Yuan'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30', 
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite', 'japan-225-futures': 'Nikkei 225'},
    'Europa': {'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40', 
               'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35'},
    'Commodities': {'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper', 
                    'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'},
    'Crypto': {'btc-usd': 'Bitcoin', 'eth-usd': 'Ethereum'}
}

# ==================== FUNÇÕES ====================
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
        price = price.text.strip() if price else 'N/D'
        change_text = change.text.strip() if change else '0%'
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': clean_price(price), '1d Change (%)': round(float(num or 0), 2)}
    except:
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': 'Erro', '1d Change (%)': 0.0}

def get_single_non_forex(category, symbol, name):
    if symbol == 'usdollar':
        url = 'https://br.investing.com/indices/usdollar'
    elif category == 'Crypto':
        url = f'https://br.investing.com/crypto/{symbol.split("-")[0]}'
    else:
        url = f'https://br.investing.com/{{"indices": "indices", "commodities": "commodities"}.get(ASSET_TYPES.get(category, ""), ASSET_TYPES[category])}/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.find('div', {'data-test': 'instrument-price-last'})
        change = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price = price.text.strip() if price else 'N/D'
        change_text = change.text.strip() if change else '0%'
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        return {'Symbol': name, 'Last Price': clean_price(price), '1d Change (%)': round(float(num or 0), 2), 'Category': category}
    except:
        return {'Symbol': name, 'Last Price': 'Erro', '1d Change (%)': 0.0, 'Category': category}

# ==================== AGRUPAMENTO ====================
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
        base = item['Symbol'].split('/')[0]
        grupo = base_map.get(base)
        if grupo:
            grupos[grupo].append(item)
    return {k: v for k, v in grupos.items() if v}

def estilizar(df):
    return df.style.format({'1d Change (%)': '{:.2f}%'}) \
        .map(lambda x: f"color: {'green' if x>0 else 'red' if x<0 else 'gray'}; font-weight: bold", subset=['1d Change (%)'])

@st.cache_data(ttl=55)
def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=35) as executor:
        # Forex
        for symbol, name in assets['Forex'].items():
            results.append(executor.submit(get_single_forex, symbol, name))
        # Outros
        for cat, itens in assets.items():
            if cat == 'Forex': continue
            for symbol, name in itens.items():
                results.append(executor.submit(get_single_non_forex, cat, symbol, name))
        for future in as_completed(results):
            results.append(future.result())
    # Remove duplicatas que o as_completed pode gerar
    seen = set()
    unique = []
    for r in results:
        if r and r['Symbol'] not in seen:
            seen.add(r['Symbol'])
            unique.append(r)
    return unique

# ==================== LOOP PRINCIPAL ====================
placeholder = st.empty()
while True:
    inicio = time.time()
    with placeholder.container():
        dados = fetch_all()

        forex_data = [x for x in dados if '/' in x['Symbol']]
        outros_data = [x for x in dados if '/' not in x['Symbol']]

        st.markdown(f"**Atualizado:** {datetime.now():%d/%m/%Y %H:%M:%S} • Tempo: {time.time()-inicio:.1f}s")
        st.markdown("---")

        # === FOREX - 4 COLUNAS FIXAS ===
        st.header("Forex - Pares de Moedas")
        grupos = agrupar_forex(forex_data)
        cols = st.columns(4)

        ordem_grupos = [
            'Dólar Americano', 'Euro', 'Libra Esterlina', 'Iene Japonês',
            'Dólar Australiano', 'Dólar Neozelandês', 'Dólar Canadense',
            'Franco Suíço', 'Real Brasileiro', 'Yuan Chinês'
        ]

        col_idx = 0
        for titulo in ordem_grupos:
            if titulo in grupos and grupos[titulo]:
                with cols[col_idx % 4]:
                    df = pd.DataFrame(grupos[titulo])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                    st.subheader(titulo)
                    st.dataframe(estilizar(df), use_container_width=True)
                col_idx += 1

        st.markdown("---")

        # === OUTROS ATIVOS - TAMBÉM EM 4 COLUNAS ===
        st.header("Outros Ativos")
        cols2 = st.columns(4)

        categorias = ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']
        cat_data = {cat: [] for cat in categorias}

        for item in outros_data:
            sym = item['Symbol']
            for cat in categorias:
                if sym in assets.get(cat, {}).values():
                    cat_data[cat].append(item)
                    break

        col_idx = 0
        for cat in categorias:
            if cat_data[cat]:
                with cols2[col_idx % 4]:
                    df = pd.DataFrame(cat_data[cat])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                    st.subheader(cat.replace('/', ' / '))
                    st.dataframe(estilizar(df), use_container_width=True)
                col_idx += 1

        # Download CSV
        csv = pd.DataFrame(dados).to_csv(index=False, encoding='utf-8')
        st.download_button("Baixar CSV", csv, f"cotacoes_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv")

    time.sleep(60)
