# app.py — VERSÃO FINAL PERFEITA (COM GRÁFICO + BRL/CN AO LADO + CRYPTO CORRIGIDO)
import streamlit as st
import requests
import re
import time
from datetime import datetime, timezone, timedelta
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
        'jpy-cad': 'Japanese Yen/Canadian Dollar', 'jpy-chf': 'Japanese Yen/Swiss Franc', 'jpy-nzd': 'Japanese Yen/New Zealand Dollar',
        'cad-usd': 'Canadian Dollar/US Dollar', 'cad-jpy': 'Canadian Dollar/Japanese Yen', 'cad-gbp': 'Canadian Dollar/British Pound',
        'cad-chf': 'Canadian Dollar/Swiss Franc', 'cad-nzd': 'Canadian Dollar/New Zealand Dollar', 'chf-usd': 'Swiss Franc/US Dollar',
        'chf-jpy': 'Swiss Franc/Japanese Yen', 'chf-gbp': 'Swiss Franc/British Pound', 'chf-cad': 'Swiss Franc/Canadian Dollar',
        'chf-nzd': 'Swiss Franc/New Zealand Dollar', 'cad-eur': 'Canadian Dollar/Euro', 'usd-eur': 'US Dollar/Euro', 'usd-gbp': 'US Dollar/British Pound',
        'jpy-aud': 'Japanese Yen/Australian Dollar', 'brl-cad': 'Brazilian Real/Canadian Dollar', 'cny-usd': 'Chinese Yuan/US Dollar',
        'cny-nzd': 'Chinese Yuan/New Zealand Dollar', 'cny-jpy': 'Chinese Yuan/Japanese Yen', 'cny-gbp': 'Chinese Yuan/British Pound',
        'cny-chf': 'Chinese Yuan/Swiss Franc', 'cny-aud': 'Chinese Yuan/Australian Dollar', 'cny-eur': 'Chinese Yuan/Euro',
        'brl-usd': 'Brazilian Real/US Dollar', 'brl-jpy': 'Brazilian Real/Japanese Yen', 'brl-gbp': 'Brazilian Real/British Pound', 'brl-nzd': 'Brazilian Real/New Zealand Dollar', 
        'brl-aud': 'Brazilian Real/Australian Dollar', 'brl-eur': 'Brazilian Real/Euro'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30', 
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite', 'japan-225-futures': 'Nikkei 225', 'ftse-china-25': 'FTSE China'},
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
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price = price_elem.text.strip() if price_elem else 'N/D'
        change_text = change_elem.text.strip() if change_elem else '0%'
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': clean_price(price), '1d Change (%)': round(float(num or 0), 2)}
    except:
        return {'Symbol': symbol.upper().replace('-','/'), 'Last Price': 'Erro', '1d Change (%)': 0.0}

def get_single_non_forex(category, symbol, name):
    if symbol == 'usdollar':
        url = 'https://br.investing.com/indices/usdollar'
    elif symbol == 'btc-usd':
        url = 'https://br.investing.com/indices/investing.com-btc-usd'
    elif symbol == 'eth-usd':
        url = 'https://br.investing.com/indices/investing.com-eth-usd'
    elif category in ['USA', 'Asia/Pacifico', 'Europa']:
        url = f'https://br.investing.com/indices/{symbol}'
    else:
        url = f'https://br.investing.com/commodities/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price = price_elem.text.strip() if price_elem else 'N/D'
        change_text = change_elem.text.strip() if change_elem else '0%'
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
                 text='1d Change (%)', title='Força Relativa Média das Moedas (1 dia)')
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
            except: pass
    seen = set()
    unique = [r for r in results if r['Symbol'] not in seen and not seen.add(r['Symbol'])]
    return unique

# ==================== LOOP PRINCIPAL ====================
placeholder = st.empty()
while True:
    inicio = time.time()
    with placeholder.container():
        dados = fetch_all()
        tempo = round(time.time() - start_time, -3)
        
        st.markdown(f"**Atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} • Carregado em **{tempo}s**")
        st.markdown("---")

        # GRÁFICO DE FORÇA (MANTIDO!)
        fig = grafico_forca(dados)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

        # FOREX — 4 COLUNAS
        st.header("Forex - Pares de Moedas")
        forex_data = [x for x in dados if '/' in x['Symbol']]
        grupos = agrupar_forex(forex_data)
        cols = st.columns(4)

        ordem = ['Dólar Americano', 'Euro', 'Libra Esterlina', 'Iene Japonês',
                 'Dólar Australiano', 'Dólar Neozelandês', 'Dólar Canadense',
                 'Franco Suíço', 'Real Brasileiro', 'Yuan Chinês']

        col_idx = 0
        for titulo in ordem:
            if titulo in grupos and grupos[titulo]:
                with cols[col_idx % 4]:
                    df = pd.DataFrame(grupos[titulo])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                    st.subheader(titulo)
                    st.dataframe(estilizar(df), use_container_width=True)
                col_idx += 1

        st.markdown("---")

        # OUTROS ATIVOS — 4 COLUNAS
        st.header("Outros Ativos")
        outros = [x for x in dados if '/' not in x['Symbol']]
        cols2 = st.columns(4)
        cat_map = {'USA': [], 'Asia/Pacifico': [], 'Europa': [], 'Commodities': [], 'Crypto': []}
        for item in outros:
            for cat, itens in assets.items():
                if cat == 'Forex': continue
                if item['Symbol'] in itens.values():
                    cat_map[cat].append(item)
                    break

        col_idx = 0
        for cat in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']:
            if cat_map[cat]:
                with cols2[col_idx % 4]:
                    df = pd.DataFrame(cat_map[cat])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                    st.subheader(cat.replace('/', ' / '))
                    st.dataframe(estilizar(df), use_container_width=True)
                col_idx += 1

        # Download
        csv = pd.DataFrame(dados).to_csv(index=False, encoding='utf-8')
        st.download_button("Baixar todos os dados (CSV)", csv, f"cotacoes_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv")

    time.sleep(60)





