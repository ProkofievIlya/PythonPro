from rest_framework.throttling import AnonRateThrottle


class TokenObtainThrottle(AnonRateThrottle):
    """Окремий (жорсткіший) ліміт на отримання JWT - захист від підбору паролів."""

    scope = "token"
