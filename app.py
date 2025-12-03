# app.py — VERSÃO FINAL COM FUTUROS INTEGRADOS

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
    page_title="Forex ao Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="💱",
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
        'jpy-aud': 'Japanese Yen/Australian Dollar', 'brl-cad': 'Brazilian Real/Canadian Dollar', 'cny-usd': 'Chinese Yuan/US Dollar',
        'cny-nzd': 'Chinese Yuan/New Zealand Dollar', 'cny-jpy': 'Chinese Yuan/Japanese Yen', 'cny-gbp': 'Chinese Yuan/British Pound',
        'cny-chf': 'Chinese Yuan/Swiss Franc', 'cny-aud': 'Chinese Yuan/Australian Dollar', 'cny-eur': 'Chinese Yuan/Euro',
        'brl-usd': 'Brazilian Real/US Dollar', 'brl-jpy': 'Brazilian Real/Japanese Yen', 'brl-gbp': 'Brazilian Real/British Pound', 'brl-nzd': 'Brazilian Real/New Zealand Dollar', 
        'brl-aud': 'Brazilian Real/Australian Dollar', 'brl-eur': 'Brazilian Real/Euro'
    }
}

# Mapeamento do nome completo para o símbolo curto desejado (para a coluna "Símbolo")
FUTURES_MAP = {
    # EUA
    'Dow Jones': 'US30F',
    'S&P 500': 'ESF',
    'Nasdaq 100': 'NDQF',
    'Russell 2000': 'RTYF',
    # Ásia-Pacífico
    'Shanghai SE': 'CSI300F', # Usando Shanghai SE como proxy/referência para China
    'Nikkei': 'NK225F',
    'Hang Seng Index': 'HSF',
    'Nifty 50': 'NIFTYF',
    'ASX 200': 'ASX200F',
    # Europa
    'Stoxx 600': 'STX600F',
    'DAX': 'DAXF',
    'FTSE 100': 'FTSEF',
    'CAC 40': 'CAC40F',
    'FTSE MIB': 'MIBF',
}

# ==================== FUNÇÃO DE RASPAGEM FUTUROS ====================
@st.cache_data(ttl=55)
def fetch_futures_data():
    """
    Raspa dados de futuros de https://br.investing.com/indices/indices-futures
    e retorna os dados em um dicionário agrupado.
    """
    url = 'https://br.investing.com/indices/indices-futures'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    results = {'EUA': [], 'Ásia-Pacífico': [], 'Europa': []}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status() # Lança exceção para códigos de erro (4xx ou 5xx)
        soup = BeautifulSoup(r.text, 'html.parser')

        # O Investing.com agrupa as tabelas por continente (ou por região na mesma página)
        # Vamos tentar encontrar todas as linhas de dados da tabela principal
        rows = soup.find_all('tr', class_=re.compile(r'datatable-v2_row__hkEus dynamic-table-v2_row__ILVMx'))

        for row in rows:
            try:
                # Extrai o nome do índice
                name_tag = row.find('a', class_='overflow-hidden')
                if not name_tag: continue
                
                # O nome do índice é o texto dentro do <h4>
                name_full = name_tag.find('span', dir='ltr').text.strip()
                
                # Usa o mapeamento para obter o Símbolo curto desejado (ex: Dow Jones -> US30F)
                symbol = FUTURES_MAP.get(name_full, None)
                if not symbol: continue # Ignora se não for um dos índices que queremos

                # Extrai as células (td) relevantes. A estrutura é:
                # [0] (checkbox)
                # [1] Nome
                # [2] Mês
                # [3] Último
                # [4] Máxima
                # [5] Mínima
                # [6] Variação
                # [7] Var. %
                # [8] Hora
                cells = row.find_all('td')
                
                # Último (célula 3)
                last_price_tag = cells[3].find('span') or cells[3]
                last_price = last_price_tag.text.strip()
                
                # Var. % (célula 7)
                change_pct_text = cells[7].text.strip().replace(',', '.').replace('%', '')
                change_pct = float(change_pct_text) if change_pct_text else 0.0

                item = {
                    'Símbolo': symbol,
                    'Último': last_price,
                    'Var. 1D (%)': change_pct
                }
                
                # Classifica o resultado na região correta
                if symbol in ['US30F', 'ESF', 'NDQF', 'RTYF']:
                    results['EUA'].append(item)
                elif symbol in ['CSI300F', 'NK225F', 'HSF', 'NIFTYF', 'ASX200F']:
                    results['Ásia-Pacífico'].append(item)
                elif symbol in ['STX600F', 'DAXF', 'FTSEF', 'CAC40F', 'MIBF']:
                    results['Europa'].append(item)
                    
            except Exception as e:
                 # print(f"Erro ao processar linha de futuro: {e}") 
                 continue # Pula a linha com erro e continua

    except requests.exceptions.RequestException as e:
        # print(f"Erro ao acessar a URL de futuros: {e}")
        pass # Retorna o dicionário vazio se houver erro de requisição
        
    return results

