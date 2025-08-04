import os
import json
import tempfile
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .rag_engine import run_chatbot, search_vector_db_image


@method_decorator(csrf_exempt, name="dispatch")
class ChatBotView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            query = body.get("query", "")
            history = body.get("history", [])

            result = run_chatbot(query, history=history)
            return JsonResponse({"response": result})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ModelSearchView(View):
    def post(self, request):
        image_file = request.FILES.get("image")
        if not image_file:
            return HttpResponseBadRequest("No image file uploaded.")

        print(f"Received image file: {image_file.name}")

        # 안전한 임시 파일 생성
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(image_file.name)[-1]
            ) as tmp_file:
                for chunk in image_file.chunks():
                    tmp_file.write(chunk)
                temp_path = tmp_file.name

            print(f"Saved file to: {temp_path}")

            # 벡터 DB 검색
            model_code = search_vector_db_image(temp_path)
            print(f"Model code found: {model_code}")

            return JsonResponse({"model_code": model_code})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
