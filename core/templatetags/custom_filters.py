from django import template
from django.urls import reverse

register = template.Library()


def linkItem(name, url, sub_links=None):
    return {'name': name, 'url': url, 'subLinks': sub_links}


@register.simple_tag
def navigationPanel(request):
    links = [
        linkItem('Dashboards', None, [
            linkItem('Admin', reverse('admin:index')),
            linkItem('Cat Purchases', reverse('core:cat-purchases-dashboard')),
            linkItem('Energy Payments', reverse('core:energy-payments-dashboard')),
            linkItem('Meter Points', reverse('core:meter-points-view')),
            linkItem('Goal & Task', reverse('core:goals-and-tasks')),
        ]),
    ]
    return links
