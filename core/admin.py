from django.apps import apps
from django.contrib import (
    admin
)
from django.contrib.sessions.models import Session
from django.db.models import Count, Q
from django.urls import (
    reverse
)

from core.models import (
    CatPurchases,
    Cat,
    EnergyPayment,
    InventoryItem,
    JournalEntry,
    Tag,
    EventReminder,
    MeterPoint,
    Goal,
    Task
)


@admin.register(CatPurchases)
class CatPurchasesAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'retailer',
        'date',
        'brand',
        'item',
        'pouchPerBox',
        'unitWeight',
        'quantity',
        'price',
        'pricePerKg',
    ]
    list_filter = [
        'retailer',
        'brand',
        'item',
        'tags',
    ]
    search_fields = (
        'tags__name',
    )
    filter_horizontal = (
        'tags',
    )

    def pricePerKg(self, obj):
        if obj.item == CatPurchases.Item.FOOD:
            weight_in_kg = obj.pouchPerBox * obj.unitWeight * obj.quantity / 1000
            return str(round(float(obj.price) / weight_in_kg, 2))
        elif obj.item == CatPurchases.Item.FLEA:
            return str(round(obj.price / (obj.pouchPerBox * obj.quantity), 2))
        return 0.0


@admin.register(Cat)
class CatAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'breed',
        'colour',
        'microchip',
        'additionalData',
        'tags__name',
    )
    filter_horizontal = (
        'tags',
    )


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    search_fields = (
        'title',
        'eventDateTime',
        'startBeforeDays',
        'intervalValue',
        'intervalUnit',
        'nextReminderDateTime',
        'completed',
    )


@admin.register(EnergyPayment)
class EnergyPaymentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in EnergyPayment._meta.get_fields()]
    list_filter = [
        'channel',
        'meterPoint'
    ]
    search_fields = (
        'date',
        'time',
        'channel',
        'topUpCode',
        'meterPoint__smartCardNumber',
        'meterPoint__identifier',
        'meterPoint__utilityMarket',
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('meterPoint')


@admin.register(MeterPoint)
class MeterPointAdmin(admin.ModelAdmin):
    class EnergyPaymentInline(admin.TabularInline):
        model = EnergyPayment
        extra = 5
        can_delete = False
        fields = ('date', 'time', 'channel', 'topUpCode', 'amount')

    list_display = [
        'smartCardNumber',
        'identifier',
        'utilityMarket',
        'tariff',
    ]
    inlines = [EnergyPaymentInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'identifier',
        'box',
        'quantity'
    ]
    list_filter = [
        'identifier',
        'box',
    ]
    search_fields = (
        'title',
        'description',
        'identifier',
        'box',
        'location',
        'tags__name',
    )
    filter_horizontal = (
        'tags',
    )


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'modifiedDateTime'
    ]
    search_fields = (
        'title',
        'content',
        'tags__name',
    )
    filter_horizontal = (
        'tags',
    )


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()

    list_display = ['session_key', '_session_data', 'expire_date']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Task._meta.get_fields()]
    list_filter = [
        'completed',
        'goal'
    ]
    search_fields = (
        'name',
        'goal__name',
    )


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    class TaskInline(admin.TabularInline):
        model = Task
        extra = 5

    list_display = [
        'name', 'completedTasks', 'totalTasks', 'createdDateTime'
    ]
    inlines = [TaskInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            totalTasks=Count('tasks'),
            completedTasks=Count('tasks', filter=Q(tasks__completed=True)),
        )

    def totalTasks(self, obj):
        return obj.totalTasks

    def completedTasks(self, obj):
        return obj.completedTasks

    totalTasks.short_description = 'Total Tasks'
    completedTasks.short_description = 'Completed Tasks'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'usage_count'
    ]
    search_fields = (
        'name',
    )
    change_form_template = 'admin/tag-change-form.html'

    def usage_count(self, obj):
        model_names = ['CatPurchases', 'JournalEntry', 'InventoryItem', 'Cat']
        models = [apps.get_model('core', model_name) for model_name in model_names]
        return sum(model.objects.filter(tags=obj).count() for model in models)

    usage_count.short_description = 'Usage Count'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        model_names = ['CatPurchases', 'JournalEntry', 'InventoryItem', 'Cat']
        models = [apps.get_model('core', model_name) for model_name in model_names]

        # Find related instances in all models that use this tag
        model_and_url = [
            {
                'model': model.__name__,
                'url': reverse(f'admin:core_{model.__name__.lower()}_change', args=[instance.pk])
            }
            for model in models
            for instance in model.objects.filter(tags__id=object_id)
        ]

        # Add the context to render in the template
        extra_context = extra_context or {}
        extra_context['model_and_url'] = model_and_url
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