# ==================== FUNÇÃO TURBO CORRIGIDA (100% FUNCIONA) — MANTIDA ====================
def get_single_pair(symbol, name):
    # ... (sua função get_single_pair permanece inalterada) ...
    url = f'https://br.investing.com/currencies/{symbol}-historical-data'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'N/D', '1d Change (%)': 0.0}

        # Regex MELHORADA: pega o bloco JSON da tabela histórica (mais amplo)
        pattern = re.compile(r'(\{"rowDate":[^}]*"last_close"[^}]*"change_precent"[^}]*"change_precentRaw"[^}]*\})', re.DOTALL)
        matches = pattern.findall(r.text)
        
        if matches:
            data = json.loads(matches[0])  # Primeiro match = linha mais recente
            price = data.get('last_close', 'N/D')
            if price and isinstance(price, str):
                price = price.strip().replace(',', '.')  # Limpa formatação BR

            # Usa change_precentRaw (número puro, sem % ou parênteses)
            raw_change = data.get('change_precentRaw')
            if raw_change is not None:
                change_pct = round(float(raw_change), 2)
            else:
                # Fallback: limpa o texto de change_precent
                text_change = data.get('change_precent', '0')
                # Remove parênteses, % e limpa (ex: "(-0,06%)" → -0.06)
                num = re.sub(r'[^\d,.-]', '', text_change).replace(',', '.')
                change_pct = round(float(num or 0), 2)
        else:
            # Fallback: extrai do HEADER (como no seu HTML) se tabela falhar
            soup = BeautifulSoup(r.text, 'html.parser')
            price_elem = soup.find('div', {'data-test': 'instrument-price-last'})
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            
            price = price_elem.text.strip() if price_elem else 'N/D'
            change_text = change_elem.text.strip() if change_elem else '(0,00%)'
            # Limpa % do header (ex: "(-0,06%)" → -0.06)
            num = re.sub(r'[^\d,.-]', '', change_text).replace(',', '.')
            change_pct = round(float(num or 0), 2)

        return {
            'Symbol': symbol.upper().replace('-', '/'),
            'Name': name,
            'Last Price': price,
            '1d Change (%)': change_pct
        }

    except Exception as e:
        # print(f"Erro em {symbol}: {e}")  # Descomente para debug
        return {'Symbol': symbol.upper().replace('-','/'), 'Name': name, 'Last Price': 'Erro', '1d Change (%)': 0.0}


@st.cache_data(ttl=55)
def fetch_all_turbo():
    results = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(get_single_pair, symbol, name): symbol for symbol, name in assets['Forex'].items()}
        for future in as_completed(futures):
            results.append(future.result())
    return results

# ==================== AGRUPAMENTO — MANTIDA ====================
def agrupar_por_base(data):
    # ... (sua função agrupar_por_base permanece inalterada) ...
    grupos = {
        'Dólar Americano': [], 'Euro': [], 'Libra Esterlina': [], 'Iene Japonês': [],
        'Dólar Australiano': [], 'Dólar Neozelandês': [], 'Dólar Canadense': [], 'Franco Suíço': [],
        'Real Brasileiro': [], 'Yuan Chinês': []
    }
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

