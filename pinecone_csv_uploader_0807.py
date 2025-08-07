import glob
import logging
import os
import tiktoken
import pandas as pd
from tqdm import tqdm
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from pinecone import Pinecone

# .env 파일에서 환경변수 로드
load_dotenv()

# 환경변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# API 키 검증
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")


def get_csv_files(base_dir):
    """하위 디렉토리의 모든 CSV 파일 목록 가져오기"""
    csv_pattern = os.path.join(base_dir, "**", "*.csv")
    return glob.glob(csv_pattern, recursive=True)


def create_searchable_text(model_name):
    """모델명을 검색 가능한 텍스트로 생성"""
    # 모델명만 텍스트로 사용 (단순하고 명확하게)
    return model_name if model_name.strip() else "Unknown Model"


def process_csv_data(csv_path):
    """CSV 파일을 읽어서 PDF 데이터 처리 및 청크 분할"""
    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"CSV 파일 로드 완료: {len(df)} 행")
        
        all_chunks = []
        
        # 각 행의 데이터 처리
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="데이터 처리 중"):
            pdf_url = row.get('pdf_url', '')
            model_name = row.get('dir', '')  # dir = 모델명
            original_filename = row.get('원본_파일명', '')
            product_page_url = row.get('제품_페이지_URL', '')
            
            if not pdf_url or not model_name:
                continue
                
            # 모델명만 검색 텍스트로 사용
            text = create_searchable_text(model_name)
            
            # 생성된 텍스트는 보통 짧으므로 chunk 분할하지 않음
            # URL과 메타데이터는 문서 단위로 관리
            chunks = [text]  # 하나의 문서로 처리
            
            # 메타데이터 추가 (chunk 분할 없이 문서 단위로)
            chunk_data = {
                "text": text,
                "metadata": {
                    "model_name": model_name,
                    "pdf_url": pdf_url,
                    "original_filename": original_filename,
                    "product_page_url": product_page_url,
                    "collection_time": str(row.get('수집_시간', ''))
                },
            }
            all_chunks.append(chunk_data)
            
            print(f"처리 완료: {model_name} - {original_filename}")
            
        return all_chunks
        
    except Exception as e:
        print(f"CSV 처리 실패 {csv_path}: {e}")
        return []


MAX_TOKENS_PER_REQUEST = 300000
# text-embedding-3-small에 맞는 encoding
encoding = tiktoken.get_encoding("cl100k_base")


def batch_by_tokens(texts, metadatas, max_tokens=MAX_TOKENS_PER_REQUEST):
    """토큰 수에 따라 배치 분할"""
    batches = []
    current_texts = []
    current_metadatas = []
    current_tokens = 0

    for text, metadata in zip(texts, metadatas):
        tokens = len(encoding.encode(text))
        if tokens > max_tokens:
            # 너무 긴 단일 텍스트 → 따로 처리
            print(f"텍스트 하나가 {tokens} 토큰으로 너무 깁니다. 잘라서 넣으세요!")
            continue

        if current_tokens + tokens > max_tokens:
            # 현재 배치 마감
            batches.append((current_texts, current_metadatas))
            current_texts = []
            current_metadatas = []
            current_tokens = 0

        current_texts.append(text)
        current_metadatas.append(metadata)
        current_tokens += tokens

    # 마지막 배치 추가
    if current_texts:
        batches.append((current_texts, current_metadatas))

    return batches


def create_pinecone_index(pc, index_name, dimension=1536, metric='cosine', cloud='aws', region='us-east-1'):
    """
    Pinecone 인덱스 생성 함수

    Args:
        pc: Pinecone 클라이언트 객체
        index_name: 생성할 인덱스 이름
        dimension: 벡터 차원 (text-embedding-3-small = 1536)
        metric: 유사도 메트릭 ('cosine', 'euclidean', 'dotproduct')
        cloud: 클라우드 제공자 ('aws', 'gcp', 'azure')
        region: 리전 설정

    Returns:
        bool: 성공 여부
    """
    try:
        # 기존 인덱스 목록 확인
        existing_indexes = [index.name for index in pc.list_indexes()]
        print(f"기존 인덱스 목록: {existing_indexes}")

        # 인덱스가 이미 존재하는지 확인
        if index_name in existing_indexes:
            print(f"인덱스 '{index_name}'가 이미 존재합니다.")
            return True

        # 새 인덱스 생성
        print(f"인덱스 '{index_name}' 생성 중...")

        from pinecone import ServerlessSpec

        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud=cloud,
                region=region
            )
        )

        print(f"인덱스 '{index_name}' 생성 완료!")

        # 인덱스 초기화 대기
        import time
        print("인덱스 초기화를 위해 10초 대기중...")
        time.sleep(10)

        return True

    except Exception as e:
        print(f"인덱스 생성 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    BASE_DIR = "C:/Workspaces/SKN14-4th-3Team_backup/data"  # CSV 파일이 있는 디렉토리
    EMBEDDINGS_MODEL = "text-embedding-3-small"
    INDEX_NAME = "manual-url-index-0807"

    # Pinecone 클라이언트 초기화
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # 인덱스 생성 (존재하지 않는 경우)
    if not create_pinecone_index(pc, INDEX_NAME):
        print("인덱스 생성에 실패했습니다. 프로그램을 종료합니다.")
        return

    embeddings = OpenAIEmbeddings(model=EMBEDDINGS_MODEL)

    # Pinecone 벡터스토어 초기화
    try:
        vectordb = PineconeVectorStore(
            index=pc.Index(INDEX_NAME),
            embedding=embeddings,
        )
        print("Pinecone 벡터스토어 초기화 완료!")
    except Exception as e:
        print(f"벡터스토어 초기화 실패: {e}")
        return

    # CSV 파일 목록 가져오기
    csv_files = get_csv_files(BASE_DIR)

    if not csv_files:
        print("CSV 파일을 찾을 수 없습니다.")
        return

    print(f"총 {len(csv_files)}개의 CSV 파일을 처리합니다.")

    # 전체 텍스트 청크 저장
    all_chunks = []

    for csv_path in tqdm(csv_files, desc="CSV 처리 중"):
        chunks = process_csv_data(csv_path)
        all_chunks.extend(chunks)
        print(f"처리완료: {os.path.basename(csv_path)} - {len(chunks)}개 청크")

    # 벡터 데이터베이스에 저장
    if all_chunks:
        print(f"\n총 {len(all_chunks)}개 청크를 벡터DB에 저장 중...")

        texts = [chunk["text"] for chunk in all_chunks]
        metadatas = [chunk["metadata"] for chunk in all_chunks]

        batches = batch_by_tokens(texts, metadatas)

        for batch_texts, batch_metadatas in tqdm(batches, desc="임베딩 배치 저장 중"):
            try:
                vectordb.add_texts(texts=batch_texts, metadatas=batch_metadatas)
            except Exception as e:
                print(f"배치 저장 실패: {e}")
                continue

        print("벡터DB 저장 완료!")
    else:
        print("처리할 텍스트가 없습니다.")


if __name__ == "__main__":
    main()