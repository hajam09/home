from django import template
from django.urls import reverse

register = template.Library()


def linkItem(name, url=None, icon=None):
    return {'name': name, 'url': url, 'icon': icon}


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Admin', reverse('admin:index')),
        linkItem('Index', reverse('core:index-view')),
        linkItem('Cat Purchases', reverse('core:cat-purchases-dashboard')),
        linkItem('Energy Payments', reverse('core:energy-payments-dashboard')),
        linkItem('Events', reverse('core:events')),
        linkItem('Goal & Task', reverse('core:goals-and-tasks')),
    ]
    return links
