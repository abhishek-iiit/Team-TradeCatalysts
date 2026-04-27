from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_staff']
        read_only_fields = fields


class EmailSettingsSerializer(serializers.ModelSerializer):
    """Allows the user to read/update their SMTP app password."""
    smtp_password = serializers.CharField(
        max_length=255, allow_blank=True, required=False,
        write_only=False,
        style={'input_type': 'password'},
    )
    has_smtp_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['email', 'smtp_password', 'has_smtp_password']
        read_only_fields = ['email']

    def get_has_smtp_password(self, obj):
        return bool(obj.smtp_password)
