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
from django.db.models.functions import Round
from django.db.models.functions import (
    TruncMonth,
    TruncYear
)
from rest_framework import status, serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Tag,
    CatPurchases,
    JournalEntry,
    InventoryItem,
    MeterPoint,
    EnergyPayment,
    Cat,
    EventReminder,
)


class CatPurchasesAnalyticsApiVersion1(APIView):

    def base_queryset(self):
        return CatPurchases.objects.all()

    def total_weight_expr(self):
        return ExpressionWrapper(
            F("pouchPerBox") * F("unitWeight") * F("quantity"),
            output_field=IntegerField()
        )

    def price_per_kg_expr(self):
        return ExpressionWrapper(
            F("price") / (self.total_weight_expr() * 0.001),
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
            total_spending=Sum("price"),
            average_spend=Avg("price"),
            total_unit_weight=Sum(self.total_weight_expr()),
            first_date=Min("date"),
            last_date=Max("date"),
        )

        average_spend_per_month = self.average_spend_per_month(
            aggregates["total_spending"] or 0,
            aggregates["first_date"],
            aggregates["last_date"],
        )

        # ---- Retailer analytics ----
        spending_amount_for_each_retailer = qs.values("retailer").annotate(
            total_spent=Sum("price")
        )

        spending_count_for_each_retailer = qs.values("retailer").annotate(
            purchases_count=Count("id")
        )

        average_spending_for_each_retailer = qs.values("retailer").annotate(
            average_spent=Round(Avg("price"), precision=2)
        )

        most_common_retailer = (
            qs.values("retailer")
            .annotate(count=Count("id"))
            .order_by("-count")
            .first()
        )

        # ---- Time-based ----
        total_cost_each_year = (
            qs.annotate(year=TruncYear("date"))
            .values("year")
            .annotate(total_cost_per_year=Sum("price"))
            .order_by("year")
        )

        monthly_spending = (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                total_spent=Sum("price"),
                purchase_count=Count("id"),
            )
            .order_by("month")
        )

        # ---- Expensive purchases ----
        top_expensive_purchases = (
            qs.annotate(rounded_price=Round(F("price"), precision=2))
            .values("brand", "rounded_price", "retailer", "date")
            .order_by("-price")[:5]
        )

        # ---- Detailed table ----
        all_purchase_detail = (
            qs.annotate(
                totalWeight=self.total_weight_expr(),
                pricePerKG=Round(self.price_per_kg_expr(), precision=2),
            )
            .values(
                "id", "retailer", "date", "brand", "item",
                "pouchPerBox", "unitWeight", "quantity",
                "price", "totalWeight", "pricePerKG",
            )
            .order_by("-date")
        )

        # ---- Final response ----
        data = {
            # Same as V1
            "total_spending": aggregates["total_spending"] or 0,
            "total_purchases": qs.count(),
            "average_spend": aggregates["average_spend"] or 0,
            "average_spend_per_month": average_spend_per_month,

            "spending_amount_for_each_retailer": spending_amount_for_each_retailer,
            "spending_count_for_each_retailer": spending_count_for_each_retailer,
            "average_spending_for_each_retailer": average_spending_for_each_retailer,
            "most_common_retailer": most_common_retailer,

            "total_unit_weight_in_grams": aggregates["total_unit_weight"] or 0,

            "top_expensive_purchases": top_expensive_purchases,
            "total_cost_each_year": total_cost_each_year,
            "all_purchase_detail": all_purchase_detail,

            "monthly_spending": monthly_spending,
        }

        return Response(data, status=status.HTTP_200_OK)


