from django.urls import path
from django.views.generic import TemplateView

from core.api import (
    CatPurchasesAnalyticsApiVersion1,
    EnergyPaymentAnalyticsApiVersion1,
    TagListAPI,
    CatPurchasesListAPI,
    JournalEntryListAPI,
    InventoryItemListAPI,
    MeterPointListAPI,
    EnergyPaymentListAPI,
    CatListAPI,
    EventReminderListAPI,
    GoalListAPI,
    TaskListAPI,
)
from core.views import (
    indexView,
    meterPointsView,
    goalAndTasks,
)

app_name = 'core'

urlpatterns = [
    # Default views
    path(
        '',
        indexView,
        name='index-view'
    ),
    path(
        'cat-purchases-dashboard/',
        TemplateView.as_view(template_name='core/cat-purchases-dashboard.html'),
        name='cat-purchases-dashboard'
    ),
    path(
        'energy-payments-dashboard/',
        TemplateView.as_view(template_name='core/energy-payments-dashboard.html'),
        name='energy-payments-dashboard'
    ),
    path(
        'meter-points/',
        meterPointsView,
        name='meter-points-view'
    ),
    path(
        'goals-and-tasks/',
        goalAndTasks,
        name='goals-and-tasks'
    ),

    # Versioned custom APIs
    path(
        'v1/cat-purchases-analytics-api/',
        CatPurchasesAnalyticsApiVersion1.as_view(),
        name='v1-cat-purchases-analytics-api'
    ),

    path(
        'v1/energy-payments-analytics-api/',
        EnergyPaymentAnalyticsApiVersion1.as_view(),
        name='v1-energy-payments-analytics-api'
    ),

    path('api/tags/', TagListAPI.as_view(), name='tag-list'),
    path('api/cat-purchases/', CatPurchasesListAPI.as_view(), name='cat-purchases-list'),
    path('api/journal-entries/', JournalEntryListAPI.as_view(), name='journal-entries-list'),
    path('api/inventory-items/', InventoryItemListAPI.as_view(), name='inventory-items-list'),
    path('api/meter-points/', MeterPointListAPI.as_view(), name='meter-points-list'),
    path('api/energy-payments/', EnergyPaymentListAPI.as_view(), name='energy-payments-list'),
    path('api/cats/', CatListAPI.as_view(), name='cats-list'),
    path('api/event-reminders/', EventReminderListAPI.as_view(), name='event-reminders-list'),
    path('api/goals/', GoalListAPI.as_view(), name='goals-list'),
    path('api/tasks/', TaskListAPI.as_view(), name='tasks-list'),
]
