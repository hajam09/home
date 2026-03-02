from django import template
from django.urls import reverse

register = template.Library()


def linkItem(name, url=None, icon=None):
    return {'name': name, 'url': url, 'icon': icon}


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Admin', reverse('admin:index'), 'fas fa-user-shield'),
        linkItem('Index', reverse('core:index-view'), 'fas fa-th-large'),
        linkItem('Cat Purchases', reverse('core:cat-purchases-dashboard'), 'fas fa-shopping-cart'),
        linkItem('Energy Payments', reverse('core:energy-payments-dashboard'), 'fas fa-bolt'),
        linkItem('Events', reverse('core:events'), 'fas fa-calendar-alt'),
        linkItem('Goal & Task', reverse('core:goals-and-tasks'), 'fas fa-tasks'),
        linkItem('Generator', reverse('core:generator'), 'fas fa-plug'),
        linkItem('API', reverse('core:api-view'), 'fas fa-network-wired'),
        linkItem(None),
    ]

    if request.user.is_authenticated:
        links.append(
            linkItem('Logout', reverse('core:logout-view'), 'fas fa-sign-out-alt')
        )
    return links
