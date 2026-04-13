"""
及時公關處理系統 (emergency_pr_agent.py) - 方案A：雙檔案架構主程式
具備自動套件安裝與隨插即用特性。
"""
import os
import sys
import subprocess

# ==========================================
# 0. 魔法啟動器：全自動環境與路徑配置
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 確保在 Streamlit 環境下執行，並自動處理相依套件
if "streamlit" not in sys.modules and __name__ == "__main__":
    print("🔍 [系統預檢] 正在啟動千手觀音模組...")
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    with open(req_file, "w", encoding="utf-8") as f:
        # 強制指定最新版 google-genai
        f.write("streamlit\ngoogle-genai\ntenacity\n")
    try:
        import streamlit
    except ImportError:
        print("偵測到新環境，正在為您自動安裝核心套件...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"])
    
    print("啟動系統中...")
    subprocess.check_call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

# ==========================================
# 以下為 Streamlit Web 應用程式本體
# ==========================================
import streamlit as st

# 🌟【架構師心法】：匯入同資料夾下的核心引擎室
try:
    import ai_core
except ImportError:
    st.error(f"❌ 嚴重錯誤：找不到 `ai_core.py` 檔案。請確保它與本程式放在同一個資料夾：{BASE_DIR}")
    sys.exit(1)

st.set_page_config(page_title="危機公關代理人", page_icon="🚨", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    st.title("🔒 企業機密 - 災防應變與危機公關總部")
    if st.button("解鎖進入", type="primary"):
        st.session_state['logged_in'] = True
        st.rerun()
    st.stop()

st.title("🚨 24H 災防緊急通報與安撫代理人 (中央引擎版)")
st.markdown("已成功掛載 `ai_core.py` 降級備援防護盾與 **Token 極限節流閥**。")

default_report = "你好！我是頭份市中華路跟建國路交叉口這裡的居民！馬路上有怪手在挖水溝，結果突然聽到『嘶嘶』很大聲，然後整條街都是超濃的瓦斯味！你們快點派人來啦，感覺快爆炸了！"
report_text = st.text_area("民眾緊急訊息：", value=default_report, height=100)

if st.button("⚡ 啟動 AI 千手觀音應變機制", type="primary", use_container_width=True):
    if report_text:
        try:
            client = ai_core.get_client() # 從引擎取得連線
        except Exception as e:
            st.error(str(e))
            st.stop()
            
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        # 依照方案A維持原設計：三個分身獨立執行，但底層透過 ai_core 進行了極限 Token 限制
        with col1:
            st.info("👩‍💼 **【分身一】客服公關**")
            with st.spinner("撰寫安撫訊息中..."):
                sys_prompt_1 = "你是天然氣公司客服。根據報案回覆簡短安撫訊息，指導退到安全處。限80字。"
                pr_response, model_used = ai_core.robust_generate_content(client, report_text, sys_prompt_1)
                st.write(pr_response)
                st.caption(f"🛡️ 引擎: {model_used}")

        with col2:
            st.warning("👷‍♂️ **【分身二】工務調度**")
            with st.spinner("生成派工單中..."):
                sys_prompt_2 = "你是調度員。立刻寫一封給頭份區工務班長的緊急簡訊。包含：地點、原因、嚴重等級。文字精簡。"
                dispatch_response, _ = ai_core.robust_generate_content(client, report_text, sys_prompt_2)
                st.write(dispatch_response)

        with col3:
            st.error("👔 **【分身三】政府聯絡官**")
            with st.spinner("擬定通報稿中..."):
                sys_prompt_3 = "你是聯絡官。擬定傳給『消防局』與『里長』的通報備忘錄。格式嚴謹，表明已派員處理。"
                gov_response, _ = ai_core.robust_generate_content(client, report_text, sys_prompt_3)
                st.write(gov_response)
                
        st.success("✅ 應變機制執行完畢！(API 費用已壓至最低極限)")
