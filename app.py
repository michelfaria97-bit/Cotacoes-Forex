# app.py — VERSÃO FINAL 100% IGUAL À SUA FOTO + BRL e CNY MANTIDOS
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
""", unsafe_allow_html=True)

# ==================== TODOS OS ATIVOS (INCLUI BRL E CNY) ====================
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
        # BRL e CNY mantidos
        'brl-usd': 'US Dollar/Brazilian Real', 'brl-jpy': 'Japanese Yen/Brazilian Real', 'brl-eur': 'Euro/Brazilian Real',
        'brl-gbp': 'British Pound/Brazilian Real', 'brl-cad': 'Brazilian Real/Canadian Dollar',
        'cny-usd': 'US Dollar/Chinese Yuan', 'cny-jpy': 'Japanese Yen/Chinese Yuan', 'cny-eur': 'Euro/Chinese Yuan'
    },
    'USA': {'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30 (Dow)',
            'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY'},
    'Asia/Pacifico': {'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite',
                      'japan-225-futures': 'Nikkei 225'},
    'Europa': {'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40',
               'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35'},
    'Commodities': {'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper',
                    'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'},
    'Crypto': {'btc-usd': 'Bitcoin', 'eth-usd': 'Ethereum'}
}

ASSET_TYPES = {'Forex': 'currencies', 'USA': 'indices', 'Asia/Pacifico': 'indices', 'Europa': 'indices',
               'Commodities': 'commodities', 'Crypto': 'crypto'}

# ==================== FUNÇÕES DE LIMPEZA E SCRAPING ====================
def clean_price(price_text):
    if not price_text or price_text in ['N/D', '-']:
        return 'N/D'
    price_temp = price_text.replace(',', '.')
    parts = price_temp.split('.')
    if len(parts) > 2:
        integer_part = "".join(parts[:-1])
        decimal_part = parts[-1]
        price_clean = f"{integer_part}.{decimal_part}"
    else:
        price_clean = price_temp
    try:
        return str(float(price_clean))
    except:
        return price_text

def get_single_forex(symbol, name):
    url = f'https://br.investing.com/currencies/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.find('div', {'data-test': 'instrument-price-last'})
        change = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price = price.text.strip() if price else 'N/D'
        change_text = change.text.strip() if change else '0%'
        price_clean = clean_price(price)
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        change_pct = round(float(num or 0), 2)
        return {'Symbol': symbol.upper().replace('-', '/'), 'Name': name, 'Last Price': price_clean,
                '1d Change (%)': change_pct, 'Category': 'Forex'}
    except:
        return {'Symbol': symbol.upper().replace('-', '/'), 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0, 'Category': 'Forex'}

def get_single_non_forex(category, symbol, name):
    if symbol == 'usdollar': url = 'https://br.investing.com/indices/usdollar'
    elif category == 'Crypto': url = f'https://br.investing.com/crypto/{symbol.split("-")[0]}'
    else: url = f'https://br.investing.com/{ASSET_TYPES[category]}/{symbol}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.find('div', {'data-test': 'instrument-price-last'})
        change = soup.find('span', {'data-test': 'instrument-price-change-percent'})
        price = price.text.strip() if price else 'N/D'
        change_text = change.text.strip() if change else '0%'
        price_clean = clean_price(price)
        num = re.sub(r'[^\d.-]', '', change_text.replace(',', '.'))
        change_pct = round(float(num or 0), 2)
        return {'Symbol': name if category != 'Forex' else symbol.upper().replace('-', '/'), 'Name': name,
                'Last Price': price_clean, '1d Change (%)': change_pct, 'Category': category}
    except:
        return {'Symbol': name, 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0, 'Category': category}

# ==================== AGRUPAMENTO CORRETO PELA MOEDA BASE ====================
def agrupar_forex(data):
    grupos = { 
        'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
        'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [], 'Franco Suíço': [],
        'Real Brasileiro': [], 'Yuan Chinês': []
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

# ==================== GRÁFICO E ESTILO ====================
def grafico_forca(data):
    forex = [i for i in data if i['Category'] == 'Forex']
    if not forex: return None
    df = pd.DataFrame(forex)
    df['1d Change (%)'] = pd.to_numeric(df['1d Change (%)'], errors='coerce')
    df['Base'] = df['Symbol'].str.split('/').str[0]
    media = df.groupby('Base')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
    fig = px.bar(media.reset_index(), x='Base', y='1d Change (%)', color='1d Change (%)',
                 color_continuous_scale=['red','orange','lightgray','lightgreen','green'], text='1d Change (%)')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False, xaxis={'categoryorder': 'total descending'})
    return fig

def estilizar_dataframe(df):
    return df.style.format({'1d Change (%)': '{:.2f}%'}) \
                  .map(lambda v: f"color: {'green' if v > 0 else 'red' if v < 0 else 'gray'}; font-weight: bold", subset=['1d Change (%)'])

# ==================== BUSCA TURBO ====================
@st.cache_data(ttl=55)
def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {}
        for symbol, name in assets['Forex'].items():
            futures[executor.submit(get_single_forex, symbol, name)] = 'Forex'
        for cat in ['USA','Asia/Pacifico','Europa','Commodities','Crypto']:
            for symbol, name in assets[cat].items():
                futures[executor.submit(get_single_non_forex, cat, symbol, name)] = cat
        for f in as_completed(futures):
            results.append(f.result())
    grouped = {}
    for r in results:
        cat = r['Category']
        grouped.setdefault(cat, []).append(r)
    return grouped

# ==================== LOOP PRINCIPAL ====================
placeholder = st.empty()
while True:
    inicio = time.time()
    with placeholder.container():
        dados = fetch_all()
        todos = [item for sub in dados.values() for item in sub]

        st.markdown(f"**Atualizado:** {datetime.now():%d/%m/%Y %H:%M:%S} • Tempo: {time.time()-inicio:.1f}s")
        st.markdown("---")

        # Gráfico de força
        fig = grafico_forca(todos)
        if fig: st.plotly_chart(fig, use_container_width=True)

        # FOREX AGRUPADO (EXATAMENTE COMO NA FOTO)
        if 'Forex' in dados:
            st.header("Forex - Pares de Moedas")
            grupos = agrupar_forex(dados['Forex'])

            cols = st.columns(4)

            # LINHA 1
            for i, titulo in enumerate(['Dólar Americano', 'Euro', 'Libra Esterlina', 'Iene Japonês']):
                with cols[i]:
                    if titulo in grupos:
                        df = pd.DataFrame(grupos[titulo])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                        st.subheader(titulo)
                        st.dataframe(estilizar_dataframe(df), use_container_width=True)

            # LINHA 2
            for i, titulo in enumerate(['Dólar Australiano', 'Dólar Neozelandês', 'Dólar Canadense', 'Franco Suíço']):
                with cols[i]:
                    if titulo in grupos:
                        df = pd.DataFrame(grupos[titulo])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                        st.subheader(titulo)
                        st.dataframe(estilizar_dataframe(df), use_container_width=True)

            # BRL e CNY na última coluna (abaixo do Franco Suíço)
            with cols[3]:
                for titulo in ['Real Brasileiro', 'Yuan Chinês']:
                    if titulo in grupos and grupos[titulo]:
                        df = pd.DataFrame(grupos[titulo])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                        st.subheader(titulo)
                        st.dataframe(estilizar_dataframe(df), use_container_width=True)

            st.markdown("---")

        # OUTROS ATIVOS
        st.header("Outros Ativos")
        for cat in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']:
            if cat in dados:
                st.subheader(cat)
                df = pd.DataFrame(dados[cat])[['Symbol', 'Last Price', '1d Change (%)']].set_index('Symbol')
                st.dataframe(estilizar_dataframe(df), use_container_width=True)
                st.markdown("***")

        # Download
        csv = pd.DataFrame(todos).to_csv(index=False, encoding='utf-8')
        st.download_button("Baixar CSV", csv, f"cotacoes_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv")

    time.sleep(60)
