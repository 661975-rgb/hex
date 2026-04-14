"""
及時公關處理系統 (emergency_pr_agent.py) - 全自動雷達尋標版
內建動態模型偵測機制，徹底解決 404 Model Not Found 問題。
"""
import streamlit as st

try:
    import google.generativeai as genai
    from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
except ImportError:
    st.error("❌ 系統啟動失敗：缺少核心套件。請確認 GitHub 上有 `requirements.txt`。")
    st.stop()

@st.cache_resource
def auto_discover_model() -> tuple:
    """動態偵測此 API 金鑰真正有權限使用的模型，回傳 (連線實體, 模型名稱)"""
    if "GEMINI_API_KEY" not in st.secrets:
        raise ValueError("🔒 找不到 API 金鑰！請在 Streamlit 的 Secrets 設定 GEMINI_API_KEY。")

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    # 1. 向 Google 伺服器請求可用模型清單
    valid_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            valid_models.append(m.name)

    if not valid_models:
        raise ValueError("❌ 致命錯誤：這把 API 金鑰雖然有效，但沒有綁定任何可用的文字生成模型！請檢查 Google Cloud / AI Studio 權限。")

    # 2. 智慧排序邏輯：優先找 1.5-flash -> 1.5-pro -> 1.0-pro -> 隨便抓第一個能用的
    target_model = valid_models[0] 
    for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro', 'models/gemini-1.0-pro']:
        if preferred in valid_models:
            target_model = preferred
            break
            
    # 3. 移除 'models/' 前綴以符合 SDK 呼叫慣例
    clean_name = target_model.replace('models/', '')
    
    return genai.GenerativeModel(clean_name), clean_name

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def robust_generate_content(model: genai.GenerativeModel, prompt: str, system_instruction: str):
    """具備自動重試與 Token 節流防護的生成函數"""
    full_prompt = f"【系統指令】\n{system_instruction}\n\n【緊急報案內容】\n{prompt}"
    config = genai.types.GenerationConfig(
        temperature=0.2,
        max_output_tokens=150 
    )
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text

# ==========================================
# UI 介面與主邏輯
# ==========================================
st.set_page_config(page_title="危機公關代理人", page_icon="🚨", layout="wide")

st.title("🚨 24H 災防緊急通報與安撫代理人")

default_report = "你好！我是頭份市中華路跟建國路交叉口這裡的居民！馬路上有怪手在挖水溝，結果突然聽到『嘶嘶』很大聲，然後整條街都是超濃的瓦斯味！你們快點派人來啦，感覺快爆炸了！"
report_text = st.text_area("民眾緊急訊息：", value=default_report, height=100)

if st.button("⚡ 啟動 AI 千手觀音應變機制", type="primary", use_container_width=True):
    if report_text:
        try:
            with st.spinner("啟動雷達系統，尋找可用模型中..."):
                client, active_model_name = auto_discover_model()
            st.success(f"✅ 雷達鎖定！已自動配對並切換至您的可用模型：**`{active_model_name}`**")
        except Exception as e:
            st.error(str(e))
            st.stop()
            
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("👩‍💼 **【分身一】客服公關**")
            with st.spinner("連線生成中..."):
                sys_prompt_1 = "你是天然氣公司客服。根據報案回覆簡短安撫訊息，指導退到安全處。限80字。"
                try:
                    pr_response = robust_generate_content(client, report_text, sys_prompt_1)
                    st.write(pr_response)
                except RetryError as e:
                    real_error = e.last_attempt.exception()
                    st.error(f"❌ 生成失敗。Google 原廠報錯：\n`{real_error}`")
                    st.stop()

        with col2:
            st.warning("👷‍♂️ **【分身二】工務調度**")
            with st.spinner("生成派工單中..."):
                sys_prompt_2 = "你是調度員。立刻寫一封給頭份區工務班長的緊急簡訊。包含：地點、原因、嚴重等級。文字精簡。"
                try:
                    dispatch_response = robust_generate_content(client, report_text, sys_prompt_2)
                    st.write(dispatch_response)
                except RetryError:
                    st.error("連線異常，已中止。")

        with col3:
            st.error("👔 **【分身三】政府聯絡官**")
            with st.spinner("擬定通報稿中..."):
                sys_prompt_3 = "你是聯絡官。擬定傳給『消防局』與『里長』的通報備忘錄。格式嚴謹，表明已派員處理。"
                try:
                    gov_response = robust_generate_content(client, report_text, sys_prompt_3)
                    st.write(gov_response)
                except RetryError:
                    st.error("連線異常，已中止。")
