from django.urls import path
from .views import ChatBotView, ModelSearchView

urlpatterns = [
    path("chat/", ChatBotView.as_view(), name="chat"),
    path("model-search/", ModelSearchView.as_view(), name="model-search"),
]
