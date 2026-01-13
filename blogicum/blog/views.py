from django.shortcuts import get_object_or_404, render, redirect
from .models import Post, Category, Comment
from .forms import PostForm, ProfileForm, CommentForm

from django.db.models import Count

from django.contrib.auth.decorators import login_required

from django.core.paginator import Paginator

from django.contrib.auth import get_user_model

import datetime

import pytz

from django.utils import timezone

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from django.views.generic import UpdateView

from django.urls import reverse


def index(request):
    template_name = 'blog/index.html'
    post_list = filter_posts(
        Post.objects.select_related('location', 'category')
    )
    post_list_comments = get_comment_count(post_list)
    post_list_comments = sort_posts(post_list_comments)

    page_number = request.GET.get('page')
    page_obj = get_paginator_page(post_list_comments, page_number, 10)

    context = {'page_obj': page_obj}
    return render(request, template_name, context)


def post_detail(request, post_id):
    template_name = 'blog/detail.html'
    now = datetime.datetime.now().replace(tzinfo=pytz.utc)
    try:
        post = get_object_or_404(
            Post.objects.select_related('location', 'category'),
            pk=post_id
        )
        expr = (post.is_published is False)\
            or (post.category.is_published is False)\
            or (post.pub_date > now)
        if (expr) and request.user.pk != post.author.id:
            return render(request, 'pages/404.html', status=404)
    except Exception:
        return render(request, 'pages/404.html', status=404)
    context = {'post': post}
    context['form'] = CommentForm()
    comments = Comment.objects.filter(post=post_id).order_by('created_at')
    context['comments'] = comments
    return render(request, template_name, context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = filter_posts(
        Post.objects.select_related('category', 'location', 'author').
        filter(category=category)
    )

    post_with_comments = get_comment_count(post_list)
    post_with_comments = sort_posts(post_with_comments)

    page_number = request.GET.get('page')
    page_obj = get_paginator_page(post_with_comments, page_number, 10)
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': page_obj
    })


User = get_user_model()


def profile(request, username):
    template_name = 'blog/profile.html'
    profile = get_object_or_404(User, username=username)
    if request.user.username != username:
        publication_list = filter_posts(
            Post.objects.select_related('author').
            filter(author__username=username)
        )
    else:
        publication_list = Post.objects.select_related('author').\
            filter(author__username=username)

    post_with_comments = get_comment_count(publication_list)
    post_with_comments = sort_posts(post_with_comments)
    page_number = request.GET.get('page')

    page_obj = get_paginator_page(post_with_comments, page_number, 10)

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


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return redirect('login')

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})


@login_required
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


@login_required
def delete_post(request, post_id):
    instance = get_object_or_404(Post, pk=post_id)
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', post_id)
    form = PostForm(request.POST or None, instance=instance)
    context = {'form': form}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    if comment_id is not None:
        instance = get_object_or_404(Comment, pk=comment_id)
    else:
        instance = None
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', post_id)
    form = CommentForm(request.POST or None, instance=instance)
    comment = get_object_or_404(Comment, pk=comment_id)
    context = {'form': form}
    context['comment'] = comment
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    instance = get_object_or_404(Comment, pk=comment_id)
    if instance.author.id != request.user.id:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/comment.html')


def get_paginator_page(object_list, page_number, posts_count):
    paginator = Paginator(object_list, posts_count)
    page_obj = paginator.get_page(page_number)
    return page_obj


def get_comment_count(post_list):
    return post_list.annotate(
        comment_count=Count('comment')
    )


def sort_posts(post_list):
    return post_list.order_by('-pub_date')


def filter_posts(post_list):
    return post_list.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    )
