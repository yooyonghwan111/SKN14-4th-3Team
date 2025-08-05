import os
import json
import asyncio
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
from concurrent.futures import ThreadPoolExecutor


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

def create_prompt_chain(llm):
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
                {
                    "keywords": ["키워드1", "키워드2", "키워드3"],
                    "main_topic": "주제",
                    "conditions": ["조건1"],
                    "details": ["세부사항1"]
                }
                """,
            ),
            ("human", "질문: {query}"),
        ]
    )
    return prompt | llm | StrOutputParser()


async def analyze_with_llm(query, llm, executor):
    chain = create_prompt_chain(llm)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, chain.invoke, {"query": query})


async def search_with_tavily(query, tavily_tool, executor):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, tavily_tool.invoke, {"query": query})


async def retrieve_from_vector(keywords, retriever, executor):
    loop = asyncio.get_running_loop()
    all_docs = []

    async def get_docs(keyword):
        try:
            return await loop.run_in_executor(executor, retriever.invoke, keyword)
        except Exception as e:
            print(f"[벡터 검색 오류] '{keyword}': {e}")
            return []

    tasks = [get_docs(k) for k in keywords]
    results = await asyncio.gather(*tasks)
    for docs in results:
        all_docs.extend(docs)
    return all_docs


def parse_analysis_result(result: str, fallback_query: str):
    try:
        data = json.loads(result)
        keywords = data.get("keywords", [])
        return keywords, result  # JSON 파싱 성공
    except json.JSONDecodeError as e:
        print(f"[LLM 분석 결과 JSON 파싱 실패]: {e}")
        return [fallback_query], ""  # fallback 처리


async def analyze_query_and_retrieve_async(query: str, retriever, llm, tavily_tool):
    all_contexts = []

    # with로 executor 명시적 자원관리
    with ThreadPoolExecutor() as executor:
        try:
            # LLM 분석 + 웹 검색 병렬 처리
            llm_task = analyze_with_llm(query, llm, executor)
            tavily_task = search_with_tavily(query, tavily_tool, executor)
            analysis_result, search_result = await asyncio.gather(llm_task, tavily_task)

            # 분석 결과에서 키워드 추출
            keywords, parsed_result = parse_analysis_result(analysis_result, query)

            # Tavily 검색 결과 → 문서화
            web_results = search_result.get("results", [])
            for item in web_results:
                content = item.get("content", "")
                url = item.get("url", "")
                if content:
                    doc = Document(
                        page_content=content,
                        metadata={"source": url, "title": item.get("title", "")},
                    )
                    all_contexts.append(doc)

            # 벡터 검색도 병렬 처리
            vector_docs = await retrieve_from_vector(keywords, retriever, executor)
            all_contexts.extend(vector_docs)

            return all_contexts, parsed_result

        except Exception as e:
            print(f"[전체 처리 오류]: {e}")
            return [], ""


def enhanced_chain(query: str, retriever, llm, cot_prompt, history=[]):
    tavily_tool = TavilySearch(max_results=5)
    context, analysis = asyncio.run(analyze_query_and_retrieve_async(query, retriever, llm, tavily_tool))
    
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
