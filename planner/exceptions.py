class PlannerError(Exception):
    status = 400


class GeocodeError(PlannerError):
    pass


class NonUSLocationError(PlannerError):
    pass


class RoutingError(PlannerError):
    status = 502


class CannotRefuelError(PlannerError):
    pass
