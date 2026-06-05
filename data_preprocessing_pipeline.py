import re
import html
import os
import pandas as pd
from kiwipiepy import Kiwi

# Kiwi 형태소 분석기 초기화
kiwi = Kiwi()

class OliveYoungPreprocessor:
    def __init__(self):
        # 모든 종류의 컬러 이모지, 하트, 그래픽 기호를 잡는 정규식 패턴
        self.emoticon_pattern = re.compile(
            r'[\U00010000-\U0010FFFF]'  # 🍫, 🤎, 💗, 🌹 등 최신 이모지
            r'|[\u2600-\u27BF]'          # 하트, 별, 문구용 기호 등
            r'|[\u2000-\u33FF]'          # 특수 문장 부호 및 기호
        )
        
        # 괄호 안에 어떤 문자, 공백, 슬래시(/)가 들어가든 괄호 자체를 통째로 날리는 강력한 패턴
        self.bracket_pattern = re.compile(r'\[.*?\]|\(.*?\)|{.*?}')
        
        # URL 패턴 (광고 필터링용)
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        
    def clean_text(self, text):
        """1단계: 텍스트 정제 (Text Cleaning)"""
        if not isinstance(text, str) or pd.isna(text):
            return ""
        
        text = html.unescape(text)
        text = re.sub(r'[\r\n\t]+', ' ', text)
        
        # 본문에서도 모든 괄호문과 이모지 완벽 제거
        text = self.bracket_pattern.sub('', text)
        text = self.emoticon_pattern.sub('', text)
        
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def filter_quality(self, text):
        """2단계: 품질 필터링 (Quality Filtering)"""
        if not text:
            return None
            
        if len(text) < 20 or len(text) > 2000:
            return None
            
        if self.url_pattern.search(text):
            return None
            
        text = re.sub(r'(ㅋ|ㅎ|ㅠ|ㅜ|아|오|요|다|가|이|의){3,}', r'\1', text)
        
        try:
            tokens = kiwi.tokenize(text)
            words = [t.form for t in tokens if t.tag.startswith('N') or t.tag.startswith('V')]
            if words:
                max_word_count = max(words.count(w) for w in set(words))
                if (max_word_count / len(words)) > 0.5:
                    return None
        except Exception:
            pass
            
        return text

    def clean_product_name_directly(self, raw_name):
        """
        3단계: product_name 컬럼 자체를 완전히 청소하는 함수 🎯
        """
        if not isinstance(raw_name, str) or pd.isna(raw_name):
            return "Unknown", False
            
        # 1) bundle 여부 체크 (괄호 지우기 전에 원본에서 확인)
        bundle = any(keyword in raw_name for keyword in ['기획', '세트', '증정', '번들', '1+1', '추가', '미니'])
        
        # 2) 🎯 공백/슬래시가 포함된 모든 형태의 괄호문([..], (..), {..})을 안의 내용까지 완전히 무조건 제거
        cleaned_name = self.bracket_pattern.sub('', raw_name)
        
        # 이모티콘 제거
        cleaned_name = self.emoticon_pattern.sub('', cleaned_name).strip()
        
        # 3) 'X종 중 택1', '단품', '기획' 등 RAG 검색 노이즈 단어 및 용량 문자열 실시간 청소
        cleaned_name = re.sub(r'\d+종\s+중\s+택\d+', '', cleaned_name)
        cleaned_name = re.sub(r'\d+(?:ml|g|매|패드|개입|입)', '', cleaned_name)
        cleaned_name = cleaned_name.replace('단품/기획', '').replace('단품', '').replace('기획', '')
        
        # 4) brand와 순수 제품명 분리 (첫 어절 분리)
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
        name_parts = cleaned_name.split(' ', 1)
        
        brand = name_parts[0] if len(name_parts) > 1 else "Unknown"
        pure_name = name_parts[1] if len(name_parts) > 1 else cleaned_name
        
        # 문장 앞뒤에 남은 쓸데없는 특수문자지 찌꺼기 최종 흡입 (/, -, ! 등 제거)
        pure_name = re.sub(r'^[^a-zA-Z0-9가-힣]+|[^a-zA-Z0-9가-힣]+$', '', pure_name)
        pure_name = re.sub(r'\s+', ' ', pure_name).strip()
        
        # 최종적으로 생성할 '브랜드명 + 순수제품명' 조합 생성
        final_product_name = f"{brand} {pure_name}".strip()
        
        return pd.Series([final_product_name, brand, bundle])

    def run_pipeline(self, input_file_path, output_file_path):
        """통합 전처리 파이프라인 가동"""
        if not os.path.exists(input_file_path):
            print(f"❌ 에러: {input_file_path} 파일을 찾을 수 없습니다.")
            return None
            
        print(f"🔍 CSV 로드 중... ({input_file_path})")
        df = pd.read_csv(input_file_path)
        print(f"📊 원본 데이터 수: {len(df)}건")
        
        # 01 텍스트 정제
        print("🔄 01 텍스트 정제 단계 수행 중...")
        df['cleaned_text'] = df['content'].apply(self.clean_text)
        
        # 02 품질 필터링
        print("🔄 02 품질 필터링 단계 수행 중...")
        df['cleaned_text'] = df['cleaned_text'].apply(self.filter_quality)
        
        # 필터링 조건 미달 데이터 제거
        df = df.dropna(subset=['cleaned_text']).reset_index(drop=True)
        print(f"✅ 필터링 완료: {len(df)}건 데이터 최종 확정")
        
        # 03 제품명 파싱 (🎯 product_name 자체를 변환하고 product_clean 컬럼은 삭제!)
        print("🔄 03 product_name 컬럼 자체의 괄호 무조건 삭제 및 덮어쓰기 중...")
        df[['product_name', 'brand', 'bundle']] = df['product_name'].apply(self.clean_product_name_directly)
        
        # 결과 컬럼 구성 및 정렬 (product_clean 대신 깨끗해진 product_name을 사용)
        final_cols = [
            'category', 'brand', 'product_name', 'bundle', 'rating', 'cleaned_text'
        ]
        df_final = df[final_cols]
        
        # 저장
        df_final.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        print(f"🎉 전처리 완료! 파일이 저장되었습니다 ➡️ {output_file_path}")
        return df_final

# --- 스크립체 실행 ---
if __name__ == "__main__":
    preprocessor = OliveYoungPreprocessor()
    
    input_path = "c:/RAGP/reviews_all.csv"
    output_path = "c:/RAGP/reviews_preprocessed.csv"
    
    df_result = preprocessor.run_pipeline(input_path, output_path)
    
    if df_result is not None:
        print("\n📊 [product_name 컬럼 내부의 괄호가 완벽하게 교체된 결과]")
        print(df_result[['brand', 'product_name', 'bundle']].head(5).to_string())