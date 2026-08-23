# ============================================================
# PRICE CALCULATION
# ============================================================

def calculate_pc_price(configuration):

    total = 0

    for component in configuration.values():

        total += component

    return total