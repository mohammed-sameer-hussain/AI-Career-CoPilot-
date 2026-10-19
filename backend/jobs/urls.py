from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import (ProfileViewSet,ResumeViewSet,JobViewSet,ApplicationViewSet,NotificationViewSet,
                    AssistantMessageViewSet,dashboard,login,register,token_refresh)
from .views import create_background_task, background_task_status
router=DefaultRouter(); router.register('profiles',ProfileViewSet); router.register('resumes',ResumeViewSet); router.register('jobs',JobViewSet); router.register('applications',ApplicationViewSet); router.register('notifications',NotificationViewSet); router.register('assistant',AssistantMessageViewSet)
urlpatterns=[path('',include(router.urls)),path('dashboard/',dashboard),
             path('tasks/',create_background_task),path('tasks/<str:task_id>/',background_task_status),
             path('auth/register/',register),path('auth/login/',login),path('auth/token/refresh/',token_refresh)]
