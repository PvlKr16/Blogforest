from .forms import DEFAULT_SEARCH_SCOPES


def search_scopes(request):
    """
    Inject active search scope checkboxes into every template context.
    Falls back to DEFAULT_SEARCH_SCOPES when no scope param is present.
    """
    scopes = request.GET.getlist('scope')
    if not scopes:
        scopes = DEFAULT_SEARCH_SCOPES
    return {'search_scopes': scopes}
