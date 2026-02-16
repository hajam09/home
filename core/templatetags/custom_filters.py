from django import template
from django.urls import reverse

register = template.Library()


def linkItem(name, url=None, icon=None, subLinks=None):
    return {'name': name, 'url': url, 'icon': icon, 'subLinks': subLinks or []}


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Dashboards', subLinks=[
            linkItem('Admin', reverse('admin:index')),
            linkItem('Cat Purchases', reverse('core:cat-purchases-dashboard')),
            linkItem('Energy Payments', reverse('core:energy-payments-dashboard')),
            linkItem('Events', reverse('core:events')),
            linkItem('Goal & Task', reverse('core:goals-and-tasks')),
        ]),
    ]
    return links
