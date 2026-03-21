from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from .models import Blog, Post, Comment, Tag, PostFile


class MultipleFileInput(forms.FileInput):
    """FileInput widget that supports selecting multiple files."""
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)



class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=30, required=False, label='Имя')
    last_name = forms.CharField(max_length=30, required=False, label='Фамилия')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class BlogForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label='Участники',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'member-checkbox'}),
    )

    class Meta:
        model = Blog
        fields = ('title', 'description', 'is_public', 'cover', 'members')
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'is_public': 'Открытый блог (виден всем)',
            'cover': 'Обложка',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название блога'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Описание блога'}),
            'cover': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            self.fields['members'].queryset = User.objects.exclude(pk=self.owner.pk)

    def clean_cover(self):
        cover = self.cleaned_data.get('cover')
        if cover and hasattr(cover, 'size'):
            if cover.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'Размер изображения не должен превышать {settings.MAX_IMAGE_SIZE // (1024*1024)} МБ.'
                )
        return cover


class PostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label='Теги',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите теги через запятую'
        })
    )

    class Meta:
        model = Post
        fields = ('title', 'content', 'image', 'is_published')
        labels = {
            'title': 'Заголовок',
            'content': 'Содержание',
            'image': 'Изображение',
            'is_published': 'Опубликовать',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок поста'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Текст поста...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size'):
            if image.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'Размер изображения не должен превышать {settings.MAX_IMAGE_SIZE // (1024*1024)} МБ.'
                )
        return image

    def save_tags(self, post):
        tags_input = self.cleaned_data.get('tags_input', '')
        post.tags.clear()
        if tags_input.strip():
            for tag_name in tags_input.split(','):
                tag_name = tag_name.strip().lower()
                if tag_name:
                    from django.utils.text import slugify
                    import re
                    slug = slugify(tag_name)
                    if not slug:
                        slug = re.sub(r'[^\w]', '-', tag_name)[:50]
                    tag, _ = Tag.objects.get_or_create(
                        slug=slug,
                        defaults={'name': tag_name}
                    )
                    post.tags.add(tag)


class PostFileForm(forms.Form):
    files = forms.FileField(
        label='Файлы',
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True}),
        required=False
    )

    def clean_files(self):
        files = self.files.getlist('files') if hasattr(self, 'files') else []
        for f in files:
            if f.size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError(
                    f'Файл "{f.name}" превышает допустимый размер '
                    f'{settings.MAX_UPLOAD_SIZE // (1024*1024)} МБ.'
                )
        return files


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        labels = {'content': ''}
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Напишите комментарий...'
            })
        }


class SearchForm(forms.Form):
    q = forms.CharField(
        label='',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск постов...',
        })
    )


class AddMemberForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Пользователь',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, blog=None, **kwargs):
        super().__init__(*args, **kwargs)
        if blog:
            existing = blog.members.values_list('pk', flat=True)
            self.fields['user'].queryset = User.objects.exclude(
                pk__in=list(existing)
            ).exclude(pk=blog.owner.pk)
