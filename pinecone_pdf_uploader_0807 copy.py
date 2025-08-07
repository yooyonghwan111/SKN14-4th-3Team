# import glob
# import logging
# import os
# import tiktoken
# from tqdm import tqdm
# from pdfminer.high_level import extract_text
# from langchain_pinecone import PineconeVectorStore  # Chroma 대신 Pinecone import
# from langchain_openai import OpenAIEmbeddings
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from dotenv import load_dotenv
# from pinecone import Pinecone  # Pinecone 클라이언트 import


# load_dotenv()

# from google.colab import userdata
# import os

# os.environ['OPENAI_API_KEY'] = userdata.get('OPENAI_API_KEY')
# os.environ['PINECONE_API_KEY'] = userdata.get('PINECONE_API_KEY')


import glob
import logging
import os
import tiktoken
from tqdm import tqdm
from pdfminer.high_level import extract_text
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



# pdfminer 경고 무시
logging.getLogger("pdfminer").setLevel(logging.ERROR)


def get_pdf_files(base_dir):
    """하위 디렉토리 모든 PDF 파일 목록 가져오기"""
    pdf_pattern = os.path.join(base_dir, "**", "*.pdf")
    return glob.glob(pdf_pattern, recursive=True)


def extract_text_from_pdf(pdf_path):
    """PDF 텍스트 추출하기"""
    try:
        text = extract_text(pdf_path)
        return text
    except Exception as e:
        print(f"PDF 읽기 실패 {pdf_path}: {e}")
        return ""


def process_pdf_text(pdf_path):
    """PDF 텍스트 처리 및 청크 분할"""
    # PDF에서 텍스트 추출
    text = extract_text_from_pdf(pdf_path)

    if not text.strip():
        return []

    # 파일명에서 모델명 추출
    filename = os.path.basename(pdf_path)
    model_name = filename.replace(".pdf", "")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    )

    # 텍스트 청크로 분할
    chunks = text_splitter.split_text(text)

    # 각 청크에 메타데이터 추가
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        processed_chunks.append(
            {
                "text": chunk,
                "metadata": {
                    "model_name": model_name,
                    "chunk_id": i + 1,
                    "total_chunks": len(chunks),
                },
            }
        )

    return processed_chunks


MAX_TOKENS_PER_REQUEST = 300000
# text-embedding-3-small에 맞는 encoding
encoding = tiktoken.get_encoding("cl100k_base")


def batch_by_tokens(texts, metadatas, max_tokens=MAX_TOKENS_PER_REQUEST):
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
    # """메인 실행 함수"""
    # BASE_DIR = "/content/Bespoke_AI_세탁기_21kg_WF21CB6650BW.pdf"
    # EMBEDDINGS_MODEL = "text-embedding-3-small"
    # INDEX_NAME = "manual-test-index"  # COLLECTION_NAME 대신 INDEX_NAME 사용

    # # Pinecone 클라이언트 초기화
    # pc = Pinecone(api_key=PINECONE_API_KEY)

    # embeddings = OpenAIEmbeddings(model=EMBEDDINGS_MODEL)

    # # Pinecone 벡터스토어 초기화
    # vectordb = PineconeVectorStore(
    #     index=pc.Index(INDEX_NAME),  # 기존 인덱스 사용
    #     embedding=embeddings,
    # )


    """메인 실행 함수"""
    BASE_DIR = "C:\Workspaces\SKN14-4th-3Team_backup\data"
    EMBEDDINGS_MODEL = "text-embedding-3-small"
    INDEX_NAME = "manual-index-0807"

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





    """PDF 텍스트 인덱싱"""
    # PDF 파일 목록 가져오기
    pdf_files = get_pdf_files(BASE_DIR)

    if not pdf_files:
        print("PDF 파일을 찾을 수 없습니다.")

    print(f"총 {len(pdf_files)}개의 PDF 파일을 처리합니다.")

    # 전체 텍스트 청크 저장
    all_chunks = []

    for pdf_path in tqdm(pdf_files, desc="PDF 처리 중"):
        chunks = process_pdf_text(pdf_path)
        all_chunks.extend(chunks)
        print(f"처리완료: {os.path.basename(pdf_path)} - {len(chunks)}개 청크")

    # 벡터 데이터베이스에 저장
    if all_chunks:
        print(f"\n총 {len(all_chunks)}개 청크를 벡터DB에 저장 중...")

        texts = [chunk["text"] for chunk in all_chunks]
        metadatas = [chunk["metadata"] for chunk in all_chunks]

        batches = batch_by_tokens(texts, metadatas)

        for batch_texts, batch_metadatas in tqdm(batches, desc="임베딩 배치 저장 중"):
            vectordb.add_texts(texts=batch_texts, metadatas=batch_metadatas)

        print("벡터DB 저장 완료!")
    else:
        print("처리할 텍스트가 없습니다.")


if __name__ == "__main__":
    main()