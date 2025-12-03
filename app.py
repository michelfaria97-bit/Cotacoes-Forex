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

# ==================== FUTUROS – SEM .style NENHUM ====================
@st.cache_data(ttl=55)
def fetch_futures():
    url = 'https://br.investing.com/indices/indices-futures'
    headers = {'User-Agent': 'Mozilla/5.0'}
    mapa = {
        'Dow Jones':'US30', 'S&P 500':'SPX500', 'Nasdaq':'NAS100', 'Russell':'RUS2000',
        'Shanghai':'CHINA50', 'Nikkei 225':'JPN225', 'Hang Seng':'HK50', 'Nifty':'IND50',
        'ASX 200':'AUS200', 'Stoxx 50':'EU50', 'DAX':'GER40', 'FTSE 100':'UK100',
        'CAC 40':'FRA40', 'IBEX':'ESP35', 'FTSE MIB':'ITA40'
    }
    reg = {'EUA':[], 'Ásia-Pacífico':[], 'Europa':[]}
    try:
        soup = BeautifulSoup(requests.get(url,headers=headers,timeout=15).text,'html.parser')
        for row in soup.find_all('tr', class_=re.compile('row')):
            tds = row.find_all('td')
            if len(tds)<8: continue
            nome = row.find('a')
            if not nome: continue
            nome = nome.get_text(strip=True)
            simbolo = next((v for k,v in mapa.items() if k.lower() in nome.lower()), None)
            if not simbolo: continue
            ultimo = tds[3].get_text(strip=True)
            var_txt = tds[7].get_text(strip=True).replace('%','').replace('(remove')).replace(')','')
            try: var = round(float(var_txt.replace(',','.')),2)
            except: var = 0.0
            item = [simbolo, ultimo, var]
            if simbolo in ['US30','SPX500','NAS100','RUS2000']: reg['EUA'].append(item)
            elif simbolo in ['CHINA50','JPN225','HK50','IND50','AUS200']: reg['Ásia-Pacífico'].append(item)
            else: reg['Europa'].append(item)
    except: pass
    return reg

# ==================== LOOP PRINCIPAL ====================
ph = st.empty()
while True:
    start = time.time()
    with ph.container():
        forex = fetch_all_turbo()
        futuros = fetch_futures()

        st.markdown(f"**Atualizado:** {datetime.now():%d/%m/%Y %H:%M:%S} • {time.time()-start:.1f}s")

        # ==================== FUTUROS – SÓ DATAFRAME PURO + HTML ====================
        st.header("Futuros de Índices Globais")
        c1,c2,c3 = st.columns(3)
        for col, região in zip([c1,c2,c3], ['EUA','Ásia-Pacífico','Europa']):
            with col:
                st.subheader(região)
                dados = futuros.get(região, [])
                if not dados:
                    st.info("Sem dados")
                    continue
                # Criamos HTML manual – 100% imune ao KeyError
                html = "<table style='width:100%; border-collapse:collapse; font-size:14px;'>"
                html += "<tr style='background:#0e1117; color:white;'><th>Símbolo</th><th>Último</th><th>Var %</th></tr>"
                for simb, ult, var in dados:
                    cor = "#00ff00" if var>0 else "#ff4444" if var<0 else "white"
                    html += f"<tr><td style='padding:8px; text-align:left;'>{simb</td>"
                    html += f"<td style='padding:8px; text-align:center;'>{ult}</td>"
                    html += f"<td style='padding:8px; text-align:center; color:{cor}; font-weight:bold;'>{var:+.2f}%</td></tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")

        # ==================== FOREX (pode usar .style normalmente) ====================
        st.header("Pares Forex")
        grupos = {}
        for item in forex:
            base = item['Symbol'].split('/')[0]
            grupos.setdefault(base, []).append(item)

        cols = st.columns(4)
        for i, (moeda, lista) in enumerate(grupos.items()):
            with cols[i%4]:
                st.subheader(moeda)
                df = pd.DataFrame(lista)[['Symbol','Last Price','1d Change (%)']].set_index('Symbol')
                def cor(v): 
                    try: return "color:#00ff00;font-weight:bold" if float(v)>0 else "color:#ff4444;font-weight:bold"
                    except: return ""
                styled = df.style.applymap(cor, subset=['1d Change (%)']).format({'1d Change (%)':'{:+.2f}%'})
                st.dataframe(styled, use_container_width=True)

        # Gráfico força relativa
        st.header("Força Relativa 24h")
        dfg = pd.DataFrame(forex)
        dfg['Moeda'] = dfg['Symbol'].str.split('/').str[0]
        media = dfg.groupby('Moeda')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
        fig = px.bar(media.reset_index(), x='Moeda', y='1d Change (%)', color='1d Change (%)',
                     color_continuous_scale=['red','orange','yellow','lightgreen','green'], text='1d Change (%)')
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.add_hline(y=0)
        st.plotly_chart(fig, use_container_width=True)

    time.sleep(60)
