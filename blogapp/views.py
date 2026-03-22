from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Blog, Post, Comment, Tag, PostFile, BlogFile
from .forms import (
    RegistrationForm, LoginForm, BlogForm, PostForm,
    CommentForm, SearchForm, AddMemberForm,
    DEFAULT_SEARCH_SCOPES,
    SEARCH_IN_AUTHOR, SEARCH_IN_TITLE,
    SEARCH_IN_DESCRIPTION, SEARCH_IN_CONTENT, SEARCH_IN_COMMENTS,
)


# ─── Auth ────────────────────────────────────────────────────────────────────

@login_required
def register_view(request):
    """Admin-only view for creating new user accounts."""
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can register new users.')
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{form.cleaned_data["username"]}" created successfully.')
            return redirect('register')
    else:
        form = RegistrationForm()
    return render(request, 'blogapp/auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'blogapp/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ─── Home / Search ───────────────────────────────────────────────────────────

def home(request):
    # Bind the form only when the user submitted a search (q param present)
    search_form = SearchForm(request.GET if 'q' in request.GET else None)
    query = ''
    active_scopes = []

    public_blogs = Blog.objects.filter(is_public=True)
    if request.user.is_authenticated:
        private_blogs = Blog.objects.filter(
            Q(owner=request.user) | Q(members=request.user),
            is_public=False
        )
        visible_blogs = (public_blogs | private_blogs).distinct()
    else:
        visible_blogs = public_blogs

    # Latest posts from all blogs visible to the current user
    posts_qs = Post.objects.filter(
        blog__in=visible_blogs, is_published=True
    ).select_related('author', 'blog').prefetch_related('tags')

    if search_form.is_valid():
        query = search_form.cleaned_data.get('q', '').strip()
        active_scopes = search_form.cleaned_data.get('scope') or DEFAULT_SEARCH_SCOPES
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if query:
            filters = Q()
            if SEARCH_IN_TITLE in active_scopes:
                filters |= Q(title__icontains=query)
            if SEARCH_IN_CONTENT in active_scopes:
                filters |= Q(content__icontains=query)
            if SEARCH_IN_DESCRIPTION in active_scopes:
                filters |= Q(blog__description__icontains=query) | Q(blog__body__icontains=query)
            if SEARCH_IN_AUTHOR in active_scopes:
                filters |= Q(author__username__icontains=query)
            if SEARCH_IN_COMMENTS in active_scopes:
                filters |= Q(comments__content__icontains=query)
            posts_qs = posts_qs.filter(filters).distinct()

        # Date range filter applies regardless of query text
        if date_from:
            posts_qs = posts_qs.filter(created_at__date__gte=date_from)
        if date_to:
            posts_qs = posts_qs.filter(created_at__date__lte=date_to)


    paginator = Paginator(posts_qs, 10)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    blogs = visible_blogs.order_by('-created_at')[:8]
    popular_tags = Tag.objects.filter(
        post__blog__in=visible_blogs,
        post__is_published=True
    ).distinct()[:20]

    return render(request, 'blogapp/home.html', {
        'posts': posts,
        'blogs': blogs,
        'popular_tags': popular_tags,
        'search_form': search_form,
        'query': query,
        'active_scopes': active_scopes,
    })


# ─── Blogs ───────────────────────────────────────────────────────────────────

def blog_list(request):
    if request.user.is_authenticated:
        public_blogs = Blog.objects.filter(is_public=True)
        private_blogs = Blog.objects.filter(
            Q(owner=request.user) | Q(members=request.user),
            is_public=False
        )
        blogs = (public_blogs | private_blogs).distinct().order_by('-created_at')
    else:
        blogs = Blog.objects.filter(is_public=True).order_by('-created_at')

    paginator = Paginator(blogs, 12)
    page = request.GET.get('page')
    blogs_page = paginator.get_page(page)
    return render(request, 'blogapp/blog/list.html', {'blogs': blogs_page})


def blog_detail(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if not blog.can_view(request.user):
        raise Http404

    posts = blog.posts.filter(is_published=True).select_related('author').prefetch_related('tags')
    paginator = Paginator(posts, 10)
    page = request.GET.get('page')
    posts_page = paginator.get_page(page)

    members = blog.members.all()
    can_post = blog.can_post(request.user)
    is_owner = request.user == blog.owner
    is_member = blog.members.filter(pk=request.user.pk).exists() if request.user.is_authenticated else False

    add_member_form = None
    if request.user.is_authenticated:
        add_member_form = AddMemberForm(blog=blog)

    return render(request, 'blogapp/blog/detail.html', {
        'blog': blog,
        'posts': posts_page,
        'members': members,
        'can_post': can_post,
        'is_owner': is_owner,
        'is_member': is_member,
        'add_member_form': add_member_form,
    })


@login_required
def blog_create(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.owner = request.user
            blog.save()
            form.save_m2m()
            # Handle file attachments (max 5 MB each, any format)
            for f in request.FILES.getlist('blog_files'):
                if f.size > 5 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 5 MB limit.')
                    continue
                BlogFile.objects.create(blog=blog, file=f, original_name=f.name, size=f.size)
            messages.success(request, 'Topic created successfully!')
            return redirect('blog_detail', pk=blog.pk)
    else:
        form = BlogForm(owner=request.user)
    return render(request, 'blogapp/blog/form.html', {'form': form, 'action': 'Create topic'})


@login_required
def blog_edit(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    # Only admins can edit a topic after it has been published
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can edit topics.')
        return redirect('blog_detail', pk=pk)
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog, owner=blog.owner)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist('blog_files'):
                if f.size > 5 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 5 MB limit.')
                    continue
                BlogFile.objects.create(blog=blog, file=f, original_name=f.name, size=f.size)
            messages.success(request, 'Topic updated!')
            return redirect('blog_detail', pk=blog.pk)
    else:
        form = BlogForm(instance=blog, owner=blog.owner)
    return render(request, 'blogapp/blog/form.html', {'form': form, 'blog': blog, 'action': 'Edit topic'})


@login_required
def blog_delete(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    # Only admins can delete a topic
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can delete topics.')
        return redirect('blog_detail', pk=pk)
    if request.method == 'POST':
        blog.delete()
        messages.success(request, 'Topic deleted.')
        return redirect('blog_list')
    return render(request, 'blogapp/blog/delete_confirm.html', {'blog': blog})


# ─── Members ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def blog_add_member(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if not blog.can_view(request.user):
        raise Http404
    form = AddMemberForm(request.POST, blog=blog)
    if form.is_valid():
        user = form.cleaned_data['user']
        blog.members.add(user)
        messages.success(request, f'User {user.username} added as a member.')
    else:
        messages.error(request, 'Could not add member.')
    return redirect('blog_detail', pk=blog.pk)


@login_required
@require_POST
def blog_leave(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if blog.owner == request.user:
        messages.error(request, 'The owner cannot leave their own blog.')
        return redirect('blog_detail', pk=blog.pk)
    blog.members.remove(request.user)
    messages.success(request, f'You have left the blog "{blog.title}".')
    return redirect('blog_list')


@login_required
@require_POST
def blog_remove_member(request, pk, user_id):
    blog = get_object_or_404(Blog, pk=pk)
    target = get_object_or_404(User, pk=user_id)
    # Only the member themselves can remove themselves from a topic
    if request.user == target:
        blog.members.remove(target)
        messages.success(request, f'You have been removed from "{blog.title}".')
    else:
        messages.error(request, 'You can only remove yourself from a topic.')
    return redirect('blog_detail', pk=blog.pk)


# ─── Posts ───────────────────────────────────────────────────────────────────

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk, is_published=True)
    if not post.blog.can_view(request.user):
        raise Http404

    comments = post.comments.select_related('author')
    files = post.files.all()
    comment_form = CommentForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect('post_detail', pk=post.pk)

    can_edit = request.user == post.author or request.user == post.blog.owner
    return render(request, 'blogapp/post/detail.html', {
        'post': post,
        'comments': comments,
        'files': files,
        'comment_form': comment_form,
        'can_edit': can_edit,
    })


@login_required
def post_create(request, blog_pk):
    blog = get_object_or_404(Blog, pk=blog_pk)
    if not blog.can_post(request.user):
        messages.error(request, 'You do not have permission to post in this blog.')
        return redirect('blog_detail', pk=blog_pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.blog = blog
            post.author = request.user
            post.save()
            form.save_tags(post)

            # Handle multiple file attachments
            for f in request.FILES.getlist('post_files'):
                if f.size > 10 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 10 MB limit.')
                    continue
                PostFile.objects.create(
                    post=post,
                    file=f,
                    original_name=f.name,
                    size=f.size
                )

            messages.success(request, 'Post published!')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()

    return render(request, 'blogapp/post/form.html', {
        'form': form, 'blog': blog, 'action': 'New post'
    })


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author and request.user != post.blog.owner:
        messages.error(request, 'You do not have permission to edit this post.')
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            form.save_tags(post)

            for f in request.FILES.getlist('post_files'):
                if f.size > 10 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 10 MB limit.')
                    continue
                PostFile.objects.create(
                    post=post, file=f, original_name=f.name, size=f.size
                )

            messages.success(request, 'Post updated!')
            return redirect('post_detail', pk=post.pk)
    else:
        tags_str = ', '.join(post.tags.values_list('name', flat=True))
        form = PostForm(instance=post, initial={'tags_input': tags_str})

    return render(request, 'blogapp/post/form.html', {
        'form': form, 'post': post, 'blog': post.blog, 'action': 'Edit post'
    })


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author and request.user != post.blog.owner:
        messages.error(request, 'You do not have permission to delete this post.')
        return redirect('post_detail', pk=pk)
    blog_pk = post.blog.pk
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
        return redirect('blog_detail', pk=blog_pk)
    return render(request, 'blogapp/post/delete_confirm.html', {'post': post})


@login_required
@require_POST
def delete_file(request, file_pk):
    pf = get_object_or_404(PostFile, pk=file_pk)
    post = pf.post
    if request.user != post.author and request.user != post.blog.owner:
        messages.error(request, 'You do not have permission to delete this file.')
        return redirect('post_detail', pk=post.pk)
    pf.file.delete(save=False)
    pf.delete()
    messages.success(request, 'File deleted.')
    return redirect('post_edit', pk=post.pk)


# ─── Blog files ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def blog_delete_file(request, file_pk):
    bf = get_object_or_404(BlogFile, pk=file_pk)
    blog = bf.blog
    if request.user != blog.owner:
        messages.error(request, 'Only the topic owner can delete files.')
        return redirect('blog_edit', pk=blog.pk)
    bf.file.delete(save=False)
    bf.delete()
    messages.success(request, 'File deleted.')
    return redirect('blog_edit', pk=blog.pk)


# ─── Tags ─────────────────────────────────────────────────────────────────────

def tag_posts(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    if request.user.is_authenticated:
        public_blogs = Blog.objects.filter(is_public=True)
        private_blogs = Blog.objects.filter(
            Q(owner=request.user) | Q(members=request.user), is_public=False
        )
        visible_blogs = (public_blogs | private_blogs).distinct()
    else:
        visible_blogs = Blog.objects.filter(is_public=True)

    posts = Post.objects.filter(
        tags=tag, blog__in=visible_blogs, is_published=True
    ).select_related('author', 'blog')

    paginator = Paginator(posts, 10)
    page = request.GET.get('page')
    posts_page = paginator.get_page(page)

    return render(request, 'blogapp/tag_posts.html', {
        'tag': tag, 'posts': posts_page
    })


# ─── Profile ──────────────────────────────────────────────────────────────────

def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user.is_authenticated:
        public_blogs = Blog.objects.filter(is_public=True)
        private_blogs = Blog.objects.filter(
            Q(owner=request.user) | Q(members=request.user), is_public=False
        )
        visible_blogs = (public_blogs | private_blogs).distinct()
    else:
        visible_blogs = Blog.objects.filter(is_public=True)

    user_blogs = Blog.objects.filter(owner=profile_user).filter(pk__in=visible_blogs)
    user_posts = Post.objects.filter(
        author=profile_user, blog__in=visible_blogs, is_published=True
    ).select_related('blog')[:10]

    return render(request, 'blogapp/profile.html', {
        'profile_user': profile_user,
        'user_blogs': user_blogs,
        'user_posts': user_posts,
    })
