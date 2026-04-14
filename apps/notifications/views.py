from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NotificationLog


class NotificationHealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({"count": NotificationLog.objects.count()})


# Create your views here.
