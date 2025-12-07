import os
import time
import tempfile

import streamlit as st
from google import genai

# ---------------------------
# 設定（APIキー）
# ---------------------------
# 安全のため、本番では環境変数 or Streamlit Secrets を推奨
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

st.set_page_config(page_title="Gemini 動画解析ツール", page_icon="🎥")

st.title("🎥 Gemini 動画解析ツール (Streamlit版)")

if not GEMINI_API_KEY:
    st.warning("環境変数 GOOGLE_API_KEY が設定されていません。ローカル動作時はターミナルから設定してください。")
else:
    st.success("APIキーは設定済みのようです。")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ---------------------------
# ファイルが ACTIVE になるまで待つ関数
# ---------------------------
def wait_for_file_active(file, timeout=60, interval=2):
    start = time.time()
    file_id = file.name

    while True:
        f = client.files.get(name=file_id)

        if getattr(f, "state", None) == "ACTIVE":
            return f

        if time.time() - start > timeout:
            raise TimeoutError("ファイルがACTIVEになりませんでした（タイムアウト）")

        time.sleep(interval)


# ---------------------------
# UI
# ---------------------------
uploaded_video = st.file_uploader("動画ファイルをアップロード (mp4 など)", type=["mp4", "mov", "mkv", "webm"])

prompt = st.text_area(
    "指示プロンプト（任意）",
    value="この動画の内容を日本語でわかりやすく要約してください。",
    height=100,
)

analyze_button = st.button("解析する")

if analyze_button:
    if client is None:
        st.error("APIキーが設定されていません。GOOGLE_API_KEY を環境変数または Streamlit Secrets に設定してください。")
    elif uploaded_video is None:
        st.error("動画ファイルをアップロードしてください。")
    else:
        try:
            # 一時ファイルに保存
            suffix = "." + uploaded_video.name.split(".")[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_video.read())
                temp_path = tmp.name

            st.info("動画をアップロード中…")
            uploaded = client.files.upload(
                file=temp_path,
                config={"mime_type": "video/mp4"},  # 必要なら拡張子に合わせて条件分岐
            )

            st.info("ファイルがACTIVEになるのを待機中…")
            active_file = wait_for_file_active(uploaded)

            st.info("Gemini で解析中…")
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"file_data": {"file_uri": active_file.uri}},
                        ],
                    }
                ],
            )

            st.success("解析が完了しました！")
            st.markdown("### 解析結果")
            st.write(res.text)

        except TimeoutError as e:
            st.error(f"エラー: {e}")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
