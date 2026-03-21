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
    first_name = forms.CharField(max_length=30, required=False, label='First name')
    last_name = forms.CharField(max_length=30, required=False, label='Last name')

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )


class BlogForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label='Members',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'member-checkbox'}),
    )

    class Meta:
        model = Blog
        fields = ('title', 'description', 'is_public', 'cover', 'members')
        labels = {
            'title': 'Title',
            'description': 'Description',
            'is_public': 'Public blog (visible to everyone)',
            'cover': 'Cover image',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Blog title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Blog description'}),
            'cover': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            # Exclude the owner from the members list
            self.fields['members'].queryset = User.objects.exclude(pk=self.owner.pk)

    def clean_cover(self):
        cover = self.cleaned_data.get('cover')
        if cover and hasattr(cover, 'size'):
            if cover.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'Image size must not exceed {settings.MAX_IMAGE_SIZE // (1024 * 1024)} MB.'
                )
        return cover


class PostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label='Tags',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas'
        })
    )

    class Meta:
        model = Post
        fields = ('title', 'content', 'image', 'is_published')
        labels = {
            'title': 'Title',
            'content': 'Content',
            'image': 'Image',
            'is_published': 'Publish',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Post content...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size'):
            if image.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'Image size must not exceed {settings.MAX_IMAGE_SIZE // (1024 * 1024)} MB.'
                )
        return image

    def save_tags(self, post):
        """Parse the comma-separated tags input and attach Tag objects to the post."""
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
        label='Files',
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True}),
        required=False
    )

    def clean_files(self):
        files = self.files.getlist('files') if hasattr(self, 'files') else []
        for f in files:
            if f.size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError(
                    f'File "{f.name}" exceeds the allowed size of '
                    f'{settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB.'
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
                'placeholder': 'Write a comment...'
            })
        }


class SearchForm(forms.Form):
    q = forms.CharField(
        label='',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search posts...',
        })
    )


class AddMemberForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='User',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, blog=None, **kwargs):
        super().__init__(*args, **kwargs)
        if blog:
            # Exclude the owner and existing members from the dropdown
            existing = blog.members.values_list('pk', flat=True)
            self.fields['user'].queryset = User.objects.exclude(
                pk__in=list(existing)
            ).exclude(pk=blog.owner.pk)
