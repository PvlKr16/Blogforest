from django.apps import AppConfig


class BlogappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blogapp'
    verbose_name = 'Blog'

    def ready(self):
        import blogapp.signals  # noqa: F401
