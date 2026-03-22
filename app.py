import io
import re
import streamlit as st
from gtts import gTTS
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv

# ── 기본 설정 ──────────────────────────────────────────────
load_dotenv()
client = OpenAI()

SYSTEM_PROMPT = """당신은 응급처치 전문 AI 도우미입니다.

대화 방식:
1. 사용자가 응급상황을 말하면 핵심 응급처치 2~3가지만 간단히 알려주세요.
2. 그 다음 반드시 환자 상태를 확인하는 질문을 하나만 하세요.
3. 사용자가 답하면 그 답변에 맞게 추가 처치를 안내하고 또 다른 상태를 질문하세요.
4. 이런 식으로 대화를 이어가며 상황에 맞는 처치를 안내하세요.

예시:
사용자: 팔이 부러졌어요
AI: 팔을 움직이지 말고 부목으로 고정해주세요. 출혈이 있으면 깨끗한 천으로 눌러주세요.
    혹시 팔에 출혈이 있나요?
사용자: 네 피가 나요
AI: 깨끗한 천으로 출혈 부위를 강하게 눌러주세요. 5~10분간 유지하세요.
    출혈량이 많은가요, 적은가요?

규칙:
- 반드시 한국어로 답변
- 한 번에 질문은 하나만
- 짧고 명확하게
- 생명 위협 상황이면 119 신고를 가장 먼저 강조
"""

# ── 페이지 설정 ────────────────────────────────────────────
st.set_page_config(
    page_title="응급처치 도우미",
    page_icon="🚑",
    layout="centered",
)

