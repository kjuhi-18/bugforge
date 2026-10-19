def calculate_discount(price):
    if price > 1000:  # Intentional bug: requirement says >= 1000
        return price * 0.90
    return price
