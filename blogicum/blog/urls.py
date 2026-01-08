from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path('posts/<int:id>/', views.post_detail, name='post_detail'),
    path('create/', views.create_post, name='create_post'),
    path('<slug:category_slug>/', views.category_posts, name='category_posts'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<slug:username>/', views.profile, name='profile'),
    path('posts/<int:pk>/edit/', views.edit_post, name='edit_post'),
    path('posts/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    path(
        'posts/<int:pk>/edit_comment/<int:id>/',
        views.edit_comment,
        name='edit_comment'
    ),
    path(
        'posts/<int:pk>/delete_comment/<int:id>/',
        views.delete_comment,
        name='delete_comment'
    ),
]
