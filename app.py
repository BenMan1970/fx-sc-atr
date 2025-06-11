import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
import plotly.express as px

# Configuration de l'API Alpha Vantage
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "FALLBACK_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

# Paires forex pour le screener
FOREX_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# Fonction pour récupérer les données OHLC
def fetch_ohlc_data(symbol, interval="daily"):
    st.write(f"[DEBUG] Début de fetch_ohlc_data pour {symbol}")
    try:
        from_symbol, to_symbol = symbol.split("/")
        url = f"{BASE_URL}?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&apikey={API_KEY}"
        st.write(f"[DEBUG] URL: {url}")
        response = requests.get(url, timeout=5).json()
        st.write(f"[DEBUG] Réponse API: {response.get('Meta Data', 'No Meta Data')}")
        if "Time Series FX (Daily)" not in response:
            st.warning(f"Erreur pour {symbol}: {response.get('Note', 'Erreur API')}")
            return None
        data = response["Time Series FX (Daily)"]
        df = pd.DataFrame.from_dict(data, orient="index")
        df = df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close"})
        df["datetime"] = pd.to_datetime(df.index)
        df = df[["datetime", "open", "high", "low", "close"]]
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df = df.reset_index(drop=True)
        st.write(f"[DEBUG] Données traitées pour {symbol}: {len(df)} lignes")
        return df
    except Exception as e:
        st.error(f"[DEBUG] Erreur pour {symbol}: {str(e)}")
        return None

# Fonction pour détecter les cassures
def detect_breakout(df, lookback=20):
    if df is None or len(df) < lookback:
        return "Neutre"
    recent_high = df["high"].iloc[-lookback:-1].max()
    recent_low = df["low"].iloc[-lookback:-1].min()
    current_close = df["close"].iloc[-1]
    if current_close > recent_high:
        return "Acheter"
    elif current_close < recent_low:
        return "Vendre"
    return "Neutre"

# Interface Streamlit
st.title("Screener Forex - Alpha Vantage")
st.subheader("Analyse des signaux sur données journalières")
st.write(f"[DEBUG] Clé API: {'***' + API_KEY[-4:] if API_KEY else 'Non définie'}")

# Filtres personnalisables
st.sidebar.header("Filtres")
price_change_threshold = st.sidebar.slider("Changement de prix minimum (%)", 0.0, 5.0, 1.0)
lookback_period = st.sidebar.slider("Période de lookback (jours)", 5, 50, 20)

# Bouton pour lancer le scan
if st.button("Lancer le Scan"):
    st.write("[DEBUG] Début du scan")
    results = []
    progress_bar = st.progress(0)
    for i, pair in enumerate(FOREX_PAIRS):
        st.write(f"[DEBUG] Traitement de {pair}")
        df = fetch_ohlc_data(pair)
        if df is not None:
            # Calculer le changement de prix (en %)
            price_change = ((df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]) * 100
            breakout_signal = detect_breakout(df, lookback_period)
            # Appliquer les filtres
            if abs(price_change) >= price_change_threshold:
                results.append({
                    "Paire": pair,
                    "Dernier Prix": round(df["close"].iloc[-1], 5),
                    "Changement (%)": round(price_change, 2),
                    "Signal": breakout_signal,
                    "Statut": "Succès"
                })
        else:
            results.append({
                "Paire": pair,
                "Dernier Prix": None,
                "Changement (%)": None,
                "Signal": "Aucun",
                "Statut": "Échec"
            })
        progress_bar.progress((i + 1) / len(FOREX_PAIRS))

    # Afficher les résultats
    if results:
        st.write("[DEBUG] Résultats obtenus")
        results_df = pd.DataFrame(results)
        st.subheader("Résultats du screener")
        st.dataframe(results_df)

        # Visualisation pour une paire sélectionnée
        selected_pair = st.selectbox("Sélectionner une paire pour le graphique", results_df["Paire"])
        df = fetch_ohlc_data(selected_pair)
        if df is not None:
            fig = px.line(df, x="datetime", y="close", title=f"Prix de {selected_pair} (Journalier)")
            st.plotly_chart(fig)
    else:
        st.error("[DEBUG] Aucun résultat obtenu")

# Footer
st.markdown("---")
st.write(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write("Powered by Alpha Vantage & Streamlit")
