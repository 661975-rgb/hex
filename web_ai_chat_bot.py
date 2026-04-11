import os
import sys
import subprocess

# ==========================================
# 0. 魔法啟動器 & 雲端環境全自動配置
# ==========================================
if not "streamlit" in sys.modules and __name__ == "__main__":
    print("🔍 [系統預檢] 正在檢查環境與雲端配置...")
    
    # 【神級防呆】自動生成雲端部署必備的 requirements.txt
    base_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(base_dir, "requirements.txt")
    if not os.path.exists(req_file):
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("streamlit\nyfinance\nplotly\ngoogle-genai\npandas\n")
        print("📄 [雲端準備] 已自動為您生成 requirements.txt")

    try:
        import streamlit
        import yfinance
        import plotly
        from google import genai
    except ImportError:
        print("📦 [下載套件] 偵測到缺少套件，自動背景安裝中...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"])

    print("🚀 [啟動 Web 引擎] 正在架設對話式戰情室伺服器...")
    subprocess.check_call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

# ==========================================
# 以下為 Streamlit Web 應用程式本體
# ==========================================
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from google import genai
import pandas as pd

st.set_page_config(page_title="AI 雙向對話戰情室", page_icon="💬", layout="wide")

# --- 1. 🔐 密碼防護系統 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 企業機密戰情室 - 身份驗證")
    pwd_input = st.text_input("🔑 請輸入主管通關密碼", type="password")
    if st.button("解鎖進入", type="primary"):
        if pwd_input == "boss888":
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("密碼錯誤！")
    st.stop()

# --- 2. 🧠 初始化聊天記憶體 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "總監您好！我是您的 AI 投資顧問。我已準備好分析即時市場數據，您可以直接詢問我關於盤勢的看法。"}
    ]

# --- 3. 核心功能函式 (支援雲端與本機雙模式) ---
def get_api_key():
    # 優先嘗試抓取雲端保險箱 (st.secrets)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except:
        pass
        
    # 如果是本機運行，則抓取 KEY.TXT
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(base_dir, "KEY.TXT")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    st.error("❌ 找不到金鑰！請在雲端後台設定 Secrets 或在本機建立 KEY.TXT")
    st.stop()

@st.cache_data 
def load_data(ticker, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df.reset_index(inplace=True)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    return stock.info, df

# 【備援機制】：遇到 429 塞車，自動切換線路
def get_ai_response(client, api_messages, system_instruction):
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=api_messages,
                config={"system_instruction": system_instruction}
            )
            return response.text, model_name
        except Exception as e:
            if "429" in str(e) or "exhausted" in str(e).lower():
                st.toast(f"⚠️ {model_name} 線路滿載，自動切換備援線路...")
                continue 
            else:
                raise e 
    raise Exception("目前所有 AI 伺服器線路皆已滿載 (429)，請休息一分鐘後再試！")

# --- 4. 側邊欄與圖表展示 ---
st.title("💬 AI 雙向對話戰情室")

with st.sidebar:
    st.header("🎛️ 系統控制")
    ticker = st.text_input("股票代號", "2330.TW")
    period = st.selectbox("資料區間", ["1mo", "3mo", "6mo", "1y"], index=1)
    if st.button("🚪 登出系統"):
        st.session_state['logged_in'] = False; st.rerun()

info, df = load_data(ticker, period)
fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template='plotly_dark', margin=dict(l=0, r=0, t=0, b=0), height=400)
st.plotly_chart(fig, use_container_width=True)

# --- 5. 🗨️ 聊天介面區 ---
st.subheader("🤖 與 AI 顧問對話")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("詢問 AI 顧問 (例如：這檔股票現在適合進場嗎？)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("啟動多重伺服器連線中..."):
            try:
                client = genai.Client(api_key=get_api_key())
                recent_summary = df.tail(5)[['Date', 'Close', 'Volume']].to_string(index=False)
                system_instruction = f"你是資深分析師。目前分析標的為 {ticker}。近期數據：\n{recent_summary}\n請根據數據與對話歷史回答。"
                
                ai_messages = []
                for m in st.session_state.messages:
                    api_role = "model" if m["role"] == "assistant" else "user"
                    ai_messages.append({"role": api_role, "parts": [{"text": m["content"]}]})
                
                full_response, used_model = get_ai_response(client, ai_messages, system_instruction)
                
                st.markdown(full_response)
                st.caption(f"*(本次回覆由 {used_model} 備援引擎提供)*")
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"連線失敗：{e}")