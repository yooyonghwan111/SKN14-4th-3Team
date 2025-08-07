import os
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from .models import Conversation, Message, UploadedImage
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


@method_decorator(csrf_exempt, name="dispatch")
class ConversationView(View):
    """대화 관리 API"""
    
    def get(self, request):
        """사용자의 대화 목록 조회"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        conversations = Conversation.objects.filter(user=request.user, is_active=True)
        conversation_list = []
        
        for conv in conversations:
            conversation_list.append({
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': conv.messages.count()
            })
        
        return JsonResponse({"conversations": conversation_list})
    
    def post(self, request):
        """새 대화 생성"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        try:
            body = json.loads(request.body)
            title = body.get("title", "새 대화")
            
            conversation = Conversation.objects.create(
                user=request.user,
                title=title
            )
            
            return JsonResponse({
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class MessageView(View):
    """메시지 관리 API"""
    
    def get(self, request, conversation_id):
        """특정 대화의 메시지 조회"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        messages = conversation.messages.all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat()
            })
        
        return JsonResponse({
            "conversation_id": conversation.id,
            "title": conversation.title,
            "messages": message_list
        })
    
    def post(self, request, conversation_id):
        """메시지 전송 및 챗봇 응답"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            body = json.loads(request.body)
            user_message = body.get("message", "")
            
            if not user_message:
                return JsonResponse({"error": "메시지가 비어있습니다."}, status=400)
            
            # 사용자 메시지 저장
            user_msg = Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_message
            )
            
            # 대화 히스토리 가져오기
            history = []
            for msg in conversation.messages.all():
                history.append({
                    'role': msg.role,
                    'content': msg.content
                })
            
            # 챗봇 응답 생성
            chatbot_response = run_chatbot(user_message, history=history)
            
            # 챗봇 응답 저장
            assistant_msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=chatbot_response
            )
            
            # 대화 제목 업데이트 (첫 번째 메시지인 경우)
            if conversation.messages.count() == 2:  # 사용자 메시지 + 챗봇 응답
                conversation.title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                conversation.save()
            
            return JsonResponse({
                "user_message": {
                    'id': user_msg.id,
                    'role': user_msg.role,
                    'content': user_msg.content,
                    'created_at': user_msg.created_at.isoformat()
                },
                "assistant_message": {
                    'id': assistant_msg.id,
                    'role': assistant_msg.role,
                    'content': assistant_msg.content,
                    'created_at': assistant_msg.created_at.isoformat()
                }
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ConversationDetailView(View):
    """대화 상세 관리 API"""
    
    def delete(self, request, conversation_id):
        """대화 삭제"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            conversation.is_active = False
            conversation.save()
            
            return JsonResponse({"message": "대화가 삭제되었습니다."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def put(self, request, conversation_id):
        """대화 제목 수정"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        
        try:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            body = json.loads(request.body)
            title = body.get("title", "")
            
            if title:
                conversation.title = title
                conversation.save()
                
                return JsonResponse({
                    "id": conversation.id,
                    "title": conversation.title
                })
            else:
                return JsonResponse({"error": "제목이 비어있습니다."}, status=400)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
