# accounts/urls.py

from django.urls import path
from .views import register_view, login_view, logout_view, profile_view, upload_sequence
from .views import (
    create_alignment_task,
    alignment_task_list,
    alignment_task_detail,
)
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('upload/', upload_sequence, name='upload_sequence'),
    path('alignment_tasks/', alignment_task_list, name='alignment_task_list'),
    path('alignment_tasks/create/', create_alignment_task, name='create_alignment_task'),
    path('alignment_tasks/<int:task_id>/', alignment_task_detail, name='alignment_task_detail'),
]
