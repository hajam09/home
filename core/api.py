import re
from datetime import datetime
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
    Expense,
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


class ExpenseAnalyticsApiVersion1(APIView):

    def get(self, request):
        all_expenses = Expense.objects.all()
        selected_categories = [
            category.strip()
            for category in request.query_params.get('category', '').split(',')
            if category.strip()
        ]
        available_categories = list(
            all_expenses.order_by('category').values_list('category', flat=True).distinct()
        )
        if selected_categories:
            category_values = [category for category in selected_categories if category != '__unspecified__']
            category_filter = Q(category__in=category_values)
            if '__unspecified__' in selected_categories:
                category_filter |= Q(category='')
            qs = all_expenses.filter(category_filter)
        else:
            qs = all_expenses

        aggregates = qs.aggregate(
            total_spending=Sum('price'),
            average_spend=Avg('price'),
            first_date=Min('date'),
            last_date=Max('date'),
        )

        total_spending = aggregates['total_spending'] or 0
        first_date = aggregates['first_date']
        last_date = aggregates['last_date']
        if first_date and last_date:
            month_count = (last_date.year - first_date.year) * 12 + last_date.month - first_date.month + 1
        else:
            month_count = 1

        def display_name(value):
            return value or '(Unspecified)'

        category_rows = list(
            qs.values('category')
            .annotate(total_spent=Sum('price'), expense_count=Count('id'))
            .order_by('-total_spent', 'category')
        )
        retailer_rows = list(
            qs.values('retailer')
            .annotate(
                total_spent=Sum('price'),
                expense_count=Count('id'),
                average_spent=Round(Avg('price'), precision=2),
            )
            .order_by('-total_spent', 'retailer')
        )
        categories = [display_name(row['category']) for row in category_rows]

        category_spending = [
            {'category': display_name(row['category']), 'total_spent': float(row['total_spent'])}
            for row in category_rows
        ]
        retailer_spending = [
            {'retailer': display_name(row['retailer']), 'total_spent': float(row['total_spent'])}
            for row in retailer_rows
        ]
        retailer_averages = [
            {'retailer': display_name(row['retailer']), 'average_spent': float(row['average_spent'])}
            for row in retailer_rows
        ]

        most_common_retailer = (
            qs.values('retailer').annotate(count=Count('id')).order_by('-count', 'retailer').first()
        )
        most_common_category = (
            qs.values('category').annotate(count=Count('id')).order_by('-count', 'category').first()
        )

        annual_spending = list(
            qs.annotate(year=ExtractYear('date'))
            .values('year')
            .annotate(total_spent=Sum('price'))
            .order_by('year')
        )
        annual_category_rows = list(
            qs.annotate(year=ExtractYear('date'))
            .values('year', 'category')
            .annotate(total_spent=Sum('price'))
            .order_by('year', 'category')
        )
        years = [row['year'] for row in annual_spending]
        annual_by_category = {year: {'Year': year} for year in years}
        for row in annual_category_rows:
            annual_by_category[row['year']][display_name(row['category'])] = float(row['total_spent'])
        for row in annual_by_category.values():
            for category in categories:
                row.setdefault(category, 0)

        monthly_category_rows = list(
            qs.annotate(month=TruncMonth('date'))
            .values('month', 'category')
            .annotate(total_spent=Sum('price'))
            .order_by('month', 'category')
        )
        monthly_totals = {}
        monthly_by_category = {}
        for row in monthly_category_rows:
            month = row['month'].strftime('%Y-%m')
            category = display_name(row['category'])
            value = float(row['total_spent'])
            monthly_totals[month] = monthly_totals.get(month, 0) + value
            monthly_by_category.setdefault(category, {})[month] = value

        months = []
        if first_date and last_date:
            month = first_date.replace(day=1)
            last_month = last_date.replace(day=1)
            while month <= last_month:
                month_key = month.strftime('%Y-%m')
                months.append(month_key)
                monthly_totals.setdefault(month_key, 0)
                month += relativedelta(months=1)

        monthly_by_category_data = [
            {
                'category': category,
                'data': [monthly_by_category[category].get(month, 0) for month in months],
            }
            for category in categories
        ]

        top_expenses = [
            {
                'Date': row['date'],
                'Item': row['item'] or '(Unspecified)',
                'Category': display_name(row['category']),
                'Retailer': display_name(row['retailer']),
                'Price (£)': row['price'],
            }
            for row in qs.order_by('-price', '-date').values(
                'date', 'item', 'category', 'retailer', 'price'
            )[:10]
        ]
        largest_purchase = top_expenses[0] if top_expenses else None
        highest_spend_month = max(monthly_totals.items(), key=lambda item: item[1], default=None)

        data = {
            'available_categories': [
                {
                    'value': category if category else '__unspecified__',
                    'label': display_name(category),
                }
                for category in available_categories
            ],
            'selected_categories': selected_categories,
            'total_spending': {
                'title': 'Total Spending',
                'value': f'£{total_spending:.2f}',
            },
            'number_of_purchases': {
                'title': 'No. of Purchases',
                'value': qs.count(),
            },
            'average_per_purchase': {
                'title': 'Avg. per Purchase',
                'value': f'£{(aggregates["average_spend"] or 0):.2f}',
            },
            'average_monthly_spend': {
                'title': 'Average Monthly Spend',
                'value': f'£{(total_spending / month_count):.2f}',
            },
            'average_monthly_spend_by_category': [
                {
                    'title': f'Avg. Monthly Spend - {category}',
                    'value': f'£{(row["total_spent"] / month_count):.2f}',
                }
                for category, row in zip(categories, category_rows)
            ],
            'most_common_retailer': {
                'title': 'Most Frequently Used Retailer',
                'value': display_name(most_common_retailer['retailer']) if most_common_retailer else '-',
            },
            'most_common_category': {
                'title': 'Most Frequently Used Category',
                'value': display_name(most_common_category['category']) if most_common_category else '-',
            },
            'largest_purchase': {
                'title': 'Largest Purchase',
                'value': (
                    f'{largest_purchase["Item"]} - £{largest_purchase["Price (£)"]} '
                    f'({largest_purchase["Date"]})'
                    if largest_purchase else '-'
                ),
            },
            'highest_spend_month': {
                'title': 'Highest Spend Month',
                'value': (
                    f'{datetime.strptime(highest_spend_month[0], "%Y-%m").strftime("%b %Y")} '
                    f'- £{highest_spend_month[1]:.2f}'
                    if highest_spend_month else '-'
                ),
            },
            'top_expensive_purchases': {
                'title': 'Top Expensive Purchases',
                'value': top_expenses,
            },
            'total_annual_cost': {
                'title': 'Total Annual Cost',
                'value': [
                    {'Year': row['year'], 'Total Spending (£)': round(float(row['total_spent']), 2)}
                    for row in annual_spending
                ],
            },
            'annual_spending_by_category': {
                'title': 'Annual Spending by Category',
                'value': list(annual_by_category.values()),
            },
            'spending_by_category': category_spending,
            'spending_by_retailer': retailer_spending,
            'average_spending_by_retailer': retailer_averages,
            'monthly_spending': [
                {'month': month, 'total_spent': monthly_totals[month]}
                for month in months
            ],
            'monthly_spending_months': months,
            'monthly_spending_by_category': monthly_by_category_data,
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
        response = service.sendDatabaseBackup()
        return Response(
            {'success': response.get('isSuccess'), 'message': response.get('message')},
            status=status.HTTP_200_OK if response.get('isSuccess') else status.HTTP_500_INTERNAL_SERVER_ERROR
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


class ExpenseListAPI(ListAPIView):
    class ExpenseSerializer(serializers.ModelSerializer):
        tags = serializers.PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all(), required=False)

        class Meta:
            model = Expense
            fields = '__all__'

    queryset = Expense.objects.all().prefetch_related('tags')
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