# ── CSS (카카오톡 스타일) ──────────────────────────────────
st.markdown("""
<style>
/* 전체 배경 */
.stApp {
    background-color: #97B89A;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2382a885' fill-opacity='0.35'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

/* 헤더 */
.chat-header {
    background-color: #3B1F1F;
    color: white;
    padding: 14px 20px;
    border-radius: 0 0 0 0;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 10px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* 채팅창 컨테이너 */
.chat-container {
    padding: 10px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
}

/* 날짜 구분선 */
.date-divider {
    text-align: center;
    color: white;
    font-size: 12px;
    background-color: rgba(0,0,0,0.2);
    border-radius: 12px;
    padding: 3px 12px;
    display: inline-block;
    margin: 4px auto;
    width: fit-content;
}
.date-divider-wrapper {
    display: flex;
    justify-content: center;
    margin: 6px 0;
}

/* AI 메시지 (왼쪽) */
.msg-row-ai {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    justify-content: flex-start;
}
.ai-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FF4B4B, #FF8C00);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
.ai-name {
    font-size: 12px;
    color: white;
    margin-bottom: 4px;
    font-weight: 500;
}
.bubble-ai {
    background-color: #ffffff;
    border-radius: 0px 16px 16px 16px;
    padding: 10px 14px;
    max-width: 72%;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
    word-break: keep-all;
}
.msg-time-ai {
    font-size: 11px;
    color: rgba(255,255,255,0.8);
    align-self: flex-end;
    margin-left: 4px;
    white-space: nowrap;
}

/* 사용자 메시지 (오른쪽) */
.msg-row-user {
    display: flex;
    align-items: flex-end;
    gap: 6px;
    justify-content: flex-end;
}
.bubble-user {
    background-color: #FFEB01;
    border-radius: 16px 0px 16px 16px;
    padding: 10px 14px;
    max-width: 72%;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
    word-break: keep-all;
}
.msg-time-user {
    font-size: 11px;
    color: rgba(255,255,255,0.8);
    align-self: flex-end;
    white-space: nowrap;
}

/* 입력 영역 */
.stTextInput > div > div > input {
    background-color: white;
    border-radius: 22px;
    border: none;
    padding: 10px 16px;
    font-size: 14px;
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
}
.stButton > button {
    border-radius: 50%;
    width: 42px;
    height: 42px;
    padding: 0;
    font-size: 18px;
    border: none;
}

/* 마이크 입력 영역 숨김 처리 */
.stAudioInput {
    background-color: rgba(255,255,255,0.15);
    border-radius: 12px;
    padding: 8px;
}

/* 119 강조 스타일 */
.emergency-badge {
    display: inline-block;
    background: #FF3333;
    color: white;
    border-radius: 6px;
    padding: 1px 6px;
    font-weight: bold;
    font-size: 13px;
}

/* Streamlit 기본 요소 숨기기 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 구분선 */
div[data-testid="stHorizontalBlock"] {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ───────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # {"role": "user"/"assistant", "content": "...", "time": "..."}
if "api_messages" not in st.session_state:
    st.session_state.api_messages = []
if "audio_response" not in st.session_state:
    st.session_state.audio_response = None
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

# ── 헬퍼 함수 ─────────────────────────────────────────────
from datetime import datetime

def now_time() -> str:
    return datetime.now().strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")

def generate_response(user_input: str) -> str:
    """OpenAI GPT로 응급처치 답변 생성"""
    st.session_state.api_messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.api_messages[-6:],
        temperature=0.3,
        max_tokens=512,
        top_p=1,
    )
    answer = response.choices[0].message.content
    st.session_state.api_messages.append({"role": "assistant", "content": answer})
    return answer

def text_to_speech_bytes(text: str) -> bytes:
    """TTS → 메모리 버퍼 → bytes 반환"""
    clean = re.sub(r'[^\w\s.,!?가-힣]', ' ', text)
    tts = gTTS(text=clean, lang='ko', slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

def speech_to_text(audio_bytes: bytes) -> str | None:
    """업로드된 오디오 bytes → 텍스트"""
    recognizer = sr.Recognizer()
    audio_buf = io.BytesIO(audio_bytes)
    with sr.AudioFile(audio_buf) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data, language='ko-KR')
    except (sr.UnknownValueError, sr.RequestError):
        return None

def render_bubble(role: str, content: str, time_str: str):
    """채팅 말풍선 렌더링"""
    # 119 강조
    content_html = content.replace("119", '<span class="emergency-badge">119</span>')
    content_html = content_html.replace("\n", "<br>")

    if role == "assistant":
        st.markdown(f"""
        <div class="msg-row-ai">
            <div class="ai-avatar">🚑</div>
            <div>
                <div class="ai-name">응급처치 도우미</div>
                <div class="bubble-ai">{content_html}</div>
            </div>
            <div class="msg-time-ai">{time_str}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-row-user">
            <div class="msg-time-user">{time_str}</div>
            <div class="bubble-user">{content_html}</div>
        </div>
        """, unsafe_allow_html=True)

# ── 헤더 ──────────────────────────────────────────────────
st.markdown("""
<div class="chat-header">
    🚑&nbsp;&nbsp;응급처치 도우미
</div>
""", unsafe_allow_html=True)

# ── 날짜 구분선 ────────────────────────────────────────────
today = datetime.now().strftime("%Y년 %m월 %d일 %A").replace(
    "Monday","월요일").replace("Tuesday","화요일").replace("Wednesday","수요일").replace(
    "Thursday","목요일").replace("Friday","금요일").replace("Saturday","토요일").replace("Sunday","일요일")

st.markdown(f"""
<div class="date-divider-wrapper">
    <div class="date-divider">{today}</div>
</div>
""", unsafe_allow_html=True)

# ── 웰컴 메시지 ────────────────────────────────────────────
if not st.session_state.messages:
    welcome = "안녕하세요! 응급처치 도우미입니다 🚑\n어떤 응급 상황이 발생했나요?\n텍스트로 입력하거나 마이크로 말씀해 주세요."
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome,
        "time": now_time()
    })

# ── 메시지 렌더링 ──────────────────────────────────────────
for msg in st.session_state.messages:
    render_bubble(msg["role"], msg["content"], msg["time"])

# ── TTS 자동 재생 ──────────────────────────────────────────
if st.session_state.audio_response:
    st.audio(st.session_state.audio_response, format="audio/mp3", autoplay=True)
    st.session_state.audio_response = None

# ── 입력 영역 ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

# 탭: 텍스트 / 음성
tab1, tab2 = st.tabs(["⌨️ 텍스트 입력", "🎙️ 음성 입력"])

with tab1:
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_text = st.text_input(
                label="메시지",
                placeholder="응급 상황을 입력하세요...",
                label_visibility="collapsed",
            )
        with col2:
            send_btn = st.form_submit_button("➤")

    if send_btn and user_text.strip():
        user_input = user_text.strip()
        t = now_time()
        st.session_state.messages.append({"role": "user", "content": user_input, "time": t})
        with st.spinner(""):
            answer = generate_response(user_input)
            audio_bytes = text_to_speech_bytes(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer, "time": now_time()})
        st.session_state.audio_response = audio_bytes
        st.rerun()

with tab2:
    st.markdown("<p style='color:white; font-size:13px;'>아래 마이크 버튼을 눌러 녹음하세요.</p>", unsafe_allow_html=True)
    audio_input = st.audio_input("음성 녹음", label_visibility="collapsed", key="mic_input")

    if audio_input is not None:
        import hashlib
        audio_bytes_input = audio_input.read()
        audio_hash = hashlib.md5(audio_bytes_input).hexdigest()

        # 같은 오디오를 중복 처리하지 않도록 해시 비교
        if audio_hash != st.session_state.last_audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("음성 인식 중..."):
                recognized = speech_to_text(audio_bytes_input)

            if recognized:
                t = now_time()
                st.session_state.messages.append({"role": "user", "content": recognized, "time": t})
                with st.spinner(""):
                    answer = generate_response(recognized)
                    audio_bytes = text_to_speech_bytes(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer, "time": now_time()})
                st.session_state.audio_response = audio_bytes
                st.rerun()
            else:
                st.warning("음성을 인식하지 못했습니다. 다시 시도해 주세요.")

# ── 대화 초기화 버튼 ───────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 대화 초기화", use_container_width=True):
    st.session_state.messages = []
    st.session_state.api_messages = []
    st.session_state.audio_response = None
    st.rerun()