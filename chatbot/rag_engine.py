import os
import json
import logging
from dotenv import load_dotenv
from pdfminer.high_level import extract_text
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from .rag_indexer_class import IndexConfig, RAGIndexer
from .utils import image_to_base64


# pdfminer 경고 무시
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# 환경변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_vector_db_image(img_path):
    """백터 디비에서 이미지의 모델을 가져온다"""

    # 설정 생성
    config = IndexConfig(
        persistent_directory="./chroma",
        collection_name="imgs",
        embedding_model="text-embedding-3-small",
    )

    # 인덱서 생성 및 실행
    indexer = RAGIndexer(config)

    # 이미지 로드해서 모델명 검색
    img_base64 = image_to_base64(img_path)
    print(f"Searching for image1212: {img_path}")

    # 유사도 검색
    model_nm = indexer.search_and_show(img_base64)
    return model_nm


def extract_text_from_pdf(pdf_path):
    """PDF 텍스트 추출"""
    try:
        return extract_text(pdf_path)
    except Exception as e:
        print(f"PDF 읽기 실패 {pdf_path}: {e}")
        return ""


def analyze_query_and_retrieve(query: str, retriever, llm):
    # 질문 분석 프롬프트
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 사용자의 질문을 분석하는 전문가입니다. 
        주어진 질문에서 다음을 추출하세요:
        
        1. 주요 키워드 (3-5개)
        2. 질문의 핵심 주제
        3. 구체적인 조건이나 요구사항
        4. 답변에서 다뤄야 할 세부 사항들
        
        JSON 형식으로 출력하세요:
        {{
            "keywords": ["키워드1", "키워드2", "키워드3"],
            "main_topic": "주제",
            "conditions": ["조건1"],
            "details": ["세부사항1"]
        }}""",
            ),
            ("human", "질문: {query}"),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    analysis_result = chain.invoke({"query": query})

    # JSON 파싱
    try:
        data = json.loads(analysis_result)
        keywords = data.get("keywords", [])
    except Exception:
        keywords = [query]

    all_contexts = []

    # TavilySearch로 웹 검색 도구 설정
    tavily_tool = TavilySearch(max_results=5)

    try:
        # Tavily에서 검색
        search_result = tavily_tool.invoke({"query": query})

        # 'results' 리스트 추출
        web_results = search_result.get("results", [])

        # 각 결과를 Document로 변환
        for item in web_results:
            content = item.get("content", "")
            url = item.get("url", "")

            if content:  # 내용이 있으면 추가
                doc = Document(
                    page_content=content,
                    metadata={"source": url, "title": item.get("title", "")},
                )
                all_contexts.append(doc)
    except Exception as e:
        print(f"웹 검색 오류: {e}")

    # 기존 벡터 retriever도 검색
    for keyword in keywords:
        try:
            docs = retriever.invoke(keyword)
            print(f"검색어 '{keyword}'에 대한 검색 결과: {len(docs)}개 문서")
            all_contexts.extend(docs)
        except Exception as e:
            print(f"벡터 검색 오류: {e}")
            continue

    return all_contexts, analysis_result


def enhanced_chain(query: str, retriever, llm, cot_prompt, history=[]):
    context, analysis = analyze_query_and_retrieve(query, retriever, llm)
    prompt_value = cot_prompt.invoke(
        {"query": query, "analysis": analysis, "context": context}
    )

    prompt_str = prompt_value.to_string()

    # history + 현재 질문 prompt를 합쳐 messages 구성
    messages = history + [{"role": "user", "content": prompt_str}]

    # LLM에 messages 전달
    response = llm.invoke(messages)

    return response


def run_chatbot(query, image_path=None, history=[]):
    EMBEDDINGS_MODEL = "text-embedding-3-small"
    COLLECTION_NAME = "manuals"
    VECTOR_DB_DIR = "./chroma"

    # 설정 생성
    config = IndexConfig(
        persistent_directory=VECTOR_DB_DIR,
        collection_name=COLLECTION_NAME,
        embedding_model=EMBEDDINGS_MODEL,
    )

    # 인덱서 생성 및 실행
    indexer = RAGIndexer(config)

    retriever = indexer.vectordb.as_retriever(
        search_type="mmr", search_kwargs={"k": 8, "fetch_k": 20}
    )

    if image_path:
        model_code = search_vector_db_image(image_path)
        if model_code == -1:
            query = f"{query} (모델코드: 확인불가)"
        else:
            query = f"{query} (모델코드: {model_code})"

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3)

    cot_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
            Elaborate on the topic using a Tree of Thoughts and backtrack when necessary to construct a clear, cohesive Chain of Thought reasoning.
            당신은 스마트한 가전 도우미입니다. 질문을 분석한 후에 관련 정보를 수집한 후, 체계적으로 답변하세요.:
            ## 답변 지침
            - 조건들을 나열하기보다는 통합하여 하나의 흐름으로 설명하십시오.
            - 반복되거나 유사한 내용을 중복해서 설명하지 마십시오.
            - 논리적 구조를 갖춘 명확한 문단 형태로 답변하십시오.
            - 필요 시 예시나 유사 상황을 들어 이해를 도우십시오.

            
            예시 출력 :
            
       
            - [체계적인 통합 설명을 한 문단 이상으로 기술]

            ### 추가 안내
            - [관련된 팁이나 참고 정보가 있으면 제공]
            """,
            ),
            (
                "human",
                """
            질문: {query}
            분석: {analysis}
            컨텍스트: {context}
            """,
            ),
        ]
    )

    result = enhanced_chain(query, retriever, llm, cot_prompt, history=history)
    return result.content
