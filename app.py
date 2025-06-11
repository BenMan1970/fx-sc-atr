import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# Configuration de l'API Alpha Vantage
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "FALLBACK_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

# Paires forex réduites pour tests
FOREX_PAIRS = ["EUR/USD", "GBP/USD"]

# Fonction pour récupérer les données OHLC
def fetch_ohlc_data(symbol, interval="60min"):
    st.write(f"[DEBUG] Début de fetch_ohlc_data pour {symbol}")
    try:
        from_symbol, to_symbol = symbol.split("/")
        url = f"{BASE_URL}?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval={interval}&apikey={API_KEY}"
        st.write(f"[DEBUG] URL: {url}")
        response = requests.get(url, timeout=5).json()
        st.write(f"[DEBUG] Réponse API: {response}")
        if "Time Series FX (60min)" not in response:
            st.warning(f"Erreur pour {symbol}: {response.get('Note', 'Erreur API')}")
            return None
        data = response["Time Series FX (60min)"]
        df = pd.DataFrame.from_dict(data, orient="index")
        df = df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close"})
        df["datetime"] = pd.to_datetime(df.index)
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df = df.reset_index(drop=True)
        st.write(f"[DEBUG] Données traitées pour {symbol}: {len(df)} lignes")
        return df
    except Exception as e:
        st.error(f"[DEBUG] Erreur pour {symbol}: {str(e)}")
        return None

# Interface Streamlit
st.title("Screener Forex - Alpha Vantage")
st.subheader("Test de connexion à l'API Alpha Vantage")
st.write(f"[DEBUG] Clé API: {'***' + API_KEY[-4:] if API_KEY else 'Non définie'}")

# Bouton pour lancer le test
if st.button("Tester les paires"):
    st.write("[DEBUG] Début du scan")
    results = []
    progress_bar = st.progress(0)
    for i, pair in enumerate(FOREX_PAIRS):
        st.write(f"[DEBUG] Traitement de {pair}")
        df = fetch_ohlc_data(pair)
        if df is not None:
            results.append({
                "Paire": pair,
                "Dernier Prix": round(df["close"].iloc[-1], 5),
                "Statut": "Succès"
            })
        else:
            results.append({
                "Paire": pair,
                "Dernier Prix": None,
                "Statut": "Échec"
            })
        progress_bar.progress((i + 1) / len(FOREX_PAIRS))

    # Afficher les résultats
    if results:
        st.write("[DEBUG] Résultats obtenus")
        results_df = pd.DataFrame(results)
        st.subheader("Résultats du test")
        st.dataframe(results_df)
    else:
        st.error("[DEBUG] Aucun résultat obtenu")

# Footer
st.markdown("---")
st.write(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write("Powered by Alpha Vantage & Streamlit")
