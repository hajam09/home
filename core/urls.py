from django.urls import path
from django.views.generic import TemplateView

from core.api import (
    CatPurchasesAnalyticsApiVersion1,
    EnergyPaymentAnalyticsApiVersion1,
    MeterReadingAnalyticsApiVersion1,
    DatabaseBackupVersion1,
    TagListAPI,
    CatPurchasesListAPI,
    JournalEntryListAPI,
    InventoryItemListAPI,
    MeterPointListAPI,
    EnergyPaymentListAPI,
    MeterReadingListAPI,
    CatListAPI,
    EventListAPI,
    EventReminderListAPI,
    GoalListAPI,
    TaskListAPI,
    PropertyListAPI,
)
from core.views import (
    indexView,
    logoutView,
    goalAndTasks,
    events,
    generator,
    EnergyPaymentsDashboard,
    MeterPointView,
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
        'logout/',
        logoutView,
        name='logout-view'
    ),
    path(
        'cat-purchases-dashboard/',
        TemplateView.as_view(template_name='core/cat-purchases-dashboard.html'),
        name='cat-purchases-dashboard'
    ),
    path(
        'energy-payments-dashboard/',
        EnergyPaymentsDashboard.as_view(),
        name='energy-payments-dashboard'
    ),
    path(
        'meter-points/<slug:identifier>/',
        MeterPointView.as_view(),
        name='meter-point-view-'
    ),
    path(
        'goals-and-tasks/',
        goalAndTasks,
        name='goals-and-tasks'
    ),
    path(
        'v1/database-backup-api/',
        DatabaseBackupVersion1.as_view(),
        name='v1-database-backup-api'
    ),
    path(
        'events/',
        events,
        name='events'
    ),
    path(
        'api/',
        TemplateView.as_view(template_name='core/api.html'),
        name='api-view'
    ),
    path(
        'generator/',
        generator,
        name='generator'
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
    path(
        'v1/meter-readings-analytics-api/',
        MeterReadingAnalyticsApiVersion1.as_view(),
        name='v1-meter-readings-analytics-api'
    ),

    path('api/tags/', TagListAPI.as_view(), name='tag-list'),
    path('api/cat-purchases/', CatPurchasesListAPI.as_view(), name='cat-purchases-list'),
    path('api/journal-entries/', JournalEntryListAPI.as_view(), name='journal-entries-list'),
    path('api/inventory-items/', InventoryItemListAPI.as_view(), name='inventory-items-list'),
    path('api/meter-points/', MeterPointListAPI.as_view(), name='meter-points-list'),
    path('api/energy-payments/', EnergyPaymentListAPI.as_view(), name='energy-payments-list'),
    path('api/meter-readings/', MeterReadingListAPI.as_view(), name='meter-readings-list'),
    path('api/cats/', CatListAPI.as_view(), name='cats-list'),
    path('api/events/', EventListAPI.as_view(), name='events-list'),
    path('api/event-reminders/', EventReminderListAPI.as_view(), name='event-reminders-list'),
    path('api/goals/', GoalListAPI.as_view(), name='goals-list'),
    path('api/tasks/', TaskListAPI.as_view(), name='tasks-list'),
    path('api/properties/', PropertyListAPI.as_view(), name='properties-list'),
]
