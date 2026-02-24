def estimate_savings(current_cost, new_cost):

    if new_cost >= current_cost:
        return 0

    return current_cost - new_cost
