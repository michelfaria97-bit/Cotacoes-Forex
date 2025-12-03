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

# ===================== CONFIGURAÇÃO =====================
st.set_page_config(
    page_title="Forex + Futuros ao Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="Chart Increasing"
)

st.markdown("""
<style>
    .big-font {font-size: 38px !important; text-align: center; color: #00ff88; font-weight: bold; margin-bottom:0;}
    .time {font-size: 18px; color: #cccccc; text-align: center; margin-top:5px;}
    table {width:100%; border-collapse:collapse; font-size:14px; margin:10px 0;}
    th, td {padding: 10px; text-align: center;}
    th {background:#111; color:white;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">Forex + Futuros Globais • Ao Vivo</p>', unsafe_allow_html=True)

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
    }
}

# ===================== FOREX =====================
def get_pair(symbol):
    url = f"https://br.investing.com/currencies/{symbol}-historical-data"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        m = re.search(r'({"rowDate".*?})', r.text)
        if m:
            d = json.loads(m.group(1))
            price = str(d.get("last_close", "N/D")).replace(",", ".")
            change = float(d.get("change_precentRaw", 0))
        else:
            soup = BeautifulSoup(r.text, "html.parser")
            price_el = soup.select_one("[data-test='instrument-price-last']")
            price = price_el.get_text(strip=True) if price_el else "N/D"
            chg_el = soup.select_one("[data-test='instrument-price-change-percent']")
            txt = chg_el.get_text(strip=True) if chg_el else "0%"
            change = float(re.sub(r"[^\d.-]", "", txt.replace(",", ".")) or 0)
        return {"Symbol": symbol.upper().replace("-", "/"), "Price": price, "Change": round(change, 2)}
    except:
        return {"Symbol": symbol.upper().replace("-", "/"), "Price": "—", "Change": 0.0}

@st.cache_data(ttl=55)
def fetch_forex():
    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = [ex.submit(get_pair, s) for s in assets['Forex']]
        return [f.result() for f in as_completed(futures)]

# ===================== FUTUROS CORRETOS (EUA na tabela certa) =====================
@st.cache_data(ttl=55)
def fetch_futures():
    headers = {"User-Agent": "Mozilla/5.0"}
    dados = {"EUA": [], "Ásia-Pacífico": [], "Europa": []}
    já_exibido = set()

    # === TABELA DOS EUA (atraso 10 min) ===
    url_eua = "https://br.investing.com/indices/indices-futures"
    try:
        soup = BeautifulSoup(requests.get(url_eua, headers=headers, timeout=15).text, "html.parser")
        for row in soup.select("table.datatable-v2_table__93S4Y tbody tr"):
            tds = row.find_all("td")
            if len(tds) < 8: continue
            nome = row.find("a")
            if not nome: continue
            nome = nome.get_text(strip=True)

            mapa_eua = {
                "Dow Jones": "US30", "S&P 500": "SPX500", "Nasdaq 100": "NAS100", "Russell 2000": "RUS2000"
            }
            simbolo = next((v for k,v in mapa_eua.items() if k in nome), None)
            if not simbolo or simbolo in já_exibido: continue
            já_exibido.add(simbolo)

            ultimo = tds[3].get_text(strip=True)
            var = tds[7].get_text(strip=True).replace("%","").replace("(","").replace(")","").strip()
            try: var = round(float(var.replace(",", ".")), 2)
            except: var = 0.0

            dados["EUA"].append((simbolo, ultimo, var))
    except: pass

    # === TABELA GLOBAL (Ásia e Europa) ===
    try:
        soup = BeautifulSoup(requests.get(url_eua, headers=headers, timeout=15).text, "html.parser")
        for row in soup.select("table.datatable-v2_table__93S4Y + table tbody tr"):
            tds = row.find_all("td")
            if len(tds) < 8: continue
            nome_tag = row.find("a")
            if not nome_tag: continue
            nome = nome_tag.get_text(strip=True)

            mapa_global = {
                "Nikkei 225": "JPN225", "Hang Seng": "HK50", "Shanghai": "CHINA50",
                "ASX 200": "AUS200", "Nifty 50": "IND50", "DAX": "GER40",
                "FTSE 100": "UK100", "CAC 40": "FRA40", "Euro Stoxx 50": "EU50",
                "IBEX 35": "ESP35", "FTSE MIB": "ITA40"
            }
            simbolo = next((v for k,v in mapa_global.items() if k.lower() in nome.lower()), None)
            if not simbolo or simbolo in já_exibido: continue
            já_exibido.add(simbolo)

            ultimo = tds[3].get_text(strip=True)
            var_txt = tds[7].get_text(strip=True).replace("%","").replace("(","").replace(")","").strip()
            try: var = round(float(var_txt.replace(",", ".")), 2)
            except: var = 0.0

            if simbolo in ["JPN225","HK50","CHINA50","AUS200","IND50"]:
                dados["Ásia-Pacífico"].append((simbolo, ultimo, var))
            else:
                dados["Europa"].append((simbolo, ultimo, var))
    except: pass

    return dados

# ===================== LOOP PRINCIPAL =====================
placeholder = st.empty()
while True:
    start = time.time()
    with placeholder.container():
        forex = fetch_forex()
        futuros = fetch_futures()

        st.markdown(f'<p class="time">Atualizado: {datetime.now():%d/%m/%Y %H:%M:%S} • Tempo: {time.time()-start:.1f}s</p>', 
                    unsafe_allow_html=True)

        # === FUTUROS ===
        st.markdown("### Futuros de Índices Globais")
        c1, c2, c3 = st.columns(3)
        for col, regiao in zip([c1,c2,c3], ["EUA", "Ásia-Pacífico", "Europa"]):
            with col:
                st.markdown(f"**{regiao}**")
                lista = futuros.get(regiao, [])
                if not lista:
                    st.info("Sem dados")
                    continue
                html = "<table><tr><th>Símbolo</th><th>Último</th><th>Var %</th></tr>"
                for simb, ult, var in lista:
                    cor = "green" if var > 0 else "red" if var < 0 else ""
                    html += f"<tr><td>{simb}</td><td>{ult}</td><td class='{cor}'>{var:+.2f}%</td></tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")

        # === FOREX ===
        st.markdown("### Pares Forex")
        grupos = {}
        for item in forex:
            base = item["Symbol"].split("/")[0]
            grupos.setdefault(base, []).append(item)

        cols = st.columns(4)
        for i, (moeda, lista) in enumerate(sorted(grupos.items())):
            with cols[i%4]:
                st.subheader(moeda)
                df = pd.DataFrame(lista).set_index("Symbol")[["Price", "Change"]]
                def cor(v): 
                    try: return "color:#00ff88;font-weight:bold" if float(v)>0 else "color:#ff4444;font-weight:bold"
                    except: return ""
                styled = df.style.applymap(cor, subset=["Change"]).format({"Change": "{:+.2f}%"})
                st.dataframe(styled, use_container_width=True)

        # === GRÁFICO FORÇA ===
        st.markdown("### Força Relativa das Moedas (24h)")
        dfg = pd.DataFrame(forex)
        dfg["Moeda"] = dfg["Symbol"].str.split("/").str[0]
        media = dfg.groupby("Moeda")["Change"].mean().round(2).sort_values(ascending=False)
        fig = px.bar(media.reset_index(), x="Moeda", y="Change", color="Change",
                     color_continuous_scale=["#ff4444","#ff8800","#ffff00","#88ff88","#00ff88"],
                     text="Change", height=500)
        fig.update_traces(texttemplate="%{text:+.2f}%", textposition="outside")
        fig.add_hline(y=0, line_color="gray", line_width=2)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)

        # === DOWNLOAD ===
        csv = pd.DataFrame(forex).to_csv(index=False, encoding="utf-8-sig")
        st.download_button("Baixar Forex (CSV)", csv, f"forex_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv")

    time.sleep(60)
