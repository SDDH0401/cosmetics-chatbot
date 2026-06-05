#기본 화면 구성입니다(app.py)

# 실행 : streamlit run app.py

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI 화장품 추천 및 상담 챗봇",
    page_icon="💄",
    layout="wide"
)

st.title("💄 AI 화장품 추천 및 상담 챗봇")
st.write("피부 타입과 고민을 입력하면 맞춤형 화장품을 추천하고, 궁금한 점을 상담해줍니다.")

with st.sidebar:
    st.header("피부 정보 입력")

    skin_type = st.selectbox(
        "피부 타입",
        ["건성", "지성", "복합성", "민감성", "수부지", "잘 모르겠음"]
    )

    concerns = st.multiselect(
        "피부 고민",
        ["여드름", "홍조", "건조함", "피지", "모공", "잡티", "각질", "탄력 저하"]
    )

    texture = st.selectbox(
        "선호 제형",
        ["상관없음", "크림", "젤", "로션", "세럼", "토너", "패드"]
    )

    recommend_btn = st.button(
        "✨ 화장품 추천받기",
        use_container_width=True
    )

st.subheader("✨ 맞춤 화장품 추천")

if recommend_btn:
    if not concerns:
        st.warning("피부 고민을 하나 이상 선택해주세요.")
    else:
        payload = {
            "skin_type": skin_type,
            "concerns": concerns,
            "texture": texture
        }

        try:
            response = requests.post(f"{API_URL}/recommend", json=payload)

            if response.status_code == 200:
                result = response.json()
                products = result.get("products", [])

                if products:
                    for item in products:
                        with st.container(border=True):
                            st.markdown(f"### {item.get('name', '제품명 없음')}")

                            st.write(f"**브랜드:** {item.get('brand', '정보 없음')}")
                            st.write(f"**카테고리:** {item.get('category', '정보 없음')}")
                            st.write(f"**가격:** {item.get('price', '정보 없음')}")
                            st.write(f"**평점:** {item.get('rating', '정보 없음')}")
                            st.write(f"**리뷰 요약:** {item.get('review_summary', '리뷰 정보 없음')}")
                            st.write(f"**추천 이유:** {item.get('reason', '추천 이유 없음')}")
                else:
                    st.info("추천 결과가 없습니다.")
            else:
                st.error("추천 결과를 불러오지 못했습니다.")

        except requests.exceptions.ConnectionError:
            st.error("백엔드 서버와 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해주세요.")

st.divider()

st.subheader("💬 피부 상담 챗봇")

question = st.chat_input("화장품이나 피부 고민에 대해 질문해보세요.")

if question:
    st.chat_message("user").write(question)

    payload = {
        "question": question,
        "skin_type": skin_type,
        "concerns": concerns,
        "texture": texture
    }

    try:
        response = requests.post(f"{API_URL}/chat", json=payload)

        if response.status_code == 200:
            answer = response.json().get("answer", "답변이 없습니다.")
            st.chat_message("assistant").write(answer)
        else:
            st.chat_message("assistant").write("답변을 불러오지 못했습니다.")

    except requests.exceptions.ConnectionError:
        st.chat_message("assistant").write("백엔드 서버와 연결할 수 없습니다.")