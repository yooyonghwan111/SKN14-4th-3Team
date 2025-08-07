# Contributing Guidelines

이 프로젝트의 실행을 위한 가이드라인 입니다.

## 실행방법

```python
conda create -n skn4th python=3.12 -y
conda activate skn4th
pip install -r requirements.txt

# commit 전 코드포멧팅 체크
pre-commit install
```

### 루트디렉토리에 `.env` 포함하기

```
OPENAI_API_KEY
TAVILY_API_KEY
SECRET_KEY
ALLOWED_HOSTS
DEBUG
```

### chatbot앱 아래에 `chroma` 백터 디비 포함하기
- chroma는 3rd project에서 생성하시면 됩니다.
- [chroma DB 링크](https://huggingface.co/rwr9857/SKN14-3rd-3Team/tree/main)