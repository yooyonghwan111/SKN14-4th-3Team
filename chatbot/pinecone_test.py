import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings

# 환경변수 로드
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
EMBEDDINGS_MODEL = "text-embedding-3-small"
INDEX_NAME = "manuals-index"


class PineConeIndexConfig:
    def __init__(self, api: str, index_name: str, embedding_model: str):
        self.api = api
        self.index_name = index_name
        self.embedding_model = embedding_model


class PineConeIndexer:
    def __init__(self, config: PineConeIndexConfig):
        self.config = config

        # Pinecone 클라이언트 초기화
        self.pc = Pinecone(api_key=config.api)
        self.index = self.pc.Index(config.index_name)

        # 임베딩 모델 초기화
        self.embeddings = OpenAIEmbeddings(model=config.embedding_model)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Args:
            query: 검색 쿼리
            k: 반환할 결과 수

        Returns:
            List of documents with page_content and metadata
        """
        try:
            query_embedding = self.embeddings.embed_query(query)

            # Pinecone 검색
            search_params = {
                "vector": query_embedding,
                "top_k": k,
                "include_metadata": True,
            }

            results = self.index.query(**search_params)

            # 결과를 Chroma와 동일한 형식으로 변환
            documents = []
            for match in results.matches:
                doc = {
                    "page_content": match.metadata.get("content", ""),
                    "metadata": {
                        "model_name": match.metadata.get("model_name", "Unknown"),
                        "chunk_id": match.metadata.get("chunk_index", "Unknown"),
                        "total_chunks": match.metadata.get("total_chunks", "Unknown"),
                        "brand": match.metadata.get("brand", "Unknown"),
                        "filename": match.metadata.get("filename", "Unknown"),
                        "content_type": match.metadata.get("content_type", "pdf"),
                        "score": match.score,  # 추가: 유사도 점수
                    },
                }
                documents.append(doc)

            return documents

        except Exception as e:
            print(f"검색 실패: {e}")
            return []


def search_manuals(
    query: str,
    k: int = 5,
):
    """
    매뉴얼 검색 함수

    Args:
        query: 검색 쿼리
        k: 반환할 결과 수
        index_name: Pinecone 인덱스 이름
    """

    # 설정 생성
    config = PineConeIndexConfig(
        api=PINECONE_API_KEY, index_name=INDEX_NAME, embedding_model=EMBEDDINGS_MODEL
    )

    # 인덱서 생성 및 실행
    indexer = PineConeIndexer(config)

    # 매뉴얼 검색
    docs = indexer.similarity_search(query, k=k)

    print(f"✅ 검색 결과: {len(docs)}개")
    print("=" * 60)

    for i, doc in enumerate(docs):
        print(f"\n[TOP-{i + 1}]")
        print(f'모델명: {doc["metadata"].get("model_name", "Unknown")}')
        print(f'브랜드: {doc["metadata"].get("brand", "Unknown")}')
        print(f'파일명: {doc["metadata"].get("filename", "Unknown")}')
        print(f'유사도: {doc["metadata"].get("score", 0):.4f}')
        print(f"내용: {doc['page_content'][:200]}...")
        print("-" * 50)


def main():
    # 먼저 사용 가능한 인덱스들 확인
    pc = Pinecone(PINECONE_API_KEY)
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    print(f"존재하는 인덱스: {existing_indexes}")

    # 기본적으로 확인할 인덱스들
    # "manuals-index"
    # "imgs-index"

    # 기존 코드와 동일한 검색 실행
    query = "아가사랑_3kg_WA30DG2120EE의 주의 사항"

    search_manuals(query, k=3)


if __name__ == "__main__":
    main()
