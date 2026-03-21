from django.contrib import admin
from .models import Blog, Post, PostFile, Comment, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class PostFileInline(admin.TabularInline):
    model = PostFile
    extra = 0
    readonly_fields = ('original_name', 'size', 'uploaded_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'blog', 'author', 'created_at', 'is_published')
    list_filter = ('is_published', 'blog', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    filter_horizontal = ('tags',)
    inlines = [PostFileInline]
    date_hierarchy = 'created_at'


class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    fields = ('title', 'author', 'is_published', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_public', 'created_at', 'member_count')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'owner__username')
    filter_horizontal = ('members',)
    inlines = [PostInline]

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Участников'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'content', 'post__title')
