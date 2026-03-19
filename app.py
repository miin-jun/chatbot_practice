

import io
import re
from gtts import gTTS
import speech_recognition as sr
from IPython.display import display, Audio
from openai import OpenAI
from dotenv import load_dotenv
import time
from playsound import playsound
import pygame


load_dotenv()
recognizer = sr.Recognizer() # Recognizer 객체를 생성하여 음성 인식 기능을 사용할 준비를 함
api_messages = [] # 멀티턴 대화 기록을 위한 리스트
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

# LLM 응답 생성 함수
def generate_response(user_input: str) -> str:
    

    api_messages.append({"role": "user", "content": user_input}) # 사용자 입력을 대화 기록에 추가
    
    response = client.chat.completions.create(
        model = "gpt-4.1-mini",
        messages = [{
            'role' : 'system',
            'content' : SYSTEM_PROMPT
        }] + api_messages[-6:],
        temperature = 0.3,
        max_tokens = 4096,
        top_p = 1
        )
    
    answer = response.choices[0].message.content # LLM의 응답에서 텍스트 부분을 추출
    api_messages.append({"role": "assistant", "content": answer})# LLM 응답을 대화 기록에 추가
    return answer






# TTS 함수
def text_to_speech(text: str):
    clean = re.sub(r'[^\w\s.,!?가-힣]', ' ', text) # TTS에 적합하도록 특수문자 제거
    tts = gTTS(text=clean, lang='ko', slow=False)# gTTS 객체 생성
    
    # 파일 저장 없이 메모리에서 바로 재생
    buf = io.BytesIO() # 메모리 버퍼 생성
    tts.write_to_fp(buf) # TTS 음성을 메모리 버퍼에 저장
    buf.seek(0)
    
    pygame.mixer.init() 
    pygame.mixer.music.load(buf)
    pygame.mixer.music.play()
    
    # 재생 끝날 때까지 대기
    while pygame.mixer.music.get_busy(): # 음악이 재생 중이면 대기
        pygame.time.Clock().tick(10)




'''----------------------------------------------------------------------------------'''

while True:
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("말씀하세요")

        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio, language='ko-KR')

            if text == '고마워':
                print("프로그램을 종료합니다.")
                break

            print(f"\n사용자: {text}")

            response = generate_response(text)
            print(f"AI: {response}\n")

            text_to_speech(response)

        except sr.WaitTimeoutError:
            print("시간 내에 말이 감지되지 않았습니다.")
        except sr.UnknownValueError:
            print("음성 인식에 실패했습니다.")
        except sr.RequestError as e:
            print(f"음성 인식 서비스 오류: {e}")