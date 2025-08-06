#!/usr/bin/env python3
"""
Pinecone 매뉴얼 검색 테스트 코드 (기존 Chroma 코드와 동일한 기능)
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# 패키지 임포트
try:
    from pinecone import Pinecone
    import openai
    from langchain_openai import OpenAIEmbeddings
    USE_LANGCHAIN = True
except ImportError:
    try:
        from pinecone import Pinecone
        import openai
        USE_LANGCHAIN = False
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않음: {e}")
        print("pip install pinecone openai langchain-openai")
        exit(1)

# 환경변수 로드
load_dotenv()


class SimpleOpenAIEmbeddings:
    """간단한 OpenAI 임베딩 클래스 (LangChain 없이)"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def embed_query(self, text: str) -> List[float]:
        """텍스트를 임베딩으로 변환"""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            return []


class PineconeManualSearcher:
    """Pinecone 매뉴얼 검색 클래스 (기존 RAGIndexer와 동일한 역할)"""
    
    def __init__(self, index_name: str = "manuals-index", embedding_model: str = "text-embedding-3-small"):
        self.index_name = index_name
        self.embedding_model = embedding_model
        
        # API 키 확인
        pinecone_key = os.getenv("PINECONE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not pinecone_key:
            raise ValueError("PINECONE_API_KEY가 설정되지 않았습니다")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
        
        # Pinecone 클라이언트 초기화
        try:
            self.pc = Pinecone(api_key=pinecone_key)
            self.index = self.pc.Index(index_name)
            print(f"✅ Pinecone 연결 성공: {index_name}")
        except Exception as e:
            raise ValueError(f"Pinecone 연결 실패: {e}")
        
        # 임베딩 모델 초기화
        if USE_LANGCHAIN:
            self.embeddings = OpenAIEmbeddings(model=embedding_model)
        else:
            self.embeddings = SimpleOpenAIEmbeddings(openai_key, embedding_model)
        
        print(f"✅ 임베딩 모델 초기화: {embedding_model}")
    
    def similarity_search(self, query: str, k: int = 5, namespace: str = "", filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        유사도 검색 (기존 Chroma의 similarity_search와 동일한 인터페이스)
        
        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            namespace: 네임스페이스 (선택사항)
            filter: 메타데이터 필터 (선택사항)
                   예: {"brand": {"$eq": "sumsung"}}
                       {"model_name": {"$eq": "아가사랑_3kg_WA30DG2120EE"}}
        
        Returns:
            List of documents with page_content and metadata
        """
        try:
            # 쿼리 임베딩 생성
            if USE_LANGCHAIN:
                query_embedding = self.embeddings.embed_query(query)
            else:
                query_embedding = self.embeddings.embed_query(query)
            
            if not query_embedding:
                print("❌ 쿼리 임베딩 생성 실패")
                return []
            
            # Pinecone 검색
            search_params = {
                "vector": query_embedding,
                "top_k": k,
                "include_metadata": True,
                "namespace": namespace
            }
            
            # 메타데이터 필터 적용
            if filter:
                search_params["filter"] = filter
                print(f"🔍 필터 적용: {filter}")
            
            results = self.index.query(**search_params)
            
            # 결과를 Chroma와 동일한 형식으로 변환
            documents = []
            for match in results.matches:
                doc = {
                    'page_content': match.metadata.get('content', ''),
                    'metadata': {
                        'model_name': match.metadata.get('model_name', 'Unknown'),
                        'chunk_id': match.metadata.get('chunk_index', 'Unknown'),
                        'total_chunks': match.metadata.get('total_chunks', 'Unknown'),
                        'brand': match.metadata.get('brand', 'Unknown'),
                        'filename': match.metadata.get('filename', 'Unknown'),
                        'content_type': match.metadata.get('content_type', 'pdf'),
                        'score': match.score  # 추가: 유사도 점수
                    }
                }
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        try:
            return self.index.describe_index_stats()
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {}


class PineconeConfig:
    """설정 클래스 (기존 IndexConfig와 동일한 역할)"""
    
    def __init__(self, index_name: str, embedding_model: str, namespace: str = ""):
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.namespace = namespace


class PineconeIndexer:
    """
    Pinecone 인덱서 클래스 (기존 RAGIndexer와 동일한 인터페이스)
    vectordb 속성을 통해 검색 기능 제공
    """
    
    def __init__(self, config: PineconeConfig):
        self.config = config
        
        # vectordb 속성으로 검색 클래스 제공 (기존 코드와의 호환성)
        self.vectordb = PineconeManualSearcher(
            index_name=config.index_name,
            embedding_model=config.embedding_model
        )


def search_manuals(query: str, k: int = 5, index_name: str = "manuals-index", namespace: str = "", filter: Dict[str, Any] = None):
    """
    매뉴얼 검색 함수 (기존 코드와 동일한 인터페이스)
    
    Args:
        query: 검색 쿼리
        k: 반환할 결과 수  
        index_name: Pinecone 인덱스 이름
        namespace: 네임스페이스 (선택사항)
        filter: 메타데이터 필터 (선택사항)
               예: {"brand": {"$eq": "sumsung"}}
                   {"model_name": {"$eq": "아가사랑_3kg_WA30DG2120EE"}}
    """
    EMBEDDINGS_MODEL = "text-embedding-3-small"
    
    # 설정 생성 (기존 IndexConfig와 동일한 방식)
    config = PineconeConfig(
        index_name=index_name,
        embedding_model=EMBEDDINGS_MODEL,
        namespace=namespace
    )
    
    # 인덱서 생성 및 실행 (기존 RAGIndexer와 동일한 방식)
    indexer = PineconeIndexer(config)
    
    print(f"🔍 검색 쿼리: '{query}'")
    print(f"📊 인덱스: {index_name}")
    if namespace:
        print(f"📁 네임스페이스: {namespace}")
    print("=" * 60)
    
    # 매뉴얼 검색 (기존 코드와 동일한 방식)
    docs = indexer.vectordb.similarity_search(query, k=k, namespace=namespace, filter=filter)
    
    if not docs:
        print("❌ 검색 결과가 없습니다")
        return
    
    print(f"✅ 검색 결과: {len(docs)}개")
    print("=" * 60)
    
    for i, doc in enumerate(docs):
        print(f"\n[TOP-{i + 1}]")
        print(f'모델명: {doc["metadata"].get("model_name", "Unknown")}')
        print(f'브랜드: {doc["metadata"].get("brand", "Unknown")}')
        print(f'파일명: {doc["metadata"].get("filename", "Unknown")}')
        print(f'청크 ID: {doc["metadata"].get("chunk_id", "Unknown")}')
        print(f'청크 (total): {doc["metadata"].get("total_chunks", "Unknown")}')
        print(f'유사도: {doc["metadata"].get("score", 0):.4f}')
        print(f"내용: {doc['page_content'][:200]}...")
        print("-" * 50)


def search_manuals_with_namespace(query: str, k: int = 5, namespace: str = "documents"):
    """
    네임스페이스 기반 매뉴얼 검색 (네임스페이스 업로더 사용한 경우)
    """
    return search_manuals(query, k, index_name="multimodal-rag", namespace=namespace)


def search_by_brand(query: str, brand: str, k: int = 5):
    """특정 브랜드에서만 검색하는 편의 함수"""
    filter_dict = {"brand": {"$eq": brand}}
    return search_manuals(query, k=k, filter=filter_dict)


def search_by_model(query: str, model_name: str, k: int = 5):
    """특정 모델에서만 검색하는 편의 함수"""
    filter_dict = {"model_name": {"$eq": model_name}}
    return search_manuals(query, k=k, filter=filter_dict)


def search_by_brand_and_model(query: str, brand: str, model_name: str, k: int = 5):
    """브랜드와 모델 둘 다 필터링하는 편의 함수"""
    filter_dict = {
        "brand": {"$eq": brand},
        "model_name": {"$eq": model_name}
    }
    return search_manuals(query, k=k, filter=filter_dict)


def test_index_connection():
    """인덱스 연결 테스트"""
    print("🔗 인덱스 연결 테스트")
    print("=" * 40)
    
    # 먼저 사용 가능한 인덱스들 확인
    try:
        from dotenv import load_dotenv
        load_dotenv()
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        print(f"📋 존재하는 인덱스: {existing_indexes}")
        print()
    except Exception as e:
        print(f"❌ 인덱스 목록 조회 실패: {e}")
        return
    
    # 기본적으로 확인할 인덱스들
    possible_indexes = ["manuals-index", "imgs-index", "multimodal-rag"]
    
    for idx_name in possible_indexes:
        if idx_name not in existing_indexes:
            print(f"⚠️ {idx_name}: 존재하지 않음")
            continue
            
        try:
            config = PineconeConfig(
                index_name=idx_name,
                embedding_model="text-embedding-3-small"
            )
            indexer = PineconeIndexer(config)
            stats = indexer.vectordb.get_index_stats()
            
            print(f"✅ {idx_name}: {stats.get('total_vector_count', 0):,}개 벡터")
            
            # 네임스페이스 정보
            namespaces = stats.get('namespaces', {})
            if namespaces:
                for ns_name, ns_info in namespaces.items():
                    ns_display = ns_name if ns_name else "default"
                    print(f"   📁 {ns_display}: {ns_info['vector_count']:,}개")
            
        except Exception as e:
            print(f"❌ {idx_name}: 연결 실패")
    
    print("=" * 40)


def main():
    """메인 실행 함수"""
    print("🎯 Pinecone 매뉴얼 검색 테스트")
    print("=" * 50)
    
    # 인덱스 연결 테스트
    test_index_connection()
    
    # 존재하는 인덱스 확인
    try:
        from dotenv import load_dotenv
        load_dotenv()
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        existing_indexes = [idx.name for idx in pc.list_indexes()]
    except Exception as e:
        print(f"❌ 인덱스 목록 조회 실패: {e}")
        return
    
    print("\n" + "=" * 50)
    print("📚 매뉴얼 검색 실행")
    print("=" * 50)
    
    # 기존 코드와 동일한 검색 실행
    query = "아가사랑_3kg_WA30DG2120EE의 주의 사항"
    
    # 존재하는 인덱스에서만 검색
    search_success = False
    
    if "manuals-index" in existing_indexes:
        try:
            print("\n🔍 manuals-index에서 검색 (필터 없음)")
            search_manuals(query, k=3, index_name="manuals-index")
            
            print("\n🎯 아가사랑 모델만 검색")
            search_by_model("주의 사항", "아가사랑_3kg_WA30DG2120EE", k=3)
            
            print("\n🏢 삼성 브랜드만 검색") 
            search_by_brand("에너지 절약", "sumsung", k=3)
            
            search_success = True
        except Exception as e:
            print(f"❌ manuals-index 검색 실패: {e}")
    
    if "multimodal-rag" in existing_indexes:
        try:
            print(f"\n🔍 multimodal-rag 인덱스의 documents 네임스페이스에서 검색")
            search_manuals_with_namespace(query, k=3)
            search_success = True
        except Exception as e:
            print(f"❌ multimodal-rag 검색 실패: {e}")
    
    if not search_success:
        print("❌ 사용 가능한 매뉴얼 인덱스가 없습니다")
        print(f"💡 존재하는 인덱스: {existing_indexes}")
    else:
        print("\n🎉 매뉴얼 검색 테스트 완료!")


def interactive_search():
    """대화형 검색 모드"""
    print("🔍 대화형 검색 모드")
    print("종료하려면 'quit' 입력")
    print("=" * 40)
    
    while True:
        try:
            query = input("\n검색 쿼리: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 검색을 종료합니다")
                break
            
            if not query:
                continue
            
            # 기본 검색
            search_manuals(query, k=3)
            
        except KeyboardInterrupt:
            print("\n👋 검색을 종료합니다")
            break
        except Exception as e:
            print(f"❌ 검색 오류: {e}")


if __name__ == "__main__":
    # 기본 테스트 실행
    main()
    
    # 추가 대화형 검색 (선택사항)
    print("\n" + "=" * 50)
    user_input = input("대화형 검색을 시작하시겠습니까? (y/n): ")
    
    if user_input.lower().startswith('y'):
        interactive_search()