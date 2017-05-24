from django import template
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.models import Q

from gipsy.dashboard.models import GipsyDashboardMenu
from gipsy.dashboard.settings import GIPSY_DASHBOARD_URL,\
    GIPSY_VANILLA_INDEX_URL, GIPSY_THEME, GIPSY_DASHBOARD_TITLE,\
    GIPSY_DASHBOARD_CACHE_TIME   


register = template.Library()
tag_func = register.inclusion_tag('gipsy/dashboard/widgets/base.html',
                                  takes_context=True)


def get_active_url(request_formated):
    return GipsyDashboardMenu.objects\
        .filter(Q(url=request_formated) | Q(url=request_formated[:-1]))[:1]


@register.inclusion_tag('gipsy/dashboard/menu.html',
                        takes_context=True)
def gipsy_dashboard_menu(context, *args, **kwargs):
    """
    This tags manages the display of the admin menu.
    """
    items = []
    items_list = []
    items_parents = []
    parent_items_list = GipsyDashboardMenu.objects.filter(parent__isnull=True)\
        .order_by('order')
        
    # Only display menu items to user with the right permission
    for parent_item in parent_items_list:
        for child in parent_item.children:
            items_list.append(child)

    apps = {}

    try:
        # django >= 1.9
        app_list = admin.site.get_app_list(context['request'])
        for a in app_list:
            apps[a['app_url']] = a['models'][0]['perms']
    except AttributeError:
        # django < 1.9
        app_list = []
        for model, model_admin in admin.site._registry.items():
            app_label = model._meta.app_label
            module_perms = model_admin.get_model_perms(context['request'])
            app_url = reverse('admin:app_list', kwargs={'app_label': app_label}, current_app=admin.site.name)
            apps[app_url] = module_perms
    apps_keys = apps.keys()
    admin_prefix = reverse('admin:index').replace('/', '')
    for item in items_list:
        if item.url is None:
            continue
        url = item.url
        if url[0] != '/':
            url = '/' + item.url
        url_args = url.split('/')
        if admin_prefix == url_args[1]:
            permission = True
            for apps_key in apps_keys:
                if apps_key in url:
                    permission = False
                    for perm in apps[apps_key]:
                        if perm in url:
                            permission = apps[apps_key][perm]
                            break
                        if apps[apps_key][perm] == True:
                            permission = True
            if permission:
                items.append(item)
        else:
            items.append(item)

        if item in items and item.parent and not item.parent in items_parents:
            items_parents.append(item.parent)

    context['items_children'] = items
    context['items_parents'] = items_parents
    context['items'] = parent_items_list
    
    # Set the active item
    context['active'] = None
    if context['request'].path:
        active = []
        request_formated = context['request'].get_full_path()[1:]
        if request_formated:
            active = get_active_url(request_formated)

            # if nothing was found try to clean 'add' and 'edit' for generic urls
            # this is not done before to allow to point directly to those kinds of
            # urls
            if not active:
                if 'add' in request_formated:
                    request_formated = request_formated.split('/add', 1)
                if 'change' in request_formated:
                    request_formated = request_formated.split('/change', 1)[0].rsplit('/', 1)
                if 'history' in request_formated:
                    request_formated = request_formated.split('/history', 1)[0].rsplit('/', 1)

                active = get_active_url(request_formated[0] + '/')

    if len(active):
        context['active'] = active[0]
    context['dashboard_url'] = GIPSY_DASHBOARD_URL
    context['vanilla_index_url'] = GIPSY_VANILLA_INDEX_URL
    return context


@register.inclusion_tag('gipsy/dashboard/widgets/active_users.html')
def dashboard_active_users(count=0, title="CURRENTLY ACTIVE USERS",
                           label="CURRENT USERS"):
    return {'count': count, 'title': title, 'label': label}


@register.inclusion_tag('gipsy/dashboard/widgets/item_list.html')
def dashboard_item_list(items, title="MOST RECENT ITEMS"):
    return {'items': items, 'title': title}


@register.simple_tag
def gipsy_theme():
    """
    Returns the theme for the Admin-Interface.
    """
    return GIPSY_THEME


@register.simple_tag
def gipsy_title():
    """
    Returns the Title for the Admin-Interface.
    """
    return GIPSY_DASHBOARD_TITLE


@register.simple_tag(takes_context=True)
def url_active(context, viewname):
    request = context['request']
    current_path = request.path
    compare_path = reverse(viewname)
    if current_path == compare_path:
        return 'active'
    else:
        return ''


@register.assignment_tag(takes_context=True)
def gipsy_is_popup(context):
    """
    Checks if displayed in a popup. Addition to the django default
    templatetag as some shitty librairiesare not using this logic.
    """
    return (context.get('is_popup', False) or
            context['request'].GET.get('pop', False))


class GipsyDashboardCacheTime(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def __repr__(self):
        return "<GipsyDashboardCachTime Node>"

    def render(self, context):
        context[self.varname] = GIPSY_DASHBOARD_CACHE_TIME
        return ''


@register.tag
def gipsy_dashboard_cache_time(parser, token):
    """
    Retrieves the cache time set in settings

    Usage::

        {% gipsy_dashboard_cache_time as [cache_time] %}
    """
    tokens = token.contents.split()
    if len(tokens) < 2:
        raise template.TemplateSyntaxError(
            "'gipsy_dashboard_cache_time' statements require at least one arguments")
    if tokens[1] != 'as':
        raise template.TemplateSyntaxError(
            "Second argument to 'gipsy_dashboard_cache_time' must be 'as'")

    return GipsyDashboardCacheTime(varname=tokens[2])


def gipsy_dashboard_widget(context, widget, index=None):
    """
    Template tag that renders a given dashboard module
    """
    context.update({
        'template': widget.template,
        'widget': widget,
        'index': index,
    })
    return context
gipsy_dashboard_widget = tag_func(gipsy_dashboard_widget)
