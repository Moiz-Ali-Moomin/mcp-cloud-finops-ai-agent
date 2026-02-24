RIGHTSIZE_MAP = {
    "e2-medium": "e2-small",
    "e2-small": "e2-micro"
}


class Rightsizer:

    def suggest(self, instance_type, cpu_avg):

        if cpu_avg and cpu_avg < 0.20:
            return RIGHTSIZE_MAP.get(instance_type)

        return None
