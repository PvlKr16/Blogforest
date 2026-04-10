from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from .models import Blog, Post, Comment, Tag, PostFile, UserProfile, Poll, PollOption


class MultipleFileInput(forms.FileInput):
    """FileInput widget that supports selecting multiple files."""
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=30, required=False, label='First name')
    last_name = forms.CharField(max_length=30, required=False, label='Last name')
    is_guest = forms.BooleanField(
        required=False,
        label='Guest',
        help_text='Guests can only see topics they are members of.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'is_guest':
                field.widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_guest = self.cleaned_data.get('is_guest', False)
            profile.save()
        return user


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
        fields = ('title', 'description', 'body', 'is_public', 'members')
        labels = {
            'title': 'Title',
            'description': 'Description',
            'body': 'Content',
            'is_public': 'Public topic (visible to everyone)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Short description'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Full topic content...'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        if self.owner:
            # Exclude the owner from the members list
            self.fields['members'].queryset = User.objects.exclude(pk=self.owner.pk)




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
        fields = ('title', 'content')
        labels = {
            'title': 'Title',
            'content': 'Content',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comment title (optional)'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Write your comment...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False

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


# Search scope choices — used as checkbox values
SEARCH_IN_AUTHOR      = 'author'
SEARCH_IN_TITLE       = 'title'
SEARCH_IN_DESCRIPTION = 'description'
SEARCH_IN_CONTENT     = 'content'
SEARCH_IN_COMMENTS    = 'comments'

SEARCH_SCOPE_CHOICES = [
    (SEARCH_IN_AUTHOR,      'Author'),
    (SEARCH_IN_TITLE,       'Title'),
    (SEARCH_IN_DESCRIPTION, 'Description'),
    (SEARCH_IN_CONTENT,     'Content'),
    (SEARCH_IN_COMMENTS,    'Comments'),
]

# Fields searched when no scope checkboxes are selected
DEFAULT_SEARCH_SCOPES = [SEARCH_IN_TITLE, SEARCH_IN_DESCRIPTION, SEARCH_IN_CONTENT]


class SearchForm(forms.Form):
    q = forms.CharField(
        label='',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search posts...',
        })
    )
    scope = forms.MultipleChoiceField(
        choices=SEARCH_SCOPE_CHOICES,
        required=False,
        label='Search in',
        widget=forms.CheckboxSelectMultiple,
    )
    date_from = forms.DateField(
        required=False,
        label='From',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        label='To',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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


class AvatarForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('avatar',)
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {'avatar': 'Profile photo'}

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            if avatar.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f'Image must not exceed {settings.MAX_IMAGE_SIZE // (1024 * 1024)} MB.'
                )
        return avatar


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label='Current password',
        widget=forms.PasswordInput(attrs={'class': 'form-control password-field'})
    )
    new_password = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control password-field'}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control password-field'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pw = self.cleaned_data.get('current_password')
        if not self.user.check_password(pw):
            raise forms.ValidationError('Current password is incorrect.')
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('New passwords do not match.')
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()


class PollForm(forms.Form):
    """
    Единая форма создания опроса.
    Варианты ответов передаются как поля option_text_0, option_text_1, …
    и собираются во вьюхе poll_create.
    """
    # ── Настройки темы ────────────────────────────────────────────────────────
    title = forms.CharField(
        max_length=200,
        label='Title',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Poll topic title',
        }),
    )
    description = forms.CharField(
        required=False,
        label='Description',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'Short description (optional)',
        }),
    )
    is_public = forms.BooleanField(
        required=False,
        label='Public poll (visible to everyone)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Members',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'member-checkbox'}),
    )

    # ── Вопрос ────────────────────────────────────────────────────────────────
    question = forms.CharField(
        label='Question',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Your question...',
        }),
    )

    # ── Настройки опроса ──────────────────────────────────────────────────────
    is_anonymous = forms.BooleanField(
        required=False,
        label='Anonymous poll (names of voters are hidden)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    multiple_choice = forms.BooleanField(
        required=False,
        label='Allow multiple answers',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner:
            self.fields['members'].queryset = User.objects.exclude(pk=owner.pk)
