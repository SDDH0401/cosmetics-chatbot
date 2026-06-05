import os
import shutil
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
api_key = os.getenv("OPENAI_API_KEY")

EMBEDDINGS = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=api_key)
LLM         = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
REVIEW_DB_DIR = "./chroma_db/reviews"

def refine_review(review: str) -> str:
    prompt = f"""다음 화장품 리뷰를 명확하고 객관적인 문장으로 정제하세요.
규칙:
1. 이모지, 줄임말, 감탄사 제거
2. 핵심 내용만 남기기
3. 2~3문장으로 요약
4. 없는 내용 절대 추가하지 말 것
5. 한국어로 작성

리뷰: {review}
정제된 문장:"""
    try:
        return LLM.invoke(prompt).content.strip()
    except:
        return review

def build_review_db(csv_path="reviews_all.csv"):
    print("\n[리뷰 DB 롤백 및 복구]")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df[df["content"].notna() & (df["content"].str.len() > 20)]
    
    # 이미 정제된 csv 파일(reviews_all_refined.csv)이 있다면 시간 절약을 위해 로드
    if os.path.exists("reviews_all_refined.csv"):
        print("  기존 정제된 파일 로드 중...")
        df = pd.read_csv("reviews_all_refined.csv", encoding="utf-8-sig")
    else:
        print("  GPT 리뷰 정제 중...")
        df["content_refined"] = [refine_review(c) for c in df["content"].tolist()]
        df.to_csv("reviews_all_refined.csv", index=False, encoding="utf-8-sig")

    docs = []
    for _, row in df.iterrows():
        docs.append(Document(
            page_content=str(row["content_refined"]), # ⭐️ 쪼개지 않고 원본 컨텍스트 보존
            metadata={
                "product_name": str(row["product_name"]),
                "category":     str(row["category"]),
                "rating":       str(row["rating"]),
                "original":     str(row["content"])[:200],
            }
        ))

    if os.path.exists(REVIEW_DB_DIR):
        shutil.rmtree(REVIEW_DB_DIR)

    db = Chroma.from_documents(documents=docs, embedding=EMBEDDINGS, collection_name="reviews", persist_directory=REVIEW_DB_DIR)
    print(f"  ✅ 리뷰 원본 보존 DB 복구 완료: 최종 {len(docs)}개 문서 저장")
    return db

if __name__ == "__main__":
    build_review_db()