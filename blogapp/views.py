from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Max, Subquery, OuterRef
from django.http import Http404, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Blog, Post, Comment, Tag, PostFile, BlogFile, BlogRead
from .forms import (
    RegistrationForm, LoginForm, BlogForm, PostForm,
    CommentForm, SearchForm, AddMemberForm,
    AvatarForm, PasswordChangeForm,
    DEFAULT_SEARCH_SCOPES,
    SEARCH_IN_AUTHOR, SEARCH_IN_TITLE,
    SEARCH_IN_DESCRIPTION, SEARCH_IN_CONTENT, SEARCH_IN_COMMENTS,
)


def get_visible_blogs(user):
    """
    Return the queryset of blogs visible to the given user.
    - Guest users: only blogs where they are a member or owner.
    - Regular authenticated users: all public blogs + their private blogs.
    - Anonymous users: public blogs only.
    """
    if user.is_authenticated:
        is_guest = getattr(getattr(user, 'profile', None), 'is_guest', False)
        if is_guest:
            # Guests see only blogs they belong to
            return Blog.objects.filter(
                Q(owner=user) | Q(members=user)
            ).distinct()
        # Regular users see all public blogs plus their private ones
        public = Blog.objects.filter(is_public=True)
        private = Blog.objects.filter(
            Q(owner=user) | Q(members=user), is_public=False
        )
        return (public | private).distinct()
    return Blog.objects.filter(is_public=True)


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
                next_url = request.GET.get('next', '')
                return redirect(next_url if next_url else 'home')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    theme = request.session.get('last_theme', 'emerald')
    return render(request, 'blogapp/auth/login.html', {'form': form, 'user_theme': theme})


def logout_view(request):
    # Preserve theme preference across logout so login page shows correct colours
    theme = getattr(getattr(request.user, 'profile', None), 'theme', 'emerald')         if request.user.is_authenticated else 'emerald'
    logout(request)
    request.session['last_theme'] = theme
    return redirect('login')


# ─── Home / Search ───────────────────────────────────────────────────────────

@login_required
def home(request):
    # Anonymous users see only the login page
    if not request.user.is_authenticated:
        return redirect('login')

    # Bind the form only when the user submitted a search (q param present)
    search_form = SearchForm(request.GET if 'q' in request.GET else None)
    query = ''
    active_scopes = []

    visible_blogs = get_visible_blogs(request.user)

    if search_form.is_valid():
        query = search_form.cleaned_data.get('q', '').strip()
        active_scopes = search_form.cleaned_data.get('scope') or DEFAULT_SEARCH_SCOPES
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        # Search returns matching BLOGS (not posts), deduplicated, sorted by activity
        blogs_qs = visible_blogs.annotate(
            last_post_at=Max('posts__created_at')
        ).select_related('owner')

        if query:
            blog_filters = Q()
            post_filters = Q()

            # Blog-level fields
            if SEARCH_IN_TITLE in active_scopes:
                blog_filters |= Q(title__icontains=query)
            if SEARCH_IN_DESCRIPTION in active_scopes:
                blog_filters |= Q(description__icontains=query)
            if SEARCH_IN_CONTENT in active_scopes:
                blog_filters |= Q(body__icontains=query)
            if SEARCH_IN_AUTHOR in active_scopes:
                blog_filters |= Q(owner__username__icontains=query)

            # Post-level fields — match blogs that have relevant comments
            if SEARCH_IN_COMMENTS in active_scopes:
                post_filters |= Q(posts__content__icontains=query)


            # Only combine non-empty filter sets to avoid Q() matching everything
            combined = Q()
            if blog_filters:
                combined |= blog_filters
            if post_filters:
                combined |= post_filters

            if combined:
                blogs_qs = blogs_qs.filter(combined).distinct()
            else:
                blogs_qs = blogs_qs.none()

        if date_from:
            blogs_qs = blogs_qs.filter(created_at__date__gte=date_from)
        if date_to:
            blogs_qs = blogs_qs.filter(created_at__date__lte=date_to)

        blogs_qs = blogs_qs.order_by('-last_post_at')

        paginator = Paginator(blogs_qs, 10)
        page = request.GET.get('page')
        items = paginator.get_page(page)
        is_search = True
    else:
        # Default view: list of visible blogs sorted by latest comment (post) date
        # Annotate each blog with the timestamp of its most recent post
        from django.db.models.functions import Coalesce
        blogs_with_activity = visible_blogs.annotate(
            last_post_at=Max('posts__created_at'),
            # activity = latest post time if exists, otherwise topic creation time
            activity=Coalesce(Max('posts__created_at'), 'created_at'),
        ).order_by('-activity').select_related('owner').prefetch_related('members')

        paginator = Paginator(blogs_with_activity, 10)
        page = request.GET.get('page')
        items = paginator.get_page(page)
        is_search = False

    # Sidebar data
    sidebar_blogs = visible_blogs.order_by('-created_at')[:8]
    popular_tags = Tag.objects.filter(
        post__blog__in=visible_blogs,
        post__is_published=True
    ).distinct()[:20]

    return render(request, 'blogapp/home.html', {
        'items': items,
        'is_search': is_search,
        'sidebar_blogs': sidebar_blogs,
        'popular_tags': popular_tags,
        'search_form': search_form,
        'query': query,
        'active_scopes': active_scopes,
    })


