from rest_framework.decorators import api_view
from rest_framework.response import Response

from planner.services import PlanError, build_plan


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["POST"])
def plan_trip(request):
    try:
        plan = build_plan(request.data)
    except PlanError as exc:
        return Response({"error": exc.code, "message": exc.message}, status=exc.status)
    return Response(plan)
