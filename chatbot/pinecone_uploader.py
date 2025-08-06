import os
import sys
import hashlib
import time
from tqdm import tqdm
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from pdfminer.high_level import extract_text
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from utils import image_to_base64

# 환경변수 로드
load_dotenv()

# 경로 설정
CURRENT_DIR = Path(__file__).parent
IMG_DIR = CURRENT_DIR / "data" / "imgs"
PDF_DIR = CURRENT_DIR / "data" / "manuals"

print(f"📁 이미지: {IMG_DIR}")
print(f"📁 PDF: {PDF_DIR}")

# =============================================================================
# 유틸리티 함수
# =============================================================================


def extract_model_name(filename: str) -> str:
    """파일명에서 모델명 추출"""
    name = os.path.splitext(filename)[0]
    parts = name.split("_")

    # 숫자나 manual이 나오기 전까지만
    model_parts = []
    for part in parts:
        if part.isdigit() or "manual" in part.lower():
            break
        model_parts.append(part)

    return "_".join(model_parts) if model_parts else name


# =============================================================================
# 간단한 업로더 클래스 (최신 Pinecone API)
# =============================================================================


class PineconeUploader:
    def __init__(self):
        pinecone_key = os.getenv("PINECONE_API_KEY")
        self.pc = Pinecone(api_key=pinecone_key)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def get_or_create_index(self, index_name: str):
        """인덱스 생성 또는 가져오기"""
        try:
            # 기존 인덱스 확인
            existing_indexes = [index.name for index in self.pc.list_indexes()]

            if index_name not in existing_indexes:
                print(f"인덱스 생성: {index_name}")
                self.pc.create_index(
                    name=index_name,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            else:
                print(f"기존 인덱스 사용: {index_name}")

            return self.pc.Index(index_name)

        except Exception as e:
            print(f"인덱스 처리 실패: {e}")
            raise

    def check_files(self):
        """파일 확인"""
        print("\n파일 확인")
        print("=" * 40)

        # 이미지 확인
        if IMG_DIR.exists():
            img_files = []
            for ext in [".jpg", ".jpeg", ".png"]:
                img_files.extend(IMG_DIR.glob(f"**/*{ext}"))
                img_files.extend(IMG_DIR.glob(f"**/*{ext.upper()}"))

            print(f"이미지: {len(img_files)}개")

            brands = {}
            for img in img_files:
                brand = img.parent.name
                brands[brand] = brands.get(brand, 0) + 1

            for brand, count in brands.items():
                print(f"  {brand}: {count}개")
        else:
            print(f"이미지 없음: {IMG_DIR}")

        # PDF 확인
        if PDF_DIR.exists():
            pdf_files = list(PDF_DIR.glob("**/*.pdf"))
            print(f"PDF: {len(pdf_files)}개")

            brands = {}
            for pdf in pdf_files:
                brand = pdf.parent.name
                brands[brand] = brands.get(brand, 0) + 1

            for brand, count in brands.items():
                print(f"  {brand}: {count}개")
        else:
            print(f"PDF 없음: {PDF_DIR}")

        print("=" * 40)

    def upload_images(self):
        """이미지 업로드"""
        print("\n🖼️ 이미지 업로드 시작")

        if not IMG_DIR.exists():
            print("❌ 이미지 디렉토리 없음")
            return False

        # 이미지 파일 수집
        img_files = []
        for ext in [".jpg", ".jpeg", ".png"]:
            img_files.extend(IMG_DIR.glob(f"**/*{ext}"))
            img_files.extend(IMG_DIR.glob(f"**/*{ext.upper()}"))

        if not img_files:
            print("❌ 이미지 파일 없음")
            return False

        print(f"📷 처리할 이미지: {len(img_files)}개")

        # 인덱스 준비
        index = self.get_or_create_index("imgs-index")

        # 이미지 처리 및 업로드
        vectors = []
        for img_file in tqdm(img_files, desc="이미지 처리"):
            try:
                # base64 변환
                b64_image = image_to_base64(str(img_file))
                if not b64_image:
                    continue

                b64_image = b64_image[:800]  # 길이 제한

                # 임베딩 생성
                embedding = self.embeddings.embed_query(b64_image)

                if not embedding:
                    continue

                # 메타데이터
                model_name = extract_model_name(img_file.name)
                brand = img_file.parent.name

                vector = {
                    "id": f"img_{hashlib.md5(str(img_file).encode()).hexdigest()}",
                    "values": embedding,
                    "metadata": {
                        "model_name": model_name,
                        "brand": brand,
                        "filename": img_file.name,
                        "content_type": "image",
                    },
                }
                vectors.append(vector)

            except Exception as e:
                print(f"❌ 이미지 처리 실패 {img_file.name}: {e}")
                continue

        print(f"✅ 처리된 이미지: {len(vectors)}개")

        # Pinecone 업로드
        if vectors:
            try:
                # 배치로 업로드
                batch_size = 50
                for i in tqdm(range(0, len(vectors), batch_size), desc="업로드"):
                    batch = vectors[i : i + batch_size]
                    index.upsert(vectors=batch)

                time.sleep(3)
                stats = index.describe_index_stats()
                print(f"🎉 이미지 업로드 완료! 총: {stats['total_vector_count']}개")
                return True

            except Exception as e:
                print(f"❌ 업로드 실패: {e}")
                return False

        return False

    def upload_pdfs(self):
        """PDF 업로드"""
        print("\n📚 PDF 업로드 시작")

        if not PDF_DIR.exists():
            print("❌ PDF 디렉토리 없음")
            return False

        pdf_files = list(PDF_DIR.glob("**/*.pdf"))

        if not pdf_files:
            print("❌ PDF 파일 없음")
            return False

        print(f"📚 처리할 PDF: {len(pdf_files)}개")

        # 인덱스 준비
        index = self.get_or_create_index("manuals-index")

        # PDF 처리
        all_vectors = []
        for pdf_file in pdf_files:
            try:
                print(f"📖 처리 중: {pdf_file.name}")

                # 텍스트 추출
                text = extract_text(str(pdf_file))
                if not text.strip():
                    print(f"❌ 텍스트 없음: {pdf_file.name}")
                    continue

                # 간단한 청크 분할 (1000자씩)
                chunk_size = 1000
                chunks = [
                    text[i : i + chunk_size] for i in range(0, len(text), chunk_size)
                ]

                # 청크별 벡터 생성
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 50:
                        continue

                    try:
                        embedding = self.embeddings.embed_query(chunk)

                        if not embedding:
                            continue

                        model_name = extract_model_name(pdf_file.name)
                        brand = pdf_file.parent.name
                        pdf_hash = hashlib.md5(str(pdf_file).encode()).hexdigest()[:8]

                        vector = {
                            "id": f"pdf_{pdf_hash}_chunk_{i}",
                            "values": embedding,
                            "metadata": {
                                "model_name": model_name,
                                "brand": brand,
                                "filename": pdf_file.name,
                                "chunk_index": i,
                                "content": chunk,
                                "content_type": "pdf",
                            },
                        }
                        all_vectors.append(vector)

                    except Exception as e:
                        print(f"❌ 청크 처리 실패: {e}")
                        continue

                print(
                    f"✅ {pdf_file.name}: {len([v for v in all_vectors if pdf_hash in v['id']])}개 청크"
                )

            except Exception as e:
                print(f"❌ PDF 처리 실패 {pdf_file.name}: {e}")
                continue

        print(f"✅ 총 처리된 청크: {len(all_vectors)}개")

        # Pinecone 업로드
        if all_vectors:
            try:
                batch_size = 100
                for i in tqdm(range(0, len(all_vectors), batch_size), desc="업로드"):
                    batch = all_vectors[i : i + batch_size]
                    index.upsert(vectors=batch)

                time.sleep(3)
                stats = index.describe_index_stats()
                print(f"🎉 PDF 업로드 완료! 총: {stats['total_vector_count']}개")
                return True

            except Exception as e:
                print(f"❌ 업로드 실패: {e}")
                return False

        return False

    def upload_all(self):
        """전체 업로드"""
        print("전체 업로드 시작")
        self.check_files()

        img_result = self.upload_images()
        pdf_result = self.upload_pdfs()

        print("\n📊 결과")
        print(f"이미지: {'✅' if img_result else '❌'}")
        print(f"PDF: {'✅' if pdf_result else '❌'}")

        if img_result and pdf_result:
            print("🎉 모든 업로드 완료!")
        else:
            print("일부 실패")


# =============================================================================
# 메인 실행
# =============================================================================


def main():
    print("Pinecone 업로더")
    print("=" * 40)

    if len(sys.argv) < 2:
        action = "check"
    else:
        action = sys.argv[1]

    try:
        uploader = PineconeUploader()

        if action == "check":
            uploader.check_files()
            print("\n💡 사용법:")
            print("python pinecone_uploader.py all      # 전체")
            print("python pinecone_uploader.py images   # 이미지만")
            print("python pinecone_uploader.py pdfs     # PDF만")

        elif action == "all":
            uploader.upload_all()

        elif action == "images":
            uploader.upload_images()

        elif action == "pdfs":
            uploader.upload_pdfs()
        else:
            print(f"알 수 없는 명령: {action}")

    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
