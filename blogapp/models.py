from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
import os


class Tag(models.Model):
    name = models.CharField('Название', max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tag_posts', kwargs={'slug': self.slug})


class Blog(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='owned_blogs',
        verbose_name='Владелец'
    )
    members = models.ManyToManyField(
        User, blank=True,
        related_name='member_blogs',
        verbose_name='Участники'
    )
    is_public = models.BooleanField('Открытый блог', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    cover = models.ImageField(
        'Обложка', upload_to='blog_covers/', blank=True, null=True
    )

    class Meta:
        verbose_name = 'Блог'
        verbose_name_plural = 'Блоги'
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
        return user == self.owner or self.members.filter(pk=user.pk).exists()

    def is_member(self, user):
        if not user.is_authenticated:
            return False
        return user == self.owner or self.members.filter(pk=user.pk).exists()


def post_image_path(instance, filename):
    return f'post_images/{instance.blog.pk}/{filename}'


def post_file_path(instance, filename):
    return f'post_files/{instance.post.pk}/{filename}'


class Post(models.Model):
    blog = models.ForeignKey(
        Blog, on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Блог'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    title = models.CharField('Заголовок', max_length=300)
    content = models.TextField('Содержание')
    image = models.ImageField(
        'Изображение', upload_to=post_image_path, blank=True, null=True
    )
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='Теги')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    is_published = models.BooleanField('Опубликован', default=True)

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'pk': self.pk})


class PostFile(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='files',
        verbose_name='Пост'
    )
    file = models.FileField('Файл', upload_to=post_file_path)
    original_name = models.CharField('Имя файла', max_length=255)
    size = models.PositiveIntegerField('Размер (байт)', default=0)
    uploaded_at = models.DateTimeField('Загружен', auto_now_add=True)

    class Meta:
        verbose_name = 'Файл поста'
        verbose_name_plural = 'Файлы постов'

    def __str__(self):
        return self.original_name

    def size_display(self):
        size = self.size
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} ТБ'


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    content = models.TextField('Комментарий')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']

    def __str__(self):
        return f'Комментарий {self.author.username} к "{self.post.title}"'
