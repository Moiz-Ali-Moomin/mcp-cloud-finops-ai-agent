from typing import Optional

from ..core.models import Resource

RIGHTSIZE_MAP = {
    "e2-medium": "e2-small",
    "e2-small": "e2-micro",
}


class Rightsizer:

    def suggest(self, resource: Resource) -> Optional[str]:
        """Suggest a smaller instance type if CPU utilization is low."""
        cpu_avg = resource.cpu_avg
        instance_type = resource.class_type

        if cpu_avg is not None and cpu_avg < 0.20 and instance_type:
            return RIGHTSIZE_MAP.get(instance_type)

        return None
