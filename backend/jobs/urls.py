from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import (ProfileViewSet,ResumeViewSet,JobViewSet,ApplicationViewSet,NotificationViewSet,
                    AssistantMessageViewSet,dashboard,login,register,token_refresh)
router=DefaultRouter(); router.register('profiles',ProfileViewSet); router.register('resumes',ResumeViewSet); router.register('jobs',JobViewSet); router.register('applications',ApplicationViewSet); router.register('notifications',NotificationViewSet); router.register('assistant',AssistantMessageViewSet)
urlpatterns=[path('',include(router.urls)),path('dashboard/',dashboard),
             path('auth/register/',register),path('auth/login/',login),path('auth/token/refresh/',token_refresh)]
