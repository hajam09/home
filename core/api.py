import re
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import (
    Avg,
    Q,
    Sum
)
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    Min,
)
from django.db.models.functions import Round, ExtractYear
from django.db.models.functions import (
    TruncMonth
)
from rest_framework import status, serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from core import service
from core.models import (
    Tag,
    CatPurchases,
    JournalEntry,
    InventoryItem,
    MeterPoint,
    EnergyPayment,
    MeterReading,
    Cat,
    Event,
    EventReminder,
    Goal,
    Task,
    Property
)


class CatPurchasesAnalyticsApiVersion1(APIView):

    def base_queryset(self):
        return CatPurchases.objects.all()

    def total_weight_expr(self):
        return ExpressionWrapper(
            F('pouchPerBox') * F('unitWeight') * F('quantity'),
            output_field=IntegerField()
        )

    def price_per_kg_expr(self):
        return ExpressionWrapper(
            F('price') / (self.total_weight_expr() * 0.001),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )

    def average_spend_per_month(self, total, first_date, last_date):
        if not first_date or not last_date:
            return 0
        delta = relativedelta(last_date, first_date)
        months = delta.years * 12 + delta.months or 1
        return round(total / months, 2)

    def get(self, request):
        qs = self.base_queryset()

        # ---- Core aggregates ----
        aggregates = qs.aggregate(
            total_spending=Sum('price'),
            average_spend=Avg('price'),
            total_unit_weight=Sum(self.total_weight_expr()),
            first_date=Min('date'),
            last_date=Max('date'),
        )

        average_spend_per_month = self.average_spend_per_month(
            aggregates['total_spending'] or 0,
            aggregates['first_date'],
            aggregates['last_date'],
        )

        # ---- Retailer analytics ----
        spending_amount_for_each_retailer = qs.values('retailer').annotate(
            total_spent=Sum('price')
        )

        spending_count_for_each_retailer = qs.values('retailer').annotate(
            purchases_count=Count('id')
        )

        average_spending_for_each_retailer = qs.values('retailer').annotate(
            average_spent=Round(Avg('price'), precision=2)
        )

        most_common_retailer = (
            qs.values('retailer')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )

        # ---- Time-based ----
        total_cost_each_year = (
            qs.annotate(Year=ExtractYear('date'))
            .values('Year')
            .annotate(Price=Sum('price'))
            .order_by('Year')
        )

        monthly_spending = (
            qs.annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(
                total_spent=Sum('price'),
                purchase_count=Count('id'),
            )
            .order_by('month')
        )

        # ---- Expensive purchases ----
        top_expensive_purchases = (
            qs.annotate(Date=F('date'), Retailer=F('retailer'), Brand=F('brand'), Price=Round(F('price'), precision=2))
            .values('Date', 'Retailer', 'Brand', 'Price')
            .order_by('-price')[:5]
        )

        # ---- Detailed table ----
        all_purchase_detail = (
            qs.annotate(
                totalWeight=self.total_weight_expr(),
                pricePerKG=Round(self.price_per_kg_expr(), precision=2),
            )
            .values(
                'id', 'retailer', 'date', 'brand', 'item',
                'pouchPerBox', 'unitWeight', 'quantity',
                'price', 'totalWeight', 'pricePerKG',
            )
            .order_by('-date')
        )

        all_purchase_detail = [
            {
                'ID': i['id'], 'Retailer': i['retailer'], 'Date': i['date'], 'Brand': i['brand'],
                'Pouch Per Box': i['pouchPerBox'], 'Unit Weight': i['unitWeight'], 'Quantity': i['quantity'],
                'Price': i['price'], 'Total Weight': i['totalWeight'], 'Price Per KG': i['pricePerKG']
            }
            for i in all_purchase_detail
        ]

        # ---- Final response ----
        data = {
            # Same as V1
            'total_spending': {
                'title': 'Total Spending',
                'value': f'£{round(aggregates["total_spending"] or 0, 2)}'
            },
            'number_of_purchases': {
                'title': 'No. of Purchases',
                'value': qs.count(),
            },
            'average_per_purchase': {
                'title': 'Avg. per Purchase',
                'value': f'£{round(aggregates["average_spend"] or 0, 2)}'
            },
            'average_monthly_spend': {
                'title': 'Average Monthly Spend',
                'value': f'£{round(average_spend_per_month, 2)}',
            },

            'most_common_retailer': {
                'title': 'Most Frequently Used Retailer',
                'value': most_common_retailer['retailer']
            },
            'total_weight_purchased': {
                'title': 'Total Weight Purchased',
                'value': f'{aggregates["total_unit_weight"]}g / {aggregates["total_unit_weight"] / 1000}kg'
            },

            'top_expensive_purchases': {
                'title': 'Top Expensive Purchases',
                'value': top_expensive_purchases,
            },
            'total_annual_cost': {
                'title': 'Total Annual Cost',
                'value': total_cost_each_year,
            },

            'average_spend': aggregates['average_spend'] or 0,
            'average_spend_per_month': average_spend_per_month,

            'spending_amount_for_each_retailer': spending_amount_for_each_retailer,
            'spending_count_for_each_retailer': spending_count_for_each_retailer,
            'average_spending_for_each_retailer': average_spending_for_each_retailer,

            'all_purchase_detail': {
                'title': 'Purchase List',
                'value': all_purchase_detail
            },

            'monthly_spending': monthly_spending,
        }

        return Response(data, status=status.HTTP_200_OK)


