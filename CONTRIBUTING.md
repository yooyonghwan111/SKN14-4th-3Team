# Contributing Guidelines

이 프로젝트의 실행을 위한 가이드라인 입니다.

## 실행방법

```python
conda create -n skn4th python=3.12 -y
conda activate skn4th
pip install -r requirements.txt

# commit 전 코드포멧팅 체크 (선택)
pre-commit install
```

### 루트디렉토리에 `.env` 포함하기

```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
SECRET_KEY=your_django_secret_key
ALLOWED_HOSTS=*
DEBUG=0
```

### chatbot앱 아래에 `chroma` 백터 디비 포함하기
- chroma는 3rd project에서 생성하시면 됩니다.
- [chroma DB 링크](https://huggingface.co/rwr9857/SKN14-3rd-3Team/tree/main)

# 도커 실행방법

## 도커 파일 실행 방법

```bash
$ docker build -t skn4th_app_image . 
$ docker run --name skn4th_app --env-file .env -p 8000:8000 skn4th_app_image
```

## docker-compose 실행 방법

```bash
$ docker-compose up -d
```
