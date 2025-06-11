import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import numpy as np

# Configuration de l'API Twelve Data
API_KEY = "YOUR_TWELVE_DATA_API_KEY"  # Remplace par ta clé API Twelve Data
BASE_URL = "https://api.twelvedata.com"

# Liste des paires forex à scanner
FOREX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD",
    "USD/CHF", "NZD/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP"
]

# Fonction pour récupérer les données OHLCV et indicateurs
@st.cache_data(ttl=60)
def fetch_technical_data(symbol, interval="1h", outputsize=50):
    try:
        # Récupérer les données OHLC
        url = f"{BASE_URL}/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={API_KEY}"
        response = requests.get(url).json()
        if "values" not in response:
            return None
        df = pd.DataFrame(response["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        df = df[::-1].reset_index(drop=True)  # Inverser pour avoir les données récentes en dernier

        # Calculer ADX
        adx_url = f"{BASE_URL}/adx?symbol={symbol}&interval={interval}&time_period=14&apikey={API_KEY}"
        adx_data = requests.get(adx_url).json()
        df["adx"] = [float(x["adx"]) for x in adx_data["values"][:len(df)]][::-1]

        # Calculer ATR
        atr_url = f"{BASE_URL}/atr?symbol={symbol}&interval={interval}&time_period=14&apikey={API_KEY}"
        atr_data = requests.get(atr_url).json()
        df["atr"] = [float(x["atr"]) for x in atr_data["values"][:len(df)]][::-1]

        # Calculer RSI
        rsi_url = f"{BASE_URL}/rsi?symbol={symbol}&interval={interval}&time_period=14&apikey={API_KEY}"
        rsi_data = requests.get(rsi_url).json()
        df["rsi"] = [float(x["rsi"]) for x in rsi_data["values"][:len(df)]][::-1]

        return df
    except Exception as e:
        st.error(f"Erreur pour {symbol}: {e}")
        return None

# Fonction pour détecter les cassures
def detect_breakout(df, lookback=20):
    recent_high = df["high"].iloc[-lookback:-1].max()
    recent_low = df["low"].iloc[-lookback:-1].min()
    current_close = df["close"].iloc[-1]
    if current_close > recent_high:
        return "Acheter"
    elif current_close < recent_low:
        return "Vendre"
    return "Neutre"

# Interface Streamlit
st.title("Screener Forex Puissant")
st.subheader("Analyse des signaux forts pour mouvements directionnels rapides")

# Filtres personnalisables
st.sidebar.header("Filtres")
adx_threshold = st.sidebar.slider("ADX Minimum", 10, 50, 25)
rsi_min = st.sidebar.slider("RSI Minimum", 30, 70, 50)
rsi_max = st.sidebar.slider("RSI Maximum", 30, 70, 70)
atr_multiplier = st.sidebar.slider("ATR Multiplicateur (par rapport à la moyenne)", 1.0, 3.0, 1.5)
interval = st.sidebar.selectbox("Time Frame", ["1h", "4h", "1day"], index=0)

# Bouton pour lancer le scan
if st.button("Lancer le Scan"):
    results = []
    progress_bar = st.progress(0)
    for i, pair in enumerate(FOREX_PAIRS):
        df = fetch_technical_data(pair, interval)
        if df is not None:
            # Calculer la moyenne ATR
            atr_avg = df["atr"].rolling(window=20).mean().iloc[-1]
            current_atr = df["atr"].iloc[-1]
            current_adx = df["adx"].iloc[-1]
            current_rsi = df["rsi"].iloc[-1]
            breakout_signal = detect_breakout(df)

            # Vérifier les conditions
            if (current_adx >= adx_threshold and
                rsi_min <= current_rsi <= rsi_max and
                current_atr >= atr_multiplier * atr_avg):
                results.append({
                    "Paire": pair,
                    "ADX": round(current_adx, 2),
                    "ATR": round(current_atr, 4),
                    "ATR Moyenne": round(atr_avg, 4),
                    "RSI": round(current_rsi, 2),
                    "Signal": breakout_signal,
                    "Dernier Prix": round(df["close"].iloc[-1], 5)
                })
        progress_bar.progress((i + 1) / len(FOREX_PAIRS))

    # Afficher les résultats
    if results:
        results_df = pd.DataFrame(results)
        st.subheader("Paires avec signaux forts")
        st.dataframe(results_df)

        # Visualisation pour une paire sélectionnée
        selected_pair = st.selectbox("Sélectionner une paire pour le graphique", results_df["Paire"])
        df = fetch_technical_data(selected_pair, interval)
        if df is not None:
            fig = px.line(df, x="datetime", y="close", title=f"Prix de {selected_pair} ({interval})")
            st.plotly_chart(fig)
    else:
        st.warning("Aucune paire ne répond aux critères.")

# Footer
st.markdown("---")
st.write(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write("Powered by Twelve Data API & Streamlit")
