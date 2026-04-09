from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from rest_framework import filters, generics

from apps.users.apis.admin.logentry_serializers import LogEntrySerializer
from apps.users.auth import AdminTokenAuthentication
from apps.users.permissions import IsAdminPanelUser


class AdminRequiredMixin:
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAdminPanelUser]


class AdminLogEntryListAPIView(AdminRequiredMixin, generics.ListAPIView):
    """
    GET /api/admin/users/log-entries/

    Django Admin Log yazılarının siyahısı.
    Read-only, paginated (20/page), filterable, searchable, orderable.

    Filters:
        ?action=addition|change|deletion
        ?app_label=users|orders|payments|meals|...
        ?model=user|order|payment|...
        ?user_id=<int>
        ?year=2025|2026
        ?search=<string>       — object_repr, username üzrə
        ?ordering=action_time  — default: -action_time (ən yeni əvvəl)
    """
    serializer_class = LogEntrySerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ["object_repr", "user__username", "user__first_name", "user__last_name"]
    ordering_fields  = ["id", "action_time", "action_flag"]
    ordering         = ["-action_time"]   # ən yeni əvvəl

    # Map query param string → action_flag int
    ACTION_FILTER_MAP = {
        "addition": ADDITION,
        "change":   CHANGE,
        "deletion": DELETION,
    }

    def get_queryset(self):
        qs = (
            LogEntry.objects
            .select_related("user", "content_type")
            .order_by("-action_time")
        )

        params = self.request.query_params

        # Filter: action
        action = params.get("action", "").lower()
        if action in self.ACTION_FILTER_MAP:
            qs = qs.filter(action_flag=self.ACTION_FILTER_MAP[action])

        # Filter: app_label
        app_label = params.get("app_label")
        if app_label:
            qs = qs.filter(content_type__app_label=app_label)

        # Filter: model
        model = params.get("model")
        if model:
            qs = qs.filter(content_type__model=model)

        # Filter: user_id
        user_id = params.get("user_id")
        if user_id and user_id.isdigit():
            qs = qs.filter(user_id=int(user_id))

        # Filter: year (action_time__year)
        year = params.get("year")
        if year and year.isdigit():
            qs = qs.filter(action_time__year=int(year))

        return qs
