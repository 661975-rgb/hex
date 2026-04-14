"""
及時公關處理系統 (emergency_pr_agent.py) - 模型精準對焦版
修復 Google API v1beta 的 404 模型名稱對應問題。
"""
import streamlit as st

try:
    import google.generativeai as genai
    from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
except ImportError:
    st.error("❌ 系統啟動失敗：缺少核心套件。請確認 GitHub 上有 `requirements.txt`。")
    st.stop()

def get_client() -> genai.GenerativeModel:
    """從 Streamlit 保險箱讀取金鑰並建立連線"""
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        # 🔑 【核心修復點】：加上 -latest 確保 API 能精準找到最新且存活的模型節點
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    else:
        raise ValueError("🔒 找不到 API 金鑰！請在 Streamlit 的 Secrets 設定 GEMINI_API_KEY。")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def robust_generate_content(model: genai.GenerativeModel, prompt: str, system_instruction: str):
    """具備自動重試與 Token 節流防護的生成函數"""
    full_prompt = f"【系統指令】\n{system_instruction}\n\n【緊急報案內容】\n{prompt}"
    config = genai.types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=150 
    )
    response = model.generate_content(full_prompt, generation_config=config)
    # 更新顯示字串以核對模型版本
    return response.text, "gemini-1.5-flash-latest"

# ==========================================
# UI 介面與主邏輯
# ==========================================
st.set_page_config(page_title="危機公關代理人", page_icon="🚨", layout="wide")

st.title("🚨 24H 災防緊急通報與安撫代理人")
st.markdown("已切換至 **`gemini-1.5-flash-latest`** 穩定節點。")

default_report = "你好！我是頭份市中華路跟建國路交叉口這裡的居民！馬路上有怪手在挖水溝，結果突然聽到『嘶嘶』很大聲，然後整條街都是超濃的瓦斯味！你們快點派人來啦，感覺快爆炸了！"
report_text = st.text_area("民眾緊急訊息：", value=default_report, height=100)

if st.button("⚡ 啟動 AI 千手觀音應變機制", type="primary", use_container_width=True):
    if report_text:
        try:
            client = get_client()
        except Exception as e:
            st.error(str(e))
            st.stop()
            
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("👩‍💼 **【分身一】客服公關**")
            with st.spinner("連線中..."):
                sys_prompt_1 = "你是天然氣公司客服。根據報案回覆簡短安撫訊息，指導退到安全處。限80字。"
                try:
                    pr_response, model_used = robust_generate_content(client, report_text, sys_prompt_1)
                    st.write(pr_response)
                    st.caption(f"🛡️ 引擎: {model_used}")
                except RetryError as e:
                    real_error = e.last_attempt.exception()
                    st.error(f"❌ API 拒絕連線 (已重試3次皆失敗)。")
                    st.error(f"🔍 **Google 原廠真實報錯訊息**：\n`{real_error}`")
                    st.stop()

        with col2:
            st.warning("👷‍♂️ **【分身二】工務調度**")
            with st.spinner("生成派工單中..."):
                sys_prompt_2 = "你是調度員。立刻寫一封給頭份區工務班長的緊急簡訊。包含：地點、原因、嚴重等級。文字精簡。"
                try:
                    dispatch_response, _ = robust_generate_content(client, report_text, sys_prompt_2)
                    st.write(dispatch_response)
                except RetryError:
                    st.error("連線異常，已中止。")

        with col3:
            st.error("👔 **【分身三】政府聯絡官**")
            with st.spinner("擬定通報稿中..."):
                sys_prompt_3 = "你是聯絡官。擬定傳給『消防局』與『里長』的通報備忘錄。格式嚴謹，表明已派員處理。"
                try:
                    gov_response, _ = robust_generate_content(client, report_text, sys_prompt_3)
                    st.write(gov_response)
                except RetryError:
                    st.error("連線異常，已中止。")
