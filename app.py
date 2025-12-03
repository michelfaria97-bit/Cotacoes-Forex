# app.py — VERSÃO FINAL 100% FUNCIONAL (FOREX + FUTUROS) — DEZ/2025
import streamlit as st
import requests
import re
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração da página
st.set_page_config(
    page_title="Forex + Futuros ao Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="Chart Increasing",
    menu_items={'About': 'Dashboard Forex + Futuros Globais • Atualizado a cada minuto'}
)

# PWA (funciona no Streamlit Cloud)
st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0e1117">
""", unsafe_allow_html=True)

# ==================== PARES FOREX ====================
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
        'jpy-cad': 'Japanese Yen/Canadian Dollar', 'jpy-chf': 'Swiss Franc/Japanese Yen', 'jpy-nzd': 'Japanese Yen/New Zealand Dollar',
        'cad-usd': 'Canadian Dollar/US Dollar', 'cad-jpy': 'Canadian Dollar/Japanese Yen', 'cad-gbp': 'Canadian Dollar/British Pound',
        'cad-chf': 'Canadian Dollar/Swiss Franc', 'cad-nzd': 'Canadian Dollar/New Zealand Dollar', 'chf-usd': 'Swiss Franc/US Dollar',
        'chf-jpy': 'Swiss Franc/Japanese Yen', 'chf-gbp': 'Swiss Franc/British Pound', 'chf-cad': 'Swiss Franc/Canadian Dollar',
        'chf-nzd': 'Swiss Franc/New Zealand Dollar', 'cad-eur': 'Canadian Dollar/Euro', 'usd-eur': 'US Dollar/Euro', 'usd-gbp': 'US Dollar/British Pound',
        'jpy-aud': 'Japanese Yen/Australian Dollar', 'brl-usd': 'Brazilian Real/US Dollar', 'brl-jpy': 'Brazilian Real/Japanese Yen',
        'brl-gbp': 'Brazilian Real/British Pound', 'brl-nzd': 'Brazilian Real/New Zealand Dollar', 'brl-aud': 'Brazilian Real/Australian Dollar',
        'brl-eur': 'Brazilian Real/Euro', 'cny-usd': 'Chinese Yuan/US Dollar'
    }
}

# Mapeamento dos nomes completos → símbolos que você quer exibir
FUTURES_MAP = {
    'Dow Jones': 'US30', 'S&P 500': 'SPX500', 'Nasdaq 100': 'NAS100', 'Russell 2000': 'RUS2000',
    'Shanghai Composite': 'CHINA50', 'Nikkei 225': 'JPN225', 'Hang Seng': 'HK50', 'Nifty 50': 'IND50',
    'S&P/ASX 200': 'AUS200', 'Euro Stoxx 50': 'EU50', 'DAX': 'GER40', 'FTSE 100': 'UK100',
    'CAC 40': 'FRA40', 'IBEX 35': 'ESP35', 'FTSE MIB': 'ITA40'
}

# ==================== FOREX TURBO ====================
def get_single_pair(symbol, name):
    url = f'https://br.investing.com/currencies/{symbol}-historical-data'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'N/D', '1d Change (%)': 0.0}

        # Tenta pegar do JSON embutido na tabela histórica
        match = re.search(r'({"rowDate".*?})', r.text)
        if match:
            data = json.loads(match.group(1))
            price = data.get('last_close', 'N/D')
            if isinstance(price, str):
                price = price.replace(',', '.')
            change = data.get('change_precentRaw', 0.0)
        else:
            # Fallback: header da página
            soup = BeautifulSoup(r.text, 'html.parser')
            price = soup.find('div', {'data-test': 'instrument-price-last'})
            change_tag = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            price = price.text.strip() if price else 'N/D'
            change_text = change_tag.text.strip() if change_tag else '0%'
            change = float(re.sub(r'[^\d.-]', '', change_text.replace(',', '.')) or 0)

        return {
            'Symbol': symbol.upper().replace('-', '/'),
            'Name': name,
            'Last Price': price,
            '1d Change (%)': round(float(change), 2)
        }
    except:
        return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0}

@st.cache_data(ttl=55)
def fetch_all_turbo():
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_symbol = {executor.submit(get_single_pair, symbol, name): symbol for symbol, name in assets['Forex'].items()}
        for future in as_completed(future_to_symbol):
            results.append(future.result())
    return results

# ==================== FUTUROS ====================
@st.cache_data(ttl=55)
def fetch_futures_data():
    url = 'https://br.investing.com/indices/indices-futures'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    results = {'EUA': [], 'Ásia-Pacífico': [], 'Europa': []}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        rows = soup.find_all('tr', {'class': re.compile(r'datatable-v2_row')})
        for row in rows:
            try:
                name_tag = row.find('a', class_='overflow-hidden')
                if not name_tag: continue
                full_name = name_tag.get_text(strip=True)

                symbol = None
                for key, val in FUTURES_MAP.items():
                    if key.lower() in full_name.lower():
                        symbol = val
                        break
                if not symbol: continue

                cells = row.find_all('td')
                if len(cells) < 8: continue

                last = cells[3].get_text(strip=True)
                change_text = cells[7].get_text(strip=True).replace('%', '').replace('(', '').replace(')', '')
                try:
                    change = round(float(change_text.replace(',', '.')), 2)
                except:
                    change = 0.0

                item = {'Símbolo': symbol, 'Último': last, 'Var. 1D (%)': change}

                if symbol in ['US30', 'SPX500', 'NAS100', 'RUS2000']:
                    results['EUA'].append(item)
                elif symbol in ['CHINA50', 'JPN225', 'HK50', 'IND50', 'AUS200']:
                    results['Ásia-Pacífico'].append(item)
                elif symbol in ['EU50', 'GER40', 'UK100', 'FRA40', 'ESP35', 'ITA40']:
                    results['Europa'].append(item)
            except:
                continue
    except:
        pass
    return results

# ==================== AGRUPAMENTO E GRÁFICO ====================
def agrupar_por_base(data):
    grupos = { 'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
               'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [], 'Franco Suíço': [],
               'Real Brasileiro': [], 'Yuan Chinês': [] }
    for item in data:
        name = item['Name']
        if name.startswith('US Dollar'): grupos['Dólar Americano'].append(item)
        elif name.startswith('Euro'): grupos['Euro'].append(item)
        elif name.startswith('British Pound'): grupos['Libra Esterlina'].append(item)
        elif name.startswith('Japanese Yen'): grupos['Iene Japonês'].append(item)
        elif name.startswith('Australian Dollar'): grupos['Dólar Australiano'].append(item)
        elif name.startswith('New Zealand Dollar'): grupos['Dólar Neozelandês'].append(item)
        elif name.startswith('Canadian Dollar'): grupos['Dólar Canadense'].append(item)
        elif name.startswith('Swiss Franc'): grupos['Franco Suíço'].append(item)
        elif name.startswith('Brazilian Real'): grupos['Real Brasileiro'].append(item)
        elif name.startswith('Chinese Yuan'): grupos['Yuan Chinês'].append(item)
    return {k: v for k, v in grupos.items() if v}

def grafico_forca(data):
    df = pd.DataFrame(data)
    df['Base'] = df['Symbol'].str.split('/').str[0]
    media = df.groupby('Base')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
    fig = px.bar(media.reset_index(), x='Base', y='1d Change (%)',
                 title='Força Relativa Média das Moedas (24h)',
                 color='1d Change (%)',
                 color_continuous_scale=['red', 'orange', 'yellow', 'lightgreen', 'green'],
                 text='1d Change (%)')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig

def cor_segura(val):
    try:
        v = float(val)
        return "color: #00ff00; font-weight: bold" if v > 0 else "color: #ff0066; font-weight: bold" if v < 0 else "color: white"
    except:
        return "color: white"

# ==================== LOOP PRINCIPAL ====================
placeholder = st.empty()

while True:
    start = time.time()
    with placeholder.container():
        st.markdown("<h1 style='text-align: center; color: #00cc00;'>Forex + Futuros Globais • Ao Vivo</h1>", unsafe_allow_html=True)

        # Dados
        dados_forex = fetch_all_turbo()
        dados_futuros = fetch_futures_data()

        tempo = round(time.time() - start, 1)
        st.markdown(f"**Atualizado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} • Tempo de carga: **{tempo}s**")

        # ==================== FUTUROS ====================
        st.markdown("---")
        st.header("Futuros de Índices Globais")

        cols_fut = st.columns(3)
        regioes = ['EUA', 'Ásia-Pacífico', 'Europa']

        for i, regiao in enumerate(regioes):
            with cols_fut[i]:
                st.subheader(regiao)
                lista = dados_futuros.get(regiao, [])
                if not lista:
                    st.info("Sem dados")
                    continue
                df = pd.DataFrame(lista)
                df['Var. 1D (%)'] = pd.to_numeric(df['Var. 1D (%)'], errors='coerce').fillna(0).round(2)
                df['Último'] = df['Último'].astype(str)
                df = df.set_index('Símbolo')

                styled = df.style\
                    .map(cor_segura, subset=['Var. 1D (%)'])\
                    .format({'Var. 1D (%)': '{:+.2f}%'})
                st.dataframe(styled, use_container_width=True)

        # ==================== FOREX ====================
        st.markdown("---")
        st.header("Pares de Moedas (Forex)")

        grupos = agrupar_por_base(dados_forex)
        cols = st.columns(4)
        for i, (moeda, lista) in enumerate(grupos.items()):
            with cols[i % 4]:
                st.subheader(moeda)
                df = pd.DataFrame(lista)[['Symbol', 'Last Price', '1d Change (%)']]
                df = df.set_index('Symbol')
                styled = df.style.map(cor_segura, subset=['1d Change (%)']).format({'1d Change (%)': '{:+.2f}%'})
                st.dataframe(styled, use_container_width=True)

        # Gráfico de força
        st.markdown("---")
        st.header("Força Relativa das Moedas (24h)")
        st.plotly_chart(grafico_forca(dados_forex), use_container_width=True)

        # Download
        csv = pd.DataFrame(dados_forex).to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Baixar todos os pares Forex (CSV)",
            data=csv,
            file_name=f"forex_futuros_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

    time.sleep(60)
