from rest_framework import serializers
from .models import BusinessRequest


class BusinessRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = BusinessRequest
        fields = [
            "id",
            "user",
            "username",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "resolution",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "username",
            "created_at",
            "updated_at",
        ]

    def validate_priority(self, value):
        allowed = ["Low", "Medium", "High"]
        normalized = str(value).strip().capitalize()

        if normalized not in allowed:
            raise serializers.ValidationError(
                "Priority must be Low, Medium, or High."
            )

        return normalized

    def validate_status(self, value):
        allowed = ["Pending", "In Progress", "Completed"]

        if value not in allowed:
            raise serializers.ValidationError(
                "Status must be Pending, In Progress, or Completed."
            )

        return value

    def validate_category(self, value):
        value = str(value).strip()

        if not value:
            raise serializers.ValidationError("Category cannot be empty.")

        return value