# ─── Blogs ───────────────────────────────────────────────────────────────────

@login_required
@login_required
def blog_list(request):
    blogs = get_visible_blogs(request.user).order_by('-created_at')

    paginator = Paginator(blogs, 12)
    page = request.GET.get('page')
    blogs_page = paginator.get_page(page)
    return render(request, 'blogapp/blog/list.html', {'blogs': blogs_page})


@login_required
def blog_detail(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    if not blog.can_view(request.user):
        raise Http404
    # Guests can only view blogs they are members of
    is_guest = getattr(getattr(request.user, 'profile', None), 'is_guest', False)
    if is_guest and not blog.is_member(request.user):
        raise Http404

    # Mark as read when the topic is opened
    if request.user.is_authenticated:
        from django.utils import timezone
        BlogRead.objects.update_or_create(
            user=request.user, blog=blog,
            defaults={'last_read_at': timezone.now()}
        )

    # Sort order: 'asc' = oldest first (default), 'desc' = newest first
    sort = request.GET.get('sort', 'asc')
    order = 'created_at' if sort == 'asc' else '-created_at'

    posts = blog.posts.filter(is_published=True).order_by(order).select_related('author').prefetch_related('tags')
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
        'sort': sort,
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
            # Mark the new topic as read for its creator immediately
            from django.utils import timezone
            BlogRead.objects.update_or_create(
                user=request.user, blog=blog,
                defaults={'last_read_at': timezone.now()}
            )
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
        return redirect('home')
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
    return redirect('home')


@login_required
@require_POST
def blog_remove_member(request, pk, user_id):
    blog = get_object_or_404(Blog, pk=pk)
    target = get_object_or_404(User, pk=user_id)
    # Only the member themselves can remove themselves from a topic
    if request.user == target:
        blog.members.remove(target)
        messages.success(request, f'You have left "{blog.title}".')
        return redirect('home')
    else:
        messages.error(request, 'You can only remove yourself from a topic.')
        return redirect('blog_detail', pk=blog.pk)


# ─── Posts ───────────────────────────────────────────────────────────────────

# post_detail removed — comments live on blog_detail page


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
            post.is_published = True  # always publish — no draft mode for comments
            post.save()
            form.save_tags(post)

            # Handle multiple file attachments (max 5 MB each)
            for f in request.FILES.getlist('post_files'):
                if f.size > 5 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 5 MB limit.')
                    continue
                PostFile.objects.create(
                    post=post,
                    file=f,
                    original_name=f.name,
                    size=f.size
                )

            # Auto-add commenter as member so they receive future unread notifications
            if request.user != blog.owner:
                blog.members.add(request.user)

            # Mark blog as read for the author at the post's timestamp
            from django.utils import timezone
            BlogRead.objects.update_or_create(
                user=request.user, blog=blog,
                defaults={'last_read_at': post.created_at}
            )
            messages.success(request, 'Comment added!')
            return redirect('blog_detail', pk=blog.pk)
    else:
        form = PostForm()

    return render(request, 'blogapp/post/form.html', {
        'form': form, 'blog': blog, 'action': 'Save'
    })


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can edit comments.')
        return redirect('blog_detail', pk=post.blog.pk)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            form.save_tags(post)

            for f in request.FILES.getlist('post_files'):
                if f.size > 5 * 1024 * 1024:
                    messages.warning(request, f'File "{f.name}" skipped: exceeds the 5 MB limit.')
                    continue
                PostFile.objects.create(
                    post=post, file=f, original_name=f.name, size=f.size
                )

            messages.success(request, 'Comment updated!')
            return redirect('blog_detail', pk=post.blog.pk)
    else:
        tags_str = ', '.join(post.tags.values_list('name', flat=True))
        form = PostForm(instance=post, initial={'tags_input': tags_str})

    return render(request, 'blogapp/post/form.html', {
        'form': form, 'post': post, 'blog': post.blog, 'action': 'Save'
    })


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can delete comments.')
        return redirect('blog_detail', pk=post.blog.pk)
    blog_pk = post.blog.pk
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Comment deleted.')
        return redirect('blog_detail', pk=blog_pk)
    return render(request, 'blogapp/post/delete_confirm.html', {'post': post})


@login_required
@require_POST
def delete_file(request, file_pk):
    pf = get_object_or_404(PostFile, pk=file_pk)
    post = pf.post
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can delete files.')
        return redirect('blog_detail', pk=post.blog.pk)
    pf.file.delete(save=False)
    pf.delete()
    messages.success(request, 'File deleted.')
    return redirect(reverse('blog_detail', kwargs={'pk': post.blog.pk}))  # stays on edit page


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


# ─── Unread ───────────────────────────────────────────────────────────────────

@login_required
def unread_view(request):
    sort = request.GET.get('sort', 'activity')
    from django.db.models import Max

    blogs = get_unread_blogs(request.user)

    if sort == 'activity':
        # Sort by latest post date descending
        blogs = blogs.order_by('-last_post_at')
    else:
        # Sort by blog creation date descending
        blogs = blogs.order_by('-created_at')

    return render(request, 'blogapp/unread.html', {
        'blogs': blogs,
        'sort': sort,
    })


# ─── Tags ─────────────────────────────────────────────────────────────────────

@login_required
def tag_posts(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    visible_blogs = get_visible_blogs(request.user)

    posts = Post.objects.filter(
        tags=tag, blog__in=visible_blogs, is_published=True
    ).select_related('author', 'blog')

    paginator = Paginator(posts, 10)
    page = request.GET.get('page')
    posts_page = paginator.get_page(page)

    return render(request, 'blogapp/tag_posts.html', {
        'tag': tag, 'posts': posts_page
    })


# ─── Unread topics ────────────────────────────────────────────────────────────

def get_unread_count(user):
    """Return number of member topics with new posts since the user last visited."""
    if not user.is_authenticated:
        return 0
    from django.db.models import Max, Subquery, OuterRef
    member_blogs = Blog.objects.filter(
        Q(owner=user) | Q(members=user)
    ).distinct()
    last_read_sq = BlogRead.objects.filter(
        user=user, blog=OuterRef('pk')
    ).values('last_read_at')[:1]
    blogs = member_blogs.annotate(
        last_read_at=Subquery(last_read_sq),
        last_post_at=Max('posts__created_at'),
    )
    count = 0
    for b in blogs:
        # Never visited → always unread (even if no posts yet)
        if b.last_read_at is None:
            count += 1
        # Visited but new posts appeared since last visit
        elif b.last_post_at is not None and b.last_post_at > b.last_read_at:
            count += 1
    return count


@login_required
def unread_blogs(request):
    from django.db.models import Max, Subquery, OuterRef
    member_blogs = Blog.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    last_read_sq = BlogRead.objects.filter(
        user=request.user, blog=OuterRef('pk')
    ).values('last_read_at')[:1]
    blogs = member_blogs.annotate(
        last_read_at=Subquery(last_read_sq),
        last_post_at=Max('posts__created_at'),
    ).select_related('owner')
    unread = [
        b for b in blogs
        if b.last_read_at is None or (
            b.last_post_at is not None and b.last_post_at > b.last_read_at
        )
    ]
    sort = request.GET.get('sort', 'desc')
    unread.sort(key=lambda b: b.last_post_at or b.created_at, reverse=(sort == 'desc'))
    return render(request, 'blogapp/unread.html', {
        'unread_blogs': unread,
        'sort': sort,
    })


# ─── Mark unread ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def mark_unread(request, pk):
    from django.utils import timezone
    blog = get_object_or_404(Blog, pk=pk)
    # Set last_read_at to epoch so any post appears newer than it
    BlogRead.objects.update_or_create(
        user=request.user, blog=blog,
        defaults={'last_read_at': timezone.datetime(2000, 1, 1, tzinfo=timezone.utc)}
    )
    messages.success(request, f'"{blog.title}" marked as unread.')
    return redirect('unread_blogs')


# ─── Theme ───────────────────────────────────────────────────────────────────

@login_required
@require_POST
def set_theme(request):
    from blogapp.models import UserProfile
    theme = request.POST.get('theme', 'emerald')
    valid = {'emerald', 'ultramarine', 'violet'}
    if theme not in valid:
        theme = 'emerald'
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.theme = theme
    profile.save(update_fields=['theme'])
    from django.http import JsonResponse
    return JsonResponse({'theme': theme})


# ─── User list ────────────────────────────────────────────────────────────────

@login_required
def user_list(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'blogapp/user_list.html', {'users': users})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    is_own = request.user == profile_user
    # Ensure profile exists
    from blogapp.models import UserProfile
    profile_obj, _ = UserProfile.objects.get_or_create(user=profile_user)

    avatar_form = None
    password_form = None

    if is_own:
        if request.method == 'POST':
            if 'change_avatar' in request.POST:
                avatar_form = AvatarForm(request.POST, request.FILES, instance=profile_obj)
                if avatar_form.is_valid():
                    avatar_form.save()
                    messages.success(request, 'Profile photo updated.')
                    return redirect('profile', username=username)
            elif 'change_password' in request.POST:
                password_form = PasswordChangeForm(request.user, request.POST)
                if password_form.is_valid():
                    password_form.save()
                    # Keep user logged in after password change
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Password changed successfully.')
                    return redirect('profile', username=username)
        if avatar_form is None:
            avatar_form = AvatarForm(instance=profile_obj)
        if password_form is None:
            password_form = PasswordChangeForm(request.user)

    return render(request, 'blogapp/profile.html', {
        'profile_user': profile_user,
        'profile_obj': profile_obj,
        'is_own': is_own,
        'avatar_form': avatar_form,
        'password_form': password_form,
    })
