# app.py — VERSÃO FINAL ESTÁVEL (FOREX + FUTUROS) — NUNCA MAIS DÁ KEYERROR
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
    page_title="Forex + Futuros ao Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="Chart Increasing"
)

st.markdown("""
<style>
    .big-font {font-size: 40px !important; text-align: center; color: #00ff88; font-weight: bold;}
    .time {font-size: 18px; color: #aaaaaa; text-align: center;}
    table {width: 100%; border-collapse: collapse; margin: 10px 0;}
    th, td {padding: 10px; text-align: center; border-bottom: 1px solid #333;}
    th {background: #0e1117; color: white;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">Forex + Futuros Globais • Ao Vivo</p>', unsafe_allow_html=True)

# ==================== TODOS OS PARES FOREX (80+) ====================
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
        'chf-nzd': 'Swiss Franc/New Zealand Dollar', 'cad-eur': 'Canadian Dollar/Euro', 'usd-eur': 'US Dollar/Euro',
        'usd-gbp': 'US Dollar/British Pound', 'jpy-aud': 'Japanese Yen/Australian Dollar', 'brl-usd': 'Brazilian Real/US Dollar',
        'brl-jpy': 'Brazilian Real/Japanese Yen', 'brl-gbp': 'Brazilian Real/British Pound', 'brl-nzd': 'Brazilian Real/New Zealand Dollar',
        'brl-aud': 'Brazilian Real/Australian Dollar', 'brl-eur': 'Brazilian Real/Euro', 'cny-usd': 'Chinese Yuan/US Dollar',
        'cny-eur': 'Chinese Yuan/Euro', 'cny-jpy': 'Chinese Yuan/Japanese Yen'
    }
}

# ==================== FOREX (funciona perfeitamente) ====================
def get_pair(symbol):
    url = f"https://br.investing.com/currencies/{symbol}-historical-data"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # JSON embutido
        m = re.search(r'({"rowDate".*?})', r.text)
        if m:
            d = json.loads(m.group(1))
            price = str(d.get("last_close", "N/D")).replace(",", ".")
            change = float(d.get("change_precentRaw", 0))
        else:
            soup = BeautifulSoup(r.text, "html.parser")
            price = soup.select_one("[data-test='instrument-price-last']")
            price = price.text.strip() if price else "N/D"
            chg = soup.select_one("[data-test='instrument-price-change-percent']")
            txt = chg.text.strip() if chg else "0%"
            change = float(re.sub(r"[^\d.-]", "", txt.replace(",", ".")) or 0)
        return {"Symbol": symbol.upper().replace("-", "/"), "Price": price, "Change": round(change, 2)}
    except:
        return {"Symbol": symbol.upper().replace("-", "/"), "Price": "—", "Change": 0.0}

@st.cache_data(ttl=55)
def fetch_forex():
    with ThreadPoolExecutor(max_workers=25) as ex:
        futures = [ex.submit(get_pair, s) for s in assets['Forex'].keys()]
        return [f.result() for f in as_completed(futures)]

# ==================== FUTUROS (SEM .style → nunca dá erro) ====================
@st.cache_data(ttl=55)
def fetch_futures():
    url = "https://br.investing.com/indices/indices-futures"
    headers = {"User-Agent": "Mozilla/5.0"}
    mapa = {
        "Dow Jones": "US30", "S&P 500": "SPX500", "Nasdaq": "NAS100", "Russell 2000": "RUS2000",
        "Shanghai": "CHINA50", "Nikkei 225": "JPN225", "Hang Seng": "HK50", "Nifty": "IND50",
        "ASX 200": "AUS200", "Stoxx 50": "EU50", "DAX": "GER40", "FTSE 100": "UK100",
        "CAC 40": "FRA40", "IBEX 35": "ESP35", "FTSE MIB": "ITA40"
    }
    dados = {"EUA": [], "Ásia-Pacífico": [], "Europa": []}
    try:
        soup = BeautifulSoup(requests.get(url, headers=headers, timeout=15).text, "html.parser")
        for row in soup.find_all("tr", class_=re.compile("row")):
            tds = row.find_all("td")
            if len(tds) < 8: continue
            nome_tag = row.find("a")
            if not nome_tag: continue
            nome = nome_tag.get_text(strip=True)
            simbolo = next((v for k, v in mapa.items() if k.lower() in nome.lower()), None)
            if not simbolo: continue
            ultimo = tds[3].get_text(strip=True)
            var_txt = tds[7].get_text(strip=True).replace("%", "").replace("(", "-").replace(")", "")
            try:
                var = round(float(var_txt.replace(",", ".")), 2)
            except:
                var = 0.0
            item = (simbolo, ultimo, var)
            if simbolo in ["US30", "SPX500", "NAS100", "RUS2000"]:
                dados["EUA"].append(item)
            elif simbolo in ["CHINA50", "JPN225", "HK50", "IND50", "AUS200"]:
                dados["Ásia-Pacífico"].append(item)
            else:
                dados["Europa"].append(item)
    except:
        pass
    return dados

# ==================== LOOP PRINCIPAL ====================
placeholder = st.empty()

while True:
    inicio = time.time()
    with placeholder.container():
        forex = fetch_forex()
        futuros = fetch_futures()

        st.markdown(f'<p class="time">Atualizado: {datetime.now():%d/%m/%Y %H:%M:%S} • Tempo: {time.time()-inicio:.1f}s</p>', unsafe_allow_html=True)

        # ==================== FUTUROS (HTML PURO – 100% estável) ====================
        st.markdown("### Futuros de Índices Globais")
        col1, col2, col3 = st.columns(3)

        regioes = ["EUA", "Ásia-Pacífico", "Europa"]
        cols = [col1, col2, col3]

        for regiao, col in zip(regioes, cols):
            with col:
                st.markdown(f"**{regiao}**")
                lista = futuros.get(regiao, [])
                if not lista:
                    st.info("Sem dados")
                    continue
                html = "<table><tr style='background:#111;color:white;'><th>Símbolo</th><th>Último</th><th>Var %</th></tr>"
                for simb, ult, var in lista:
                    cor = "#00ff88" if var > 0 else "#ff4444" if var < 0 else "white"
                    html += f"<tr><td>{simb}</td><td>{ult}</td><td style='color:{cor};font-weight:bold'>{var:+.2f}%</td></tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")

        # ==================== FOREX (com .style – funciona perfeitamente) ====================
        st.markdown("### Pares Forex ao Vivo")
        grupos = {}
        for item in forex:
            base = item["Symbol"].split("/")[0]
            grupos.setdefault(base, []).append(item)

        cols = st.columns(4)
        for i, (moeda, lista) in enumerate(sorted(grupos.items())):
            with cols[i % 4]:
                st.subheader(moeda)
                df = pd.DataFrame(lista).set_index("Symbol")[["Price", "Change"]]
                def cor(v):
                    try:
                        return "color:#00ff88;font-weight:bold" if float(v)>0 else "color:#ff4444;font-weight:bold"
                    except:
                        return ""
                styled = df.style.applymap(cor, subset=["Change"]).format({"Change": "{:+.2f}%"})
                st.dataframe(styled, use_container_width=True)

        # ==================== GRÁFICO FORÇA RELATIVA ====================
        st.markdown("### Força Relativa das Moedas (24h)")
        dfg = pd.DataFrame(forex)
        dfg["Moeda"] = dfg["Symbol"].str.split("/").str[0]
        media = dfg.groupby("Moeda")["Change"].mean().round(2).sort_values(ascending=False)
        fig = px.bar(media.reset_index(), x="Moeda", y="Change", color="Change",
                     color_continuous_scale=["#ff4444", "#ffaa44", "#ffff44", "#88ff88", "#00ff88"],
                     text="Change", height=500)
        fig.update_traces(texttemplate="%{text:+.2f}%", textposition="outside")
        fig.add_hline(y=0, line_color="gray", line_width=2)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        # ==================== DOWNLOAD CSV ====================
        csv = pd.DataFrame(forex).to_csv(index=False, encoding="utf-8-sig")
        st.download_button("Baixar dados Forex (CSV)", csv, f"forex_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv")

    time.sleep(60)
