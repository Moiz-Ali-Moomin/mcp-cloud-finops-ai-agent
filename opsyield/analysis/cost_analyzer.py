class CostAnalyzer:

    def __init__(self, provider):
        self.provider = provider

    def calculate(self, resources):

        total = 0

        for r in resources:
            total += self.provider.price(r)

        return total
