from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from planner.exceptions import PlannerError
from planner.serializers import RouteQuerySerializer
from planner.services.route_planner import plan_route
from planner.services.stations import places_payload


class RouteView(APIView):
    def get(self, request):
        return self._plan(request.query_params)

    def post(self, request):
        return self._plan(request.data)

    def _plan(self, data):
        serializer = RouteQuerySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = plan_route(
                serializer.validated_data["start"],
                serializer.validated_data["finish"],
            )
        except PlannerError as exc:
            return Response({"detail": str(exc)}, status=exc.status)
        return Response(payload)


class PlacesView(APIView):
    def get(self, request):
        return Response(places_payload())


def map_view(request):
    response = render(
        request,
        "planner/map.html",
        {
            "start": request.GET.get("start", "Chicago, IL"),
            "finish": request.GET.get("finish", "Dallas, TX"),
        },
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response
