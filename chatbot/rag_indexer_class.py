import os
import logging
from tqdm import tqdm
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from langchain_chroma.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from chatbot.utils import image_to_base64, summarize_image
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@dataclass
class IndexConfig:
    """인덱싱 설정을 위한 데이터 클래스"""

    persistent_directory: str = ""
    collection_name: str = ""
    embedding_model: str = ""
    figures_directory: str = ""
    supported_extensions: List[str] = None

    def __post_init__(self):
        if self.supported_extensions is None:
            # 소문자 입력
            self.supported_extensions = [".png", ".jpg", ".jpeg", ".bmp"]


class RAGIndexer:
    """RAG 인덱서 클래스"""

    def __init__(self, config: IndexConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.embeddings = OpenAIEmbeddings(model=config.embedding_model)
        self.vectordb = self._initialize_vectordb()

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_vectordb(self) -> Chroma:
        """벡터 데이터베이스 초기화"""
        try:
            vectordb = Chroma(
                collection_name=self.config.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.config.persistent_directory,
            )
            self.logger.info(
                f"Vector database initialized: {self.config.collection_name}"
            )
            return vectordb
        except Exception as e:
            self.logger.error(f"Failed to initialize vector database: {e}")
            raise

    def _get_image_files(self) -> List[Path]:
        """이미지 파일 목록 가져오기"""
        figures_dir = Path(self.config.figures_directory)

        if not figures_dir.exists():
            raise FileNotFoundError(f"Directory not found: {figures_dir}")

        image_files = []
        for extension in self.config.supported_extensions:
            pattern = f"**/*{extension}"
            image_files.extend(figures_dir.glob(pattern))
            image_files.extend(figures_dir.glob(f"**/*{extension.upper()}"))

        self.logger.info(f"Found {len(image_files)} image files")
        return image_files

    def _process_single_image(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """단일 이미지 처리"""
        try:
            # 이미지를 base64로 변환
            b64_image = image_to_base64(str(image_path))
            # base64 길이 800으로 제한
            b64_image = b64_image[:800]

            # 이미지 요약 생성
            model_name = summarize_image(str(image_path))

            return {
                "text": b64_image,
                "metadata": {
                    "model_name": model_name,
                },
            }
        except Exception as e:
            self.logger.error(f"Failed to process image {image_path}: {e}")
            return None

    def _batch_add_to_vectordb(
        self, processed_images: List[Dict[str, Any]], batch_size: int = 100
    ) -> None:
        """배치 단위로 벡터 데이터베이스에 추가"""
        for i in range(0, len(processed_images), batch_size):
            batch = processed_images[i : i + batch_size]

            texts = [item["text"] for item in batch]
            metadatas = [item["metadata"] for item in batch]

            try:
                self.vectordb.add_texts(texts=texts, metadatas=metadatas)
                self.logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} items")
            except Exception as e:
                self.logger.error(f"Failed to add batch {i//batch_size + 1}: {e}")
                raise

    def index_images(self, batch_size: int = 100) -> None:
        """이미지 인덱싱 메인 메서드"""
        try:
            # 이미지 파일 목록 가져오기
            image_files = self._get_image_files()

            if not image_files:
                self.logger.warning("No image files found")
                return

            # 이미지 처리
            processed_images = []
            self.logger.info("Processing images...")

            for image_path in tqdm(image_files, desc="Processing images"):
                processed_image = self._process_single_image(image_path)
                if processed_image:
                    processed_images.append(processed_image)

            # 성공적으로 처리된 이미지 수 로그
            self.logger.info(
                f"Successfully processed {len(processed_images)}/{len(image_files)} images"
            )

            # 벡터 데이터베이스에 배치 저장
            if processed_images:
                self.logger.info("Adding to vector database...")
                self._batch_add_to_vectordb(processed_images, batch_size)
                self.logger.info("Indexing completed successfully")
            else:
                self.logger.warning("No images were successfully processed")

        except Exception as e:
            self.logger.error(f"Indexing failed: {e}")
            raise

    def search_and_show(self, user_img: str, k: int = 1) -> str:
        """쿼리로 검색하고 결과 표시"""

        # base64 길이 800으로 제한
        user_img = user_img[:800]

        # 유사도 검색
        results = self.vectordb.similarity_search_with_score(user_img, k=k)

        if not results:
            return -1

        doc, score = results[0]
        if score <= 0.3:
            return doc.metadata.get("model_name", -1)
        else:
            return -1

    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            docs = self.vectordb._collection.get()
            return {
                "total_documents": len(docs.get("ids", [])),
                "collection_name": self.config.collection_name,
                "persistent_directory": self.config.persistent_directory,
            }
        except Exception as e:
            self.logger.error(f"Failed to get collection info: {e}")
            return {}

    def clear_collection(self) -> None:
        """컬렉션 초기화"""
        try:
            self.vectordb._collection.delete()
            self.logger.info("Collection cleared successfully")
        except Exception as e:
            self.logger.error(f"Failed to clear collection: {e}")
            raise