class EnergyPaymentAnalyticsApiVersion1(APIView):

    def base_queryset(self):
        return EnergyPayment.objects.select_related("meterPoint")

    def electricity_filter(self):
        return Q(meterPoint__utilityMarket=MeterPoint.UtilityMarket.ELECTRICITY)

    def gas_filter(self):
        return Q(meterPoint__utilityMarket=MeterPoint.UtilityMarket.GAS)

    def monthly_costs(self, qs):
        return (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                total=Sum("amount"),
                payment_count=Count("id"),
            )
            .order_by("month")
        )

    def yearly_costs(self, qs):
        return (
            qs.annotate(year=TruncYear("date"))
            .values("year")
            .annotate(total_cost_per_year=Sum("amount"))
            .order_by("year")
        )

    def average_from_monthlies(self, monthly_data):
        if not monthly_data:
            return 0
        return sum(row["total"] for row in monthly_data) / len(monthly_data)

    def get(self, request):
        qs = self.base_queryset()

        elec_qs = qs.filter(self.electricity_filter())
        gas_qs = qs.filter(self.gas_filter())

        # ---- Monthly ----
        monthly_all = list(self.monthly_costs(qs))
        monthly_electricity = list(self.monthly_costs(elec_qs))
        monthly_gas = list(self.monthly_costs(gas_qs))

        # ---- Averages (monthly) ----
        avg_cost_all = self.average_from_monthlies(monthly_all)
        avg_cost_elec = self.average_from_monthlies(monthly_electricity)
        avg_cost_gas = self.average_from_monthlies(monthly_gas)

        # ---- Totals ----
        total_cost_all = qs.aggregate(total=Sum("amount"))["total"] or 0
        total_cost_elec = elec_qs.aggregate(total=Sum("amount"))["total"] or 0
        total_cost_gas = gas_qs.aggregate(total=Sum("amount"))["total"] or 0

        # ---- Yearly ----
        yearly_all = list(self.yearly_costs(qs))
        yearly_electricity = list(self.yearly_costs(elec_qs))
        yearly_gas = list(self.yearly_costs(gas_qs))

        # ---- Payment behaviour ----
        payment_counts = {
            "all": qs.count(),
            "electricity": elec_qs.count(),
            "gas": gas_qs.count(),
        }

        # ---- Final response ----
        data = {
            # Averages
            "average_cost_per_month_for_all_utilities": avg_cost_all,
            "average_cost_per_month_for_electricity": avg_cost_elec,
            "average_cost_per_month_for_gas": avg_cost_gas,

            # Totals
            "total_cost_for_all_utilities": total_cost_all,
            "total_cost_for_electricity": total_cost_elec,
            "total_cost_for_gas": total_cost_gas,

            # Counts & behaviour
            "payment_counts": payment_counts,

            # Yearly totals
            "total_cost_each_year_for_all_utilities": yearly_all,
            "total_cost_each_year_for_electricity": yearly_electricity,
            "total_cost_each_year_for_gas": yearly_gas,

            # Monthly breakdowns (charts)
            "cost_by_each_month_for_all_utilities": monthly_all,
            "cost_by_each_month_for_electricity": monthly_electricity,
            "cost_by_each_month_for_gas": monthly_gas,
        }

        return Response(data, status=status.HTTP_200_OK)


class TagListAPI(ListAPIView):
    class TagSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tag
            fields = "__all__"

    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class CatPurchasesListAPI(ListAPIView):
    class CatPurchasesSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = CatPurchases
            fields = "__all__"

    queryset = CatPurchases.objects.all().prefetch_related('tags').order_by('date')
    serializer_class = CatPurchasesSerializer
    permission_classes = [IsAuthenticated]


class JournalEntryListAPI(ListAPIView):
    class JournalEntrySerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = JournalEntry
            fields = "__all__"

    queryset = JournalEntry.objects.all().prefetch_related('tags').order_by('createdDateTime', 'id')
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]


class InventoryItemListAPI(ListAPIView):
    class InventoryItemSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = InventoryItem
            fields = "__all__"

    queryset = InventoryItem.objects.all().prefetch_related('tags').order_by('id')
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]


class MeterPointListAPI(ListAPIView):
    class MeterPointSerializer(serializers.ModelSerializer):
        class Meta:
            model = MeterPoint
            fields = "__all__"

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


class CatListAPI(ListAPIView):
    class CatSerializer(serializers.ModelSerializer):
        tags = serializers.StringRelatedField(many=True)

        class Meta:
            model = Cat
            fields = "__all__"

    queryset = Cat.objects.all().prefetch_related('tags').order_by('createdDateTime')
    serializer_class = CatSerializer
    permission_classes = [IsAuthenticated]


class EventReminderListAPI(ListAPIView):
    class EventReminderSerializer(serializers.ModelSerializer):
        class Meta:
            model = EventReminder
            fields = "__all__"

    queryset = EventReminder.objects.all().order_by('createdDateTime')
    serializer_class = EventReminderSerializer
    permission_classes = [IsAuthenticated]
