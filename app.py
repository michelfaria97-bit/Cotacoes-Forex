# app.py — VERSÃO FINAL COM GRÁFICO DE FORÇA RELATIVA + NOVAS COTAÇÕES (Forex Agrupado Corretamente)

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

st.set_page_config(
    page_title="Cotações ao Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📈",
    # ⇓⇓⇓ ESSAS 3 LINHAS TRANSFORMAM EM PWA ⇓⇓⇓
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Força o manifesto PWA (funciona no Streamlit Cloud)
st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1f1f1f">
""", unsafe_allow_html=True)

# ==================== TODOS OS ATIVOS ====================
assets = {
    # PARES FOREX 
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
        'jpy-aud': 'Australian Dollar/Japanese Yen', 'brl-cad': 'Brazilian Real/Canadian Dollar', 'cny-usd': 'US Dollar/Chinese Yuan',
        'cny-nzd': 'New Zealand Dollar/Chinese Yuan', 'cny-jpy': 'Japanese Yen/Chinese Yuan', 'cny-gbp': 'British Pound/Chinese Yuan',
        'cny-chf': 'Swiss Franc/Chinese Yuan', 'cny-aud': 'Australian Dollar/Chinese Yuan', 'cny-eur': 'Euro/Chinese Yuan',
        'brl-usd': 'US Dollar/Brazilian Real', 'brl-jpy': 'Japanese Yen/Brazilian Real', 'brl-gbp': 'British Pound/Brazilian Real', 'brl-nzd': 'New Zealand Dollar/Brazilian Real',
        'brl-aud': 'Australian Dollar/Brazilian Real', 'brl-eur': 'Euro/Brazilian Real'
    },
    # ÍNDICES EUA
    'USA': {
        'us-spx-500-futures': 'S&P 500', 'nq-100-futures': 'Nasdaq 100', 'us-30-futures': 'US30 (Dow)',
        'smallcap-2000-futures': 'Russel 2000', 'volatility-s-p-500': 'VIX', 'usdollar': 'DXY (US Dollar Index)'
    },
    # ÍNDICES ASIA/PACÍFICO
    'Asia/Pacifico': {
        'hong-kong-40-futures': 'Hang Seng', 'shanghai-composite': 'SSE Composite',
        'japan-225-futures': 'Nikkei 225', 'ftse-china-25': 'FTSE China'
    },
    # ÍNDICES EUROPA
    'Europa': {
        'uk-100-futures': 'FTSE 100', 'germany-30-futures': 'DAX', 'france-40-futures': 'CAC 40',
        'eu-stocks-50-futures': 'STOXX 50', 'spain-35-futures': 'IBEX 35'
    },
    # COMMODITIES
    'Commodities': {
        'gold': 'Gold', 'silver': 'Silver', 'platinum': 'Platinum', 'copper': 'Copper',
        'crude-oil': 'Crude Oil (WTI)', 'brent-oil': 'Brent Oil', 'natural-gas': 'Natural Gas'
    },
    # CRYPTO
    'Crypto': {
        'btc-usd': 'Bitcoin', 'eth-usd': 'Ethereum'
    }
}

# Mapeamento do tipo de ativo (para construir a URL)
ASSET_TYPES = {
    'Forex': 'currencies',
    'USA': 'indices',
    'Asia/Pacifico': 'indices',
    'Europa': 'indices',
    'Commodities': 'commodities',
    'Crypto': 'crypto'
}

# ==================== FUNÇÕES DE AGRUPAMENTO (REVISADA) ====================

# Mapeamento de categorias de Forex para Grupos de Moeda Base (para manter a estrutura do original)
# Chaves são as bases das moedas no nome (e.g., 'Euro', 'US Dollar')
FOREX_GROUPS_MAPPING = {
    'US Dollar': 'Dólar Americano', 
    'Euro': 'Euro', 
    'British Pound': 'Libra Esterlina', 
    'Japanese Yen': 'Iene Japonês',
    'Australian Dollar': 'Dólar Australiano', 
    'New Zealand Dollar': 'Dólar Neozelandês', 
    'Canadian Dollar': 'Dólar Canadense', 
    'Swiss Franc': 'Franco Suíço',
    'Brazilian Real': 'Real Brasileiro', 
    'Chinese Yuan': 'Yuan Chinês'
}


def agrupar_forex(data):
    """Agrupa pares Forex estritamente pela moeda base no nome, como no código original."""
    grupos = {v: [] for v in FOREX_GROUPS_MAPPING.values()}
    
    # Ordem de preferência (para evitar mistura de EUR/USD e USD/JPY, por exemplo)
    # USD é a base em USD/XXX. EUR é a base em EUR/XXX.
    ordem_bases = ['Euro', 'British Pound', 'Australian Dollar', 'New Zealand Dollar', 'US Dollar', 
                   'Canadian Dollar', 'Swiss Franc', 'Japanese Yen', 'Brazilian Real', 'Chinese Yuan']

    for item in data:
        name = item['Name']
        # Tenta encontrar a primeira moeda no nome (a moeda BASE, que define o grupo)
        for base_prefix in ordem_bases:
            if name.startswith(base_prefix):
                group_name = FOREX_GROUPS_MAPPING[base_prefix]
                grupos[group_name].append(item)
                break
            
    # Remove grupos vazios e retorna
    return {k: v for k, v in grupos.items() if v}

# ==================== FUNÇÕES DE SCRAPING (INALTERADAS) ====================

def get_single_forex(symbol, name):
    url = f'https://br.investing.com/currencies/{symbol}-historical-data'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
             return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'N/D', '1d Change (%)': 0.0, 'Category': 'Forex'}

        soup = BeautifulSoup(r.text, 'html.parser')
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})

        price = price_elem.text.strip() if price_elem else 'N/D'
        change_text = change_elem.text.strip() if change_elem else '(0,00%)'
        
        # Limpa o texto de preço/porcentagem
        price_clean = price.replace(',', '.').replace('.', '', price.count('.') - 1)
        num = re.sub(r'[^\d,.-]', '', change_text).replace(',', '.')
        change_pct = round(float(num or 0), 2)

        return {
            'Symbol': symbol.upper().replace('-', '/'),
            'Name': name,
            'Last Price': price_clean,
            '1d Change (%)': change_pct,
            'Category': 'Forex'
        }

    except Exception as e:
        return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0, 'Category': 'Forex'}

def get_single_non_forex(category, symbol, name):
    if symbol == 'usdollar':
        url = 'https://br.investing.com/indices/usdollar'
    elif category == 'Crypto':
        url = f'https://br.investing.com/{ASSET_TYPES[category]}/{symbol.split("-")[0].lower()}/{symbol}'
    else:
        url = f'https://br.investing.com/{ASSET_TYPES[category]}/{symbol}'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
             return {'Symbol': name.upper(), 'Name': name, 'Last Price': 'N/D', '1d Change (%)': 0.0, 'Category': category}
        
        soup = BeautifulSoup(r.text, 'html.parser')
        price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
        change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})

        price = price_elem.text.strip() if price_elem else 'N/D'
        change_text = change_elem.text.strip() if change_elem else '(0,00%)'
        
        price_clean = price.replace(',', '.').replace('.', '', price.count('.') - 1)
        num = re.sub(r'[^\d,.-]', '', change_text).replace(',', '.')
        change_pct = round(float(num or 0), 2)

        display_symbol = name if category != 'Forex' else symbol.upper().replace('-', '/')

        return {
            'Symbol': display_symbol,
            'Name': name,
            'Last Price': price_clean,
            '1d Change (%)': change_pct,
            'Category': category
        }

    except Exception as e:
        return {'Symbol': name.upper(), 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0, 'Category': category}

# ==================== FUNÇÃO TURBO (FETCH GERAL - INALTERADA) ====================
@st.cache_data(ttl=55)
def fetch_all_turbo():
    results = []
    all_futures = {}

    with ThreadPoolExecutor(max_workers=25) as executor:
        # 1. Forex
        for symbol, name in assets['Forex'].items():
            future = executor.submit(get_single_forex, symbol, name)
            all_futures[future] = f"Forex:{symbol}"
            
        # 2. Non-Forex (Índices, Commodities, Crypto)
        for category in ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']:
            for symbol, name in assets[category].items():
                future = executor.submit(get_single_non_forex, category, symbol, name)
                all_futures[future] = f"{category}:{symbol}"

        for future in as_completed(all_futures):
            results.append(future.result())
            
    # Agrupa por categoria para o display
    grouped_results = {}
    for item in results:
        category = item['Category']
        if category not in grouped_results:
            grouped_results[category] = []
        grouped_results[category].append(item)
        
    return grouped_results

# ==================== FUNÇÃO GRÁFICO (INALTERADA) ====================
def grafico_forca(data):
    if not data:
        return None
        
    df = pd.DataFrame(data)
    df['Base'] = df['Symbol'].str.split('/').str[0]
    
    media = df.groupby('Base')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
    
    fig = px.bar(media.reset_index(), x='Base', y='1d Change (%)',
                 title='📈 Força Relativa Média das Moedas (1 dia)',
                 color='1d Change (%)',
                 color_continuous_scale=['red', 'orange', 'lightgray', 'lightgreen', 'green'], 
                 text='1d Change (%)')
                 
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False, xaxis={'categoryorder': 'total descending'})
    return fig

# ==================== LOOP PRINCIPAL (AJUSTADO PARA A NOVA FUNÇÃO DE AGRUPAMENTO) ====================
placeholder = st.empty()

while True:
    start_time = time.time()
    with placeholder.container():
        # Retorna um dicionário com categorias como chaves
        dados_agrupados = fetch_all_turbo()
        tempo = round(time.time() - start_time, 1)

        st.markdown(f"**Última Atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} • Carregado em **{tempo}s**")
        st.markdown("---")
        
        # Função de estilização para o dataframe
        def estilizar_dataframe(df):
             def cor(val):
                color = 'red' if val < 0 else 'green' if val > 0 else 'gray'
                return f'color: {color}; font-weight: bold'

             styled = df.style.map(cor, subset=['1d Change (%)']) \
                             .format({'1d Change (%)': '{:.2f}%'})
             return styled

        # 1. EXIBE GRÁFICO DE FORÇA RELATIVA (SOMENTE FOREX)
        if 'Forex' in dados_agrupados:
            st.plotly_chart(grafico_forca(dados_agrupados['Forex']), use_container_width=True, key=f"plotly_force_{int(time.time())}")
            st.markdown("---")


        # 2. EXIBE FOREX SEPARADO POR MOEDA BASE (AGORA COM AGRUPAMENTO MAIS PRECISO)
        if 'Forex' in dados_agrupados:
            st.header("💱 Forex - Pares de Moedas")
            # CHAMADA DA FUNÇÃO DE AGRUPAMENTO CORRIGIDA
            forex_grupos = agrupar_forex(dados_agrupados['Forex']) 
            forex_cols = st.columns(4)
            
            # Garante que a ordem das colunas de Forex seja a mesma do FOREX_GROUPS_MAPPING
            ordered_groups = [g for g in FOREX_GROUPS_MAPPING.values() if g in forex_grupos]
            
            for idx, titulo in enumerate(ordered_groups):
                lista = forex_grupos[titulo]
                with forex_cols[idx % 4]:
                    df = pd.DataFrame(lista)[['Symbol', 'Last Price', '1d Change (%)']]
                    df.set_index('Symbol', inplace=True)
                    st.subheader(titulo)
                    st.dataframe(estilizar_dataframe(df), width="stretch")
            st.markdown("---")

        # 3. EXIBE ÍNDICES, COMMODITIES E CRYPTO (Inalterado)
        st.header("🌎 Outros Ativos (Índices, Commodities e Crypto)")
        ordenacao = ['USA', 'Asia/Pacifico', 'Europa', 'Commodities', 'Crypto']
        
        for category in ordenacao:
            if category in dados_agrupados:
                current_data = dados_agrupados[category]
                
                st.subheader(category)

                df = pd.DataFrame(current_data)[['Symbol', 'Last Price', '1d Change (%)']]
                df.set_index('Symbol', inplace=True)
                
                st.dataframe(estilizar_dataframe(df), use_container_width=True)
                
                st.markdown("***")
        

        # Download CSV - Inclui todos os dados
        all_data_list = [item for sublist in dados_agrupados.values() for item in sublist]
        csv = pd.DataFrame(all_data_list).to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="Baixar todos os dados (CSV)",
            data=csv,
            file_name=f"cotacoes_ao_vivo_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
    time.sleep(60)
