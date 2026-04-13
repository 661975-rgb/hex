import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="AI 企業戰術全能 App",
    page_icon="🤖",
    layout="wide"
)

# 主畫面標題
st.title("🤖 AI 企業戰術全能 App")
st.markdown("---")

# 歡迎語區塊
st.success("系統已連線：雲端伺服器運作正常")

st.markdown("""
### 🏮 歡迎來到您的個人 AI 助理總部
本系統整合了多項企業級 AI 運算工具，專為手機操作優化。
請點擊畫面 **左上角的選單按鈕 ( > )** 來切換不同的功能模組。

---
#### 🛠️ 目前已掛載模組：

1. **📈 股票戰情室 Pro**
   - 即時行情監控
   - 2.5 世代深度分析報告
   - 自動 Word/TXT 匯出

2. **🚨 公關危機應變系統**
   - 快速生成內部派工單
   - 官方公關稿撰寫
   - 災後補償建議
---
""")

# 底部資訊
st.caption("© 2026 企業級助理系統 | 隨身碟相容架構")
