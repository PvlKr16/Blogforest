from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
import os


def avatar_upload_path(instance, filename):
    return f'avatars/{instance.user.pk}/{filename}'


class UserProfile(models.Model):
    """Extends the built-in User with a guest role flag and avatar photo."""
    THEME_CHOICES = [
        ('emerald',      'Emerald'),
        ('ultramarine',  'Ultramarine'),
        ('violet',       'Violet & Orange'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_guest = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)
    theme = models.CharField(max_length=32, choices=THEME_CHOICES, default='emerald')

    class Meta:
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'

    def __str__(self):
        return f'{self.user.username} ({"guest" if self.is_guest else "regular"})'

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tag_posts', kwargs={'slug': self.slug})


class Blog(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Long-form content field with no size limit
    body = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='owned_blogs',
    )
    members = models.ManyToManyField(
        User, blank=True,
        related_name='member_blogs',
    )
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Blog'
        verbose_name_plural = 'Blogs'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'pk': self.pk})

    def can_view(self, user):
        if self.is_public:
            return True
        if not user.is_authenticated:
            return False
        return user == self.owner or self.members.filter(pk=user.pk).exists()

    def can_post(self, user):
        if not user.is_authenticated:
            return False
        # Any authenticated user who can view the blog can post a comment
        return self.can_view(user)

    def is_member(self, user):
        if not user.is_authenticated:
            return False
        return user == self.owner or self.members.filter(pk=user.pk).exists()


def blog_file_path(instance, filename):
    return f'blog_files/{instance.blog.pk}/{filename}'


class BlogFile(models.Model):
    blog = models.ForeignKey(
        'Blog', on_delete=models.CASCADE,
        related_name='files',
    )
    file = models.FileField(upload_to=blog_file_path)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Blog file'
        verbose_name_plural = 'Blog files'

    def __str__(self):
        return self.original_name

    def size_display(self):
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'


def post_image_path(instance, filename):
    return f'post_images/{instance.blog.pk}/{filename}'


def post_file_path(instance, filename):
    return f'post_files/{instance.post.pk}/{filename}'


class Post(models.Model):
    blog = models.ForeignKey(
        Blog, on_delete=models.CASCADE,
        related_name='posts',
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='posts',
    )
    title = models.CharField(max_length=300, blank=True, default='')
    content = models.TextField()
    image = models.ImageField(upload_to=post_image_path, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        # Comments live on the blog/topic page, not on their own page
        return reverse('blog_detail', kwargs={'pk': self.blog.pk}) + f'#comment-{self.pk}'


class PostFile(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='files',
    )
    file = models.FileField(upload_to=post_file_path)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Post file'
        verbose_name_plural = 'Post files'

    def __str__(self):
        return self.original_name

    def size_display(self):
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments',
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments',
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on "{self.post.title}"'


class BlogRead(models.Model):
    """
    Tracks when a user last read a blog.
    Used to determine unread topics: blogs where new posts appeared after last_read_at.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_reads')
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='reads')
    last_read_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Blog read'
        verbose_name_plural = 'Blog reads'
        unique_together = ('user', 'blog')

    def __str__(self):
        return f'{self.user.username} read "{self.blog.title}" at {self.last_read_at}'


def get_unread_blogs(user):
    """
    Return queryset of blogs that are 'unread' for the given user:
    - User is a member (or owner) of the blog
    - AND (never read OR new posts appeared after last_read_at)
    """
    from django.db.models import Max, OuterRef, Subquery
    from django.utils import timezone

    if not user.is_authenticated:
        return Blog.objects.none()

    member_blogs = Blog.objects.filter(
        models.Q(owner=user) | models.Q(members=user)
    ).distinct()

    # Subquery: last post date for each blog
    last_post_sq = Post.objects.filter(
        blog=OuterRef('pk'), is_published=True
    ).order_by('-created_at').values('created_at')[:1]

    # Subquery: user's last_read_at for each blog
    last_read_sq = BlogRead.objects.filter(
        user=user, blog=OuterRef('pk')
    ).values('last_read_at')[:1]

    blogs = member_blogs.annotate(
        last_post_at=Subquery(last_post_sq),
        last_read_at=Subquery(last_read_sq),
    ).filter(
        # Has at least one post
        last_post_at__isnull=False
    ).filter(
        # Never read OR new posts since last read
        models.Q(last_read_at__isnull=True) |
        models.Q(last_post_at__gt=models.F('last_read_at'))
    )

    return blogs
