from django.db.models import Q
from django.utils import timezone
from .forms import DEFAULT_SEARCH_SCOPES


def search_scopes(request):
    """Inject active search scope checkboxes into every template context."""
    scopes = request.GET.getlist('scope')
    if not scopes:
        scopes = DEFAULT_SEARCH_SCOPES
    return {'search_scopes': scopes}


def unread_count(request):
    """Inject unread topic count for the notification badge in the header."""
    from .views import get_unread_count
    return {'unread_count': get_unread_count(request.user)}
