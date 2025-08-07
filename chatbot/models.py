from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Conversation(models.Model):
    """대화 세션을 나타내는 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, default="새 대화")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Message(models.Model):
    """개별 메시지를 나타내는 모델"""
    ROLE_CHOICES = [
        ('user', '사용자'),
        ('assistant', '챗봇'),
        ('system', '시스템'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.conversation.title} - {self.role}: {self.content[:50]}"

class UploadedImage(models.Model):
    """업로드된 이미지를 나타내는 모델"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='chat_images/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.conversation.title} - {self.image.name}"
