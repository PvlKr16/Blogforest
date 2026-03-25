from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Home / Search
    path('', views.home, name='home'),

    # Blogs
    path('blogs/create/', views.blog_create, name='blog_create'),
    path('blogs/<int:pk>/', views.blog_detail, name='blog_detail'),
    path('blogs/<int:pk>/edit/', views.blog_edit, name='blog_edit'),
    path('blogs/<int:pk>/delete/', views.blog_delete, name='blog_delete'),

    # Members
    path('blogs/<int:pk>/add-member/', views.blog_add_member, name='blog_add_member'),
    path('blogs/<int:pk>/leave/', views.blog_leave, name='blog_leave'),
    path('blogs/<int:pk>/remove-member/<int:user_id>/', views.blog_remove_member, name='blog_remove_member'),

    # Posts
    path('blogs/<int:blog_pk>/posts/create/', views.post_create, name='post_create'),
    path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('files/<int:file_pk>/delete/', views.delete_file, name='delete_file'),
    path('blog-files/<int:file_pk>/delete/', views.blog_delete_file, name='blog_delete_file'),

    # Tags
    path('tag/<slug:slug>/', views.tag_posts, name='tag_posts'),

    # Users
    path('users/', views.user_list, name='user_list'),
    path('user/<str:username>/', views.profile, name='profile'),
]