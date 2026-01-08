from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q
from .models import Post, Category, Comment
from .forms import PostForm, ProfileForm, CommentForm

from django.contrib.auth.decorators import login_required

from django.core.paginator import Paginator

from django.contrib.auth import get_user_model

import datetime

import pytz

from django.utils import timezone


def index(request):
    template_name = 'blog/index.html'
    now = datetime.datetime.now().replace(tzinfo=pytz.utc)
    expr = Q(is_published=True) & Q(category__is_published=True) \
        & Q(pub_date__lte=now)
    post_list = Post.objects.select_related('location', 'category').\
        filter(expr).order_by('-pub_date')
    for post in post_list:
        post.comment_count = Comment.objects.filter(post=post.pk).count()

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, template_name, context)


def post_detail(request, id):
    template_name = 'blog/detail.html'
    now = datetime.datetime.now().replace(tzinfo=pytz.utc)
    try:
        post = Post.objects.select_related('location', 'category').get(pk=id)
        expr = (post.is_published is False)\
            or (post.category.is_published is False)\
            or (post.pub_date > now)
        if (expr) and request.user.pk != post.author.id:
            print(request.user.id, post.author.id)
            return render(request, 'pages/404.html', status=404)
    except Exception:
        return render(request, 'pages/404.html', status=404)
    context = {'post': post}
    context['form'] = CommentForm()
    comments = Comment.objects.filter(post=id).order_by('created_at')
    context['comments'] = comments
    return render(request, template_name, context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = Post.objects.filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).select_related('category', 'location', 'author').order_by('-pub_date')
    for post in post_list:
        post.comment_count = Comment.objects.filter(post=post.pk).count()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': page_obj
    })


User = get_user_model()


def profile(request, username):
    template_name = 'blog/profile.html'
    now = datetime.datetime.now().replace(tzinfo=pytz.utc)
    profile = get_object_or_404(User, username=username)
    if request.user.username != username:
        publication_list = Post.objects.select_related('author').\
            filter(
                author__username=username, is_published=True,
                category__is_published=True, pub_date__lte=now
        ).order_by('-pub_date')
    else:
        print(')')
        publication_list = Post.objects.select_related('author').\
            filter(author__username=username).order_by('-pub_date')
    for post in publication_list:
        post.comment_count = Comment.objects.filter(post=post.pk).count()
    paginator = Paginator(publication_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'profile': profile, 'page_obj': page_obj}
    return render(request, template_name, context)


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    context = {'form': form}
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', context)


def edit_post(request, pk):
    instance = get_object_or_404(Post, pk=pk)
    print(instance.author, request.user.id)
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', pk)
    form = PostForm(request.POST or None, instance=instance)
    context = {'form': form}
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', pk)
    return render(request, 'blog/create.html', context)


def edit_profile(request):
    instance = get_object_or_404(User, username=request.user.username)
    form = ProfileForm(
        request.POST or None,
        files=request.FILES or None,
        instance=instance
    )
    context = {'form': form}
    if form.is_valid():
        form.save()
        redirect('blog:profile', request.user.username)
    return render(request, 'blog/user.html', context)


def delete_post(request, pk):
    instance = get_object_or_404(Post, pk=pk)
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', pk)
    form = PostForm(request.POST or None, instance=instance)
    context = {'form': form}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', pk)


def edit_comment(request, pk, id):
    if id is not None:
        instance = get_object_or_404(Comment, pk=id)
    else:
        instance = None
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', pk)
    form = CommentForm(request.POST or None, instance=instance)
    comment = Comment.objects.get(pk=id)
    context = {'form': form}
    context['comment'] = comment
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', pk)
    return render(request, 'blog/comment.html', context)


def delete_comment(request, pk, id):
    instance = get_object_or_404(Comment, pk=id)
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', pk)
    if request.method == 'POST':
        # ...удаляем объект:
        instance.delete()
        return redirect('blog:post_detail', pk)
    return render(request, 'blog/comment.html')
