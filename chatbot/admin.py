from django.contrib import admin
from .models import Conversation, Message, UploadedImage

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'title']
    date_hierarchy = 'created_at'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'content', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'conversation__title']
    date_hierarchy = 'created_at'

@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'image', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['conversation__title', 'description']
    date_hierarchy = 'uploaded_at'
