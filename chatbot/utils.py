import base64
import os


def image_to_base64(image_path):
    """이미지 파일을 base64 문자열로 변환"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def summarize_image(image_path: str, base_dir: str = "") -> str:
    """이미지 파일명에서 확장자 제거하여 요약 생성"""
    if base_dir:
        rel_path = os.path.relpath(image_path, base_dir)
        return os.path.splitext(rel_path)[0]  # 확장자 제거
    return os.path.splitext(os.path.basename(image_path))[0]  # 확장자 제거
