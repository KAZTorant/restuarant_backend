import json

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from rest_framework import serializers

# action_flag → human-readable map
ACTION_MAP = {
    ADDITION: "addition",   # 1
    CHANGE:   "change",     # 2
    DELETION: "deletion",   # 3
}

ACTION_LABEL_MAP = {
    ADDITION: "Əlavəetmə",
    CHANGE:   "Dəyişiklik",
    DELETION: "Silmə",
}


class LogEntrySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Django admin LogEntry.
    Returns all fields needed for the Flutter admin panel log screen.
    """
    # User info — FK
    user_id       = serializers.IntegerField(source="user.id", read_only=True)
    username      = serializers.CharField(source="user.username", read_only=True)
    user_fullname = serializers.SerializerMethodField()

    # Content-type info
    app_label     = serializers.CharField(
        source="content_type.app_label", read_only=True
    )
    model         = serializers.CharField(
        source="content_type.model", read_only=True
    )

    # Action
    action        = serializers.SerializerMethodField()   # "addition" / "change" / "deletion"
    action_label  = serializers.SerializerMethodField()   # "Əlavəetmə" / "Dəyişiklik" / "Silmə"

    # Parsed change_message  →  list of dicts (already JSON-parseable in DB)
    change_summary = serializers.SerializerMethodField()

    # Human-readable message via Django built-in
    change_message_display = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = [
            "id",
            "action_time",
            "user_id",
            "username",
            "user_fullname",
            "app_label",
            "model",
            "object_id",
            "object_repr",
            "action",
            "action_label",
            "action_flag",
            "change_summary",
            "change_message_display",
        ]
        read_only_fields = fields

    # ── helpers ────────────────────────────────────────────────

    def get_user_fullname(self, obj):
        u = obj.user
        full = f"{u.first_name} {u.last_name}".strip()
        return full if full else u.username

    def get_action(self, obj):
        return ACTION_MAP.get(obj.action_flag, "unknown")

    def get_action_label(self, obj):
        return ACTION_LABEL_MAP.get(obj.action_flag, "Naməlum")

    def get_change_summary(self, obj):
        """
        Raw JSON parsed from change_message field.
        e.g. [{"changed": {"fields": ["Username"]}}]
        Returns [] if not parseable (Deletion entries).
        """
        if not obj.change_message:
            return []
        try:
            return json.loads(obj.change_message)
        except (ValueError, TypeError):
            return []

    def get_change_message_display(self, obj):
        """
        Django built-in get_change_message() — localized string.
        e.g. "Username dəyişdirildi."
        """
        return obj.get_change_message() or ""
