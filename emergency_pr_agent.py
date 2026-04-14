"""
及時公關處理系統 (emergency_pr_agent.py) - 終極單檔架構版
已內建 API 防護盾與 Streamlit Secrets 讀取機制。
"""
import os
import sys
import streamlit as st

# ==========================================
# 1. 核心引擎 (內建 AI 處理邏輯，免除 ai_core.py)
# ==========================================
# 嘗試載入套件，若在雲端環境缺少套件會透過 requirements.txt 安裝
try:
    import google.generativeai as genai
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    st.error("❌ 系統啟動失敗：缺少核心套件。請確認 GitHub 上有 `requirements.txt`。")
    st.stop()

def get_client() -> genai.GenerativeModel:
    """從 Streamlit 保險箱讀取金鑰並建立連線"""
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        # 強制使用 flash 模型以確保高效率與低成本
        return genai.GenerativeModel('gemini-1.5-flash')
    else:
        raise ValueError("🔒 找不到 API 金鑰！請在 Streamlit 的 Secrets 設定 GEMINI_API_KEY。")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def robust_generate_content(model: genai.GenerativeModel, prompt: str, system_instruction: str):
    """具備自動重試與 Token 節流防護的生成函數"""
    # 組合 System Prompt 與 User Prompt
    full_prompt = f"【系統指令】\n{system_instruction}\n\n【緊急報案內容】\n{prompt}"
    
    # 強制設定 Token 上限與低隨機性 (確保回答精準不廢話)
    config = genai.types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=150 
    )
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text, "gemini-1.5-flash"

# ==========================================
# 2. Streamlit Web 應用程式本體
# ==========================================
st.set_page_config(page_title="危機公關代理人", page_icon="🚨", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 企業機密 - 災防應變與危機公關總部")
    if st.button("解鎖進入", type="primary"):
        st.session_state['logged_in'] = True
        st.rerun()
    st.stop()

st.title("🚨 24H 災防緊急通報與安撫代理人")
st.markdown("已成功啟動**單檔內建引擎**，並掛載 **Token 極限節流閥**。")

default_report = "你好！我是頭份市中華路跟建國路交叉口這裡的居民！馬路上有怪手在挖水溝，結果突然聽到『嘶嘶』很大聲，然後整條街都是超濃的瓦斯味！你們快點派人來啦，感覺快爆炸了！"
report_text = st.text_area("民眾緊急訊息：", value=default_report, height=100)

if st.button("⚡ 啟動 AI 千手觀音應變機制", type="primary", use_container_width=True):
    if report_text:
        try:
            client = get_client() # 取得安全連線
        except Exception as e:
            st.error(str(e))
            st.stop()
            
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("👩‍💼 **【分身一】客服公關**")
            with st.spinner("撰寫安撫訊息中..."):
                sys_prompt_1 = "你是天然氣公司客服。根據報案回覆簡短安撫訊息，指導退到安全處。限80字。"
                pr_response, model_used = robust_generate_content(client, report_text, sys_prompt_1)
                st.write(pr_response)
                st.caption(f"🛡️ 引擎: {model_used}")

        with col2:
            st.warning("👷‍♂️ **【分身二】工務調度**")
            with st.spinner("生成派工單中..."):
                sys_prompt_2 = "你是調度員。立刻寫一封給頭份區工務班長的緊急簡訊。包含：地點、原因、嚴重等級。文字精簡。"
                dispatch_response, _ = robust_generate_content(client, report_text, sys_prompt_2)
                st.write(dispatch_response)

        with col3:
            st.error("👔 **【分身三】政府聯絡官**")
            with st.spinner("擬定通報稿中..."):
                sys_prompt_3 = "你是聯絡官。擬定傳給『消防局』與『里長』的通報備忘錄。格式嚴謹，表明已派員處理。"
                gov_response, _ = robust_generate_content(client, report_text, sys_prompt_3)
                st.write(gov_response)
                
        st.success("✅ 應變機制執行完畢！(API 費用已壓至最低極限)")
