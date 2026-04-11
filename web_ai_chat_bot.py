import os
import sys
import subprocess
import logging
from typing import Tuple, List, Dict, Any

# ==========================================
# 0. 魔法啟動器 & 雲端/本機環境全自動配置
# ==========================================
if not "streamlit" in sys.modules and __name__ == "__main__":
    print("🔍 [系統預檢] 正在檢查環境與雲端配置...")
    
    # 自動生成 requirements.txt (新增 tenacity 用於進階容錯)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(base_dir, "requirements.txt")
    if not os.path.exists(req_file):
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("streamlit\nyfinance\nplotly\ngoogle-genai\npandas\ntenacity\n")
        print("📄 [雲端準備] 已自動為您生成 requirements.txt")

    try:
        import streamlit
        import yfinance
        import plotly
        import pandas
        import tenacity
        from google import genai
    except ImportError:
        print("📦 [下載套件] 偵測到缺少核心套件，自動背景安裝中...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"])

    print("🚀 [啟動 Web 引擎] 正在架設對話式戰情室伺服器...")
    subprocess.check_call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

# ==========================================
# 1. 核心套件載入與全域設定
# ==========================================
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 設定 Log 層級以利未來除錯
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="AI 雙向對話戰情室 Pro", page_icon="📈", layout="wide")

# ==========================================
# 2. 🔐 身份驗證與記憶體初始化
# ==========================================
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
            st.error("❌ 密碼錯誤，請重新輸入！")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "總監您好！我是您的 AI 投資顧問。系統已掛載**即時聯網搜尋**與**自動容錯切換**模組，請問今日想分析哪檔標的？"}
    ]

# ==========================================
# 3. 核心系統函式 (Type Hints & 例外處理)
# ==========================================
def get_api_key() -> str:
    """自動偵測並提取 API Key (支援 Streamlit Secrets 與本機 KEY.TXT)"""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_file = os.path.join(base_dir, "KEY.TXT")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    
    st.error("❌ 系統異常：找不到 Google Gemini API 金鑰！請在雲端後台設定 Secrets 或在本機建立 KEY.TXT")
    st.stop()