class EnergyPaymentAnalyticsApiVersion1(APIView):

    def base_queryset(self):
        return EnergyPayment.objects.select_related('meterPoint')

    def get(self, request):
        # -----------------------------------
        # 1️⃣ Selected utilities
        # -----------------------------------
        utilities = re.sub(
            r'\s+',
            '',
            request.GET.get('utility', 'electricity,gas,water')
        ).lower().split(',')
        utilities = list(set(filter(None, utilities)))

        qs = self.base_queryset()

        # -----------------------------------
        # 2️⃣ Build combined filter
        # -----------------------------------
        combined_filter = Q()
        for utility in utilities:
            combined_filter |= Q(meterPoint__utilityMarket=utility.upper())
        qs = qs.filter(combined_filter)

        data = {}

        # -----------------------------------
        # 3️⃣ Totals + Counts (Single Aggregation)
        # -----------------------------------
        total_annotations = {'total_all': Sum('amount'), 'count_all': Count('id')}
        for utility in utilities:
            total_annotations[f'total_{utility}'] = Sum(
                'amount', filter=Q(meterPoint__utilityMarket=utility.upper())
            )
            total_annotations[f'count_{utility}'] = Count(
                'id', filter=Q(meterPoint__utilityMarket=utility.upper())
            )

        totals = qs.aggregate(**total_annotations)

        # Totals section
        data['total_utilities'] = {
            'title': 'Total Utilities',
            'value': f"£{round(totals.get('total_all') or 0, 2)}"
        }
        for utility in utilities:
            data[f'total_{utility}'] = {
                'title': f"Total {utility.capitalize()}",
                'value': f"£{round(totals.get(f'total_{utility}') or 0, 2)}"
            }

        # Payment counts
        data['payment_counts'] = {
            'All': totals.get('count_all', 0),
            **{
                utility.capitalize(): totals.get(f'count_{utility}', 0)
                for utility in utilities
            }
        }

        # -----------------------------------
        # 4️⃣ Determine full month range
        # -----------------------------------
        date_range = qs.aggregate(min_date=Min('date'), max_date=Max('date'))
        min_date = date_range['min_date']
        max_date = date_range['max_date']

        full_months = []
        if min_date and max_date:
            current = min_date.replace(day=1)
            end = max_date.replace(day=1)
            while current <= end:
                full_months.append(current)
                current += relativedelta(months=1)

        # -----------------------------------
        # 5️⃣ Monthly aggregation (single query)
        # -----------------------------------
        monthly_annotations = {
            'total_all': Sum('amount'),
            'payment_count_all': Count('id')
        }
        for utility in utilities:
            monthly_annotations[f'{utility}_total'] = Sum(
                'amount', filter=Q(meterPoint__utilityMarket=utility.upper())
            )
            monthly_annotations[f'{utility}_count'] = Count(
                'id', filter=Q(meterPoint__utilityMarket=utility.upper())
            )

        monthly_qs = qs.annotate(month=TruncMonth('date')).values('month').annotate(**monthly_annotations).order_by(
            'month')
        monthly_dict = {row['month']: row for row in monthly_qs}

        # -----------------------------------
        # 6️⃣ Normalize months (fill zeros)
        # -----------------------------------
        monthly = []
        for month in full_months:
            row = monthly_dict.get(month, {})
            month_row = {
                'month': month,
                'total_all': row.get('total_all', 0),
                'payment_count_all': row.get('payment_count_all', 0),
                **{
                    utility: row.get(f'{utility}_total', 0)
                    for utility in utilities
                },
                **{
                    f'{utility}_count': row.get(f'{utility}_count', 0)
                    for utility in utilities
                }
            }
            monthly.append(month_row)

        # Add monthly data to response
        data['cost_by_each_month_for_all_utilities'] = [
            {'month': row['month'], 'total': row['total_all'], 'payment_count': row['payment_count_all']}
            for row in monthly
        ]

        for utility in utilities:
            data[f'cost_by_each_month_for_{utility}'] = [
                {
                    'month': row['month'],
                    'total': row[utility],
                    'payment_count': row[f'{utility}_count']
                }
                for row in monthly
            ]

        # -----------------------------------
        # 7️⃣ Average monthly
        # -----------------------------------
        def average(key):
            values = [row.get(key) if row.get(key) is not None else Decimal('0.0') for row in monthly]
            return sum(values) / len(values) if values else Decimal('0.0')

        data['avg_monthly_utilities'] = {
            'title': 'Avg. Monthly Utilities',
            'value': f"£{round(average('total_all'), 2)}"
        }
        for utility in utilities:
            data[f'avg_monthly_{utility}'] = {
                'title': f"Avg. Monthly {utility.capitalize()}",
                'value': f"£{round(average(utility), 2)}"
            }

        # -----------------------------------
        # 8️⃣ Yearly totals
        # -----------------------------------
        yearly_annotations = {'all_utilities': Sum('amount')}
        for utility in utilities:
            yearly_annotations[utility] = Sum('amount', filter=Q(meterPoint__utilityMarket=utility.upper()))

        yearly_qs = qs.annotate(year=ExtractYear('date')).values('year').annotate(**yearly_annotations).order_by('year')

        data['total_annual_price'] = [
            {
                'Year': row['year'],
                'All Utilities': row['all_utilities'],
                **{utility.capitalize(): row.get(utility) or 0 for utility in utilities}
            }
            for row in yearly_qs
        ]
        return Response(data, status=status.HTTP_200_OK)