# ==================== GRÁFICO — MANTIDA ====================
def grafico_forca(data):
    # ... (sua função grafico_forca permanece inalterada) ...
    df = pd.DataFrame(data)
    df['Base'] = df['Symbol'].str.split('/').str[0]
    media = df.groupby('Base')['1d Change (%)'].mean().round(2).sort_values(ascending=False)
    fig = px.bar(media.reset_index(), x='Base', y='1d Change (%)',
                 title='Força Relativa Média (1 dia)',
                 color='1d Change (%)',
                 color_continuous_scale=['red', 'orange', 'yellow', 'lightgreen', 'green'],
                 text='1d Change (%)')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.add_hline(y=0, line_color='white', line_width=2)
    fig.update_layout(height=500, showlegend=False)
    return fig

# Função de estilo para as células de variação
def cor(val):
    color = 'red' if val < 0 else 'green' if val > 0 else 'gray'
    return f'color: {color}; font-weight: bold'

# ==================== LOOP PRINCIPAL — ADICIONANDO FUTUROS ====================
placeholder = st.empty()

while True:
    start_time = time.time()
    with placeholder.container():
        # 1. Busca dados de Forex (em paralelo)
        dados = fetch_all_turbo() 
        
        # 2. Busca dados de Futuros (cacheada e síncrona)
        futuros = fetch_futures_data()
        
        tempo = round(time.time() - start_time, 1)

        st.markdown(f"**Atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} • Carregado em **{tempo}s**")

        # --- TABELAS DE FUTUROS (SEPARADAS) ---
        st.header("📈 Futuros de Índices Globais")
        
        cols_futuros = st.columns(3) # Cria 3 colunas para as regiões

        # Itera sobre as regiões de futuros (EUA, Ásia-Pacífico, Europa)
        for idx, (regiao, lista_futuros) in enumerate(futuros.items()):
            with cols_futuros[idx]:
                if lista_futuros:
                    df_futuros = pd.DataFrame(lista_futuros)
                    
                    # Usa 'Símbolo' como índice e formata a coluna de variação
                    df_futuros.set_index('Símbolo', inplace=True)
                    
                    styled_futuros = df_futuros.style.map(cor, subset=['Var. 1D (%)']) \
                                                     .format({'Var. 1D (%)': '{:.2f}%'})
                    
                    st.markdown(f"**{regiao}**")
                    st.dataframe(styled_futuros, use_container_width=True)
                else:
                    st.markdown(f"**{regiao}**")
                    st.info("Dados de futuros não disponíveis.")
        
        st.markdown("---") # Separador visual

        # --- TABELAS FOREX EXISTENTES ---
        st.header("💱 Pares de Moedas (Forex)")
        grupos = agrupar_por_base(dados)

        cols = st.columns(4)
        for idx, (titulo, lista) in enumerate(grupos.items()):
            with cols[idx % 4]:
                df = pd.DataFrame(lista)[['Symbol', 'Last Price', '1d Change (%)']]
                df.set_index('Symbol', inplace=True)

                styled = df.style.map(cor, subset=['1d Change (%)']) \
                                 .format({'1d Change (%)': '{:.2f}%'})

                st.subheader(titulo)
                st.dataframe(styled, use_container_width=True)

        # GRÁFICO (USA APENAS DADOS DE FOREX)
        st.header("📊 Força Relativa das Moedas")
        st.plotly_chart(grafico_forca(dados), use_container_width=True, key=f"plotly_{int(time.time())}")

        # Download CSV
        # ... (seu código de download CSV permanece aqui) ...
        csv = pd.DataFrame(dados).to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="Baixar todos os dados (CSV)",
            data=csv,
            file_name=f"forex_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )


    time.sleep(60)