@st.cache_data(ttl=3600)
def load_and_compress_data(ticker: str, period: str) -> Tuple[dict, pd.DataFrame, str]:
    """
    載入股市資料並進行 Token 最佳化降維處理。
    將長天期資料轉換為月均線摘要，保留近5日精確資料。
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return {}, pd.DataFrame(), "無法獲取股票資料，請確認代號是否正確。"
            
        df.reset_index(inplace=True)
        # 轉換時區以避免 JSON 序列化錯誤
        if pd.api.types.is_datetime64tz_dtype(df['Date']):
            df['Date'] = df['Date'].dt.tz_localize(None)
        
        # --- 數據降維處理 (Token 成本控制) ---
        # 1. 提取最近 5 天的詳細資料
        recent_5_days = df.tail(5)[['Date', 'Close', 'Volume']].copy()
        recent_5_days['Date'] = recent_5_days['Date'].dt.strftime('%Y-%m-%d')
        recent_str = recent_5_days.to_string(index=False)
        
        # 2. 如果資料超過一個月，進行月度重採樣以壓縮 Prompt
        if len(df) > 30:
            df.set_index('Date', inplace=True)
            monthly_summary = df.resample('ME').agg({'Close': 'mean', 'Volume': 'mean'}).round(2)
            monthly_summary.index = monthly_summary.index.strftime('%Y-%m')
            monthly_summary.reset_index(inplace=True)
            monthly_str = monthly_summary.tail(6).to_string(index=False) # 取近半年月度趨勢
            df.reset_index(inplace=True)
            
            compressed_data_str = f"【近半年月均趨勢】\n{monthly_str}\n\n【近5日詳細數據】\n{recent_str}"
        else:
            compressed_data_str = f"【近期詳細數據】\n{recent_str}"
            
        return stock.info, df, compressed_data_str
    except Exception as e:
        logger.error(f"資料載入失敗: {e}")
        return {}, pd.DataFrame(), f"資料載入發生錯誤: {str(e)}"

# 定義指數退避重試邏輯，專門攔截 API 塞車錯誤
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def fetch_from_gemini(client: genai.Client, model_name: str, contents: list, config: types.GenerateContentConfig) -> str:
    """發送 API 請求，若遇到暫時性錯誤會自動等待並重試"""
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config
    )
    return response.text

def get_ai_response_with_fallback(client: genai.Client, api_messages: list, system_instruction: str, allow_search: bool) -> Tuple[str, str]:
    """多模型備援切換機制，結合 Google Search 工具與重試邏輯"""
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    
    # 動態配置：是否開啟 Google Search 工具
    tools = [{"google_search": {}}] if allow_search else None
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.4, # 降低隨機性，提高財務分析準確度
        tools=tools
    )

    for model_name in models:
        try:
            logger.info(f"嘗試連線至模型: {model_name}")
            response_text = fetch_from_gemini(client, model_name, api_messages, config)
            return response_text, model_name
            
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "overloaded" in error_msg:
                st.toast(f"⚠️ {model_name} 負載過高，自動切換備援引擎...")
                continue # 嘗試下一個模型
            else:
                # 若為其他嚴重錯誤（如 Key 無效），直接拋出
                raise e 
                
    raise Exception("❌ 所有 AI 伺服器線路皆已滿載或異常，請稍後再試！")

# ==========================================
# 4. 網頁 UI 與視覺化圖表
# ==========================================
with st.sidebar:
    st.header("🎛️ 戰術控制面板")
    ticker = st.text_input("📈 股票代號 (如: 2330.TW, AAPL)", "2330.TW")
    period = st.selectbox("📅 資料區間", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
    allow_search = st.toggle("🌐 允許 AI 即時聯網搜尋", value=True, help="開啟後 AI 可主動搜尋最新新聞與未來年份預測，但回應速度會稍慢。")
    
    st.divider()
    if st.button("🚪 安全登出系統", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state.messages = []
        st.rerun()

# 載入並處理資料
info, df, compressed_data = load_and_compress_data(ticker, period)

if not df.empty:
    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00ff00', decreasing_line_color='#ff0000'
    )])
    fig.update_layout(
        title=f"{ticker} 走勢圖", template='plotly_dark', 
        margin=dict(l=20, r=20, t=40, b=20), height=400
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("目前無圖表資料可顯示。")

# ==========================================
# 5. 🗨️ 智慧對話核心迴圈
# ==========================================
st.subheader("🤖 投資戰略顧問 (具備聯網與降維分析能力)")

# 顯示歷史對話
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 接收使用者輸入
if prompt := st.chat_input("詢問 AI 顧問 (例如：幫我搜尋 2025 年這檔股票的資本支出預測？)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("啟動多重伺服器連線與深度檢索中..."):
            try:
                # 建立客戶端
                client = genai.Client(api_key=get_api_key())
                
                # 建構系統提示詞 (注入壓縮後的數據)
                system_instruction = (
                    f"你是一位頂尖的資深金融分析師。目前分析標的為 {ticker}。\n"
                    f"以下為系統處理過的近期數據摘要：\n{compressed_data}\n"
                    f"請以專業、客觀的角度回答使用者問題。若使用者詢問未來的資料或未提供的資訊，請善用你的搜尋能力。"
                )
                
                # 轉換訊息格式以符合新版 SDK 要求
                api_messages = []
                for m in st.session_state.messages:
                    role = "user" if m["role"] == "user" else "model"
                    api_messages.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
                
                # 呼叫防呆機制獲取回應
                full_response, used_model = get_ai_response_with_fallback(
                    client, api_messages, system_instruction, allow_search
                )
                
                st.markdown(full_response)
                
                # 狀態標籤
                status_text = f"引擎: {used_model} | 聯網: {'🟢 開啟' if allow_search else '🔴 關閉'}"
                st.caption(f"*({status_text})*")
                
                # 存入記憶體
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"連線失敗，請檢查網路或 API 額度。詳細錯誤：{e}")