class MeterReadingAnalyticsApiVersion1(APIView):

    def base_queryset(self):
        return MeterReading.objects.select_related('meterPoint').order_by('date')

    def get(self, request):
        utilities = re.sub(
            r'\s+',
            '',
            request.GET.get('utility', 'electricity,gas,water')
        ).lower().split(',')

        utilities = set(filter(None, utilities))

        qs = self.base_queryset()

        utility_filters = {
            'electricity': Q(meterPoint__utilityMarket=MeterPoint.UtilityMarket.ELECTRICITY),
            'gas': Q(meterPoint__utilityMarket=MeterPoint.UtilityMarket.GAS),
        }

        data = {
            utility: {
                'dates': [r.date.strftime('%d/%m/%Y') for r in qs.filter(utility_filters[utility])],
                'readings': [float(r.reading) for r in qs.filter(utility_filters[utility])],
            }
            for utility in utilities
            if utility in utility_filters
        }

        return Response(data, status=status.HTTP_200_OK)


class DatabaseBackupVersion1(APIView):
    def post(self, request):
        try:
            success = service.sendDatabaseBackup()
        except Exception as e:
            print(f'Error sending backup: {e}')
            success = False

        return Response(
            {'success': success},
            status=status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class TagListAPI(ListAPIView):
    class TagSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tag
            fields = '__all__'

    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class CatPurchasesListAPI(ListAPIView):
    class CatPurchasesSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = CatPurchases
            fields = '__all__'

    queryset = CatPurchases.objects.all().prefetch_related('tags').order_by('date')
    serializer_class = CatPurchasesSerializer
    permission_classes = [IsAuthenticated]


class JournalEntryListAPI(ListAPIView):
    class JournalEntrySerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = JournalEntry
            fields = '__all__'

    queryset = JournalEntry.objects.all().prefetch_related('tags').order_by('createdDateTime', 'id')
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]


