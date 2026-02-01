import streamlit as st
import requests
import time
import json
import os

# Secrets məlumatları
FINNHUB_KEY = st.secrets["FINNHUB_API_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except:
        pass

DB_FILE = "alerts_db.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

st.set_page_config(page_title="Rebound Pro", layout="wide")
st.title("📈 Rebound Strategy Monitor Pro")

if 'alerts' not in st.session_state:
    st.session_state.alerts = load_data()

# Sidebar
with st.sidebar:
    st.header("⚙️ Parametrlər")
    symbol = st.text_input("Aktiv (məs: OANDA:XAG_USD)", "OANDA:XAG_USD").upper()
    trade_type = st.selectbox("İstiqamət", ["SHORT (Müqavimətdən Dönüş)", "LONG (Dəstəkdən Dönüş)"])
    
    label_a = "Müqavimət (A)" if "SHORT" in trade_type else "Dəstək (A)"
    val_a = st.number_input(label_a, format="%.4f")
    val_b = st.number_input("Qırılma Səviyyəsi (B)", format="%.4f")
    
    if st.button("İzləməni Başlat"):
        new_alert = {
            "symbol": symbol, "type": trade_type,
            "val_a": val_a, "val_b": val_b,
            "phase": "WAITING_A", "active": True
        }
        st.session_state.alerts.append(new_alert)
        save_data(st.session_state.alerts)
        st.success("Siyahıya əlavə edildi!")

# Monitoring
st.subheader("📊 Aktiv Siqnallar")
for alert in st.session_state.alerts:
    if alert["active"]:
        resp = requests.get(f"https://finnhub.io/api/v1/quote?symbol={alert['symbol']}&token={FINNHUB_KEY}").json()
        price = resp.get('c', 0)
        
        if price == 0: continue

        # Short/Long Məntiqi
        if "SHORT" in alert["type"]:
            if alert["phase"] == "WAITING_A" and price >= alert["val_a"]:
                alert["phase"] = "WAITING_B"
                save_data(st.session_state.alerts)
                send_telegram_msg(f"🔔 {alert['symbol']} Müqavimətə dəydi! Geri dönüş gözlənilir.")
            elif alert["phase"] == "WAITING_B" and price <= alert["val_b"]:
                alert["phase"] = "TRIGGERED"; alert["active"] = False
                save_data(st.session_state.alerts)
                send_telegram_msg(f"🚨 SHORT SİQNALI: {alert['symbol']} hədəfi qırdı!")
        else:
            if alert["phase"] == "WAITING_A" and price <= alert["val_a"]:
                alert["phase"] = "WAITING_B"
                save_data(st.session_state.alerts)
                send_telegram_msg(f"🔔 {alert['symbol']} Dəstəyə dəydi! Yuxarı dönüş gözlənilir.")
            elif alert["phase"] == "WAITING_B" and price >= alert["val_b"]:
                alert["phase"] = "TRIGGERED"; alert["active"] = False
                save_data(st.session_state.alerts)
                send_telegram_msg(f"🚨 LONG SİQNALI: {alert['symbol']} müqaviməti qırdı!")

        st.write(f"**{alert['symbol']}** ({alert['type']}) | Qiymət: {price:.4f} | Status: {alert['phase']}")
        st.divider()

if st.sidebar.button("🗑️ Bütün İzləmələri Sil"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.session_state.alerts = []
    st.rerun()

time.sleep(60)
st.rerun()
