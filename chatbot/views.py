import os
import json
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

        # 임시 저장
        temp_path = f"/tmp/{image_file.name}"
        with open(temp_path, "wb+") as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        try:
            model_code = search_vector_db_image(temp_path)
            return JsonResponse({"model_code": model_code})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