class InventoryItemListAPI(ListAPIView):
    class InventoryItemSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = InventoryItem
            fields = '__all__'

    queryset = InventoryItem.objects.all().prefetch_related('tags').order_by('id')
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]


class MeterPointListAPI(ListAPIView):
    class MeterPointSerializer(serializers.ModelSerializer):
        class Meta:
            model = MeterPoint
            fields = '__all__'

    queryset = MeterPoint.objects.all().order_by('id')
    serializer_class = MeterPointSerializer
    permission_classes = [IsAuthenticated]


class EnergyPaymentListAPI(ListAPIView):
    class EnergyPaymentSerializer(serializers.ModelSerializer):
        meterPointIdentifier = serializers.CharField(source='meterPoint.identifier', read_only=True)

        class Meta:
            model = EnergyPayment
            fields = ['id', 'date', 'time', 'channel', 'topUpCode', 'amount', 'meterPointIdentifier']

    queryset = EnergyPayment.objects.all().order_by('date', 'time', 'id')
    serializer_class = EnergyPaymentSerializer
    permission_classes = [IsAuthenticated]


class MeterReadingListAPI(ListAPIView):
    class MeterReadingSerializer(serializers.ModelSerializer):
        meterPointIdentifier = serializers.CharField(source='meterPoint.identifier', read_only=True)

        class Meta:
            model = MeterReading
            fields = ['id', 'date', 'reading', 'meterPointIdentifier']

    queryset = MeterReading.objects.all().order_by('date', 'id')
    serializer_class = MeterReadingSerializer
    permission_classes = [IsAuthenticated]


class CatListAPI(ListAPIView):
    class CatSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = Cat
            fields = '__all__'

    queryset = Cat.objects.all().prefetch_related('tags').order_by('createdDateTime')
    serializer_class = CatSerializer
    permission_classes = [IsAuthenticated]


class EventListAPI(ListAPIView):
    class EventSerializer(serializers.ModelSerializer):
        class Meta:
            model = Event
            fields = '__all__'

    queryset = Event.objects.all().order_by('completed', 'startDateTime')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, *args, **kwargs):
        event = self.request.data.get('event')
        completed = self.request.data.get('completed')

        data = {}
        if completed is not None:
            data['completed'] = completed

        Event.objects.filter(id=event).update(**data)
        return Response(status=status.HTTP_200_OK)


class EventReminderListAPI(ListAPIView):
    class EventReminderSerializer(serializers.ModelSerializer):
        class Meta:
            model = EventReminder
            fields = '__all__'

    queryset = EventReminder.objects.all().order_by('createdDateTime')
    serializer_class = EventReminderSerializer
    permission_classes = [IsAuthenticated]


class GoalListAPI(ListAPIView):
    class GoalSerializer(serializers.ModelSerializer):
        class Meta:
            model = Goal
            fields = '__all__'

    queryset = Goal.objects.all().order_by('createdDateTime')
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TaskListAPI(ListAPIView):
    class TaskSerializer(serializers.ModelSerializer):
        class Meta:
            model = Task
            fields = '__all__'

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        goal = self.request.GET.get('goal')
        tasks = Task.objects.all()
        if goal:
            tasks = tasks.filter(goal__id=goal)
        return tasks.order_by('completed', 'name')

    def patch(self, *args, **kwargs):
        task = self.request.data.get('task')
        completed = self.request.data.get('completed')
        name = self.request.data.get('name', None)

        data = {}
        if completed is not None:
            data['completed'] = completed
        if name is not None:
            data['name'] = name

        Task.objects.filter(id=task).update(**data)
        return Response(status=status.HTTP_200_OK)


class PropertyListAPI(ListAPIView):
    class PropertySerializer(serializers.ModelSerializer):
        class Meta:
            model = Property
            fields = '__all__'

    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]
