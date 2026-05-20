"""
URL configuration for djangoProject01 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from appnewsre import views, spider, despider
from appnewsre.views import togglecollection, togglelike, seenews, chat, register

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('login/', views.login),
    path('mainpage/<int:cid>/', views.mainpage),
    path('newsdetails/<int:newsid>/', views.newsdetails),
    path('search/', views.search),
    path('user_info/', views.user_info),
    path('manage_info/', views.manage_info),
    path('manage_user/', views.manage_user),
    path('manage_updateuser/', views.manage_updateuser),
    path('manage_deleteuser/', views.manage_deleteuser),
    path('manage_base/', views.manage_base),
    path('manage_news/', views.manage_news),
    path('moredetails/', views.moredetails),
    path('manage_deletenews/', views.manage_deletenews),
    path('manage_spider/', views.manage_spider),
    path('spider/', spider.fetch_news_from_toutiao),
    path('despider/', despider.fetch_news),
    path('manage_table/', views.manage_table),
    path('user_table/', views.user_table),
    path('user_like/', views.user_like),
    path('user_collection/', views.user_collection),
    path('user_history/', views.user_history),
    path('user_register/', views.user_register),
    path('register/', register, name='register'),
    path('user_bar/', views.user_bar),
    path('user_pie/', views.user_pie),
    path('user_line/', views.user_line),
    path('user_comment/', views.user_comment),
    path('logout/', views.logout),
    # 收藏功能的路由
    path('togglecollection/<int:newsid>/', togglecollection, name='togglecollection'),
    # 喜欢功能的路由
    path('togglelike/<int:newsid>/', togglelike, name='togglelike'),
    # 浏览新闻的路由
    path('seenews/<int:newsid>/', seenews, name='seenews'),
    # 评论的路由
    path('chat/<int:newsid>/', chat, name='chat'),
]
