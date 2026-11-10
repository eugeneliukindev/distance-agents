from datetime import timedelta


def delivery_date(order):
    # moscow is faster
    if order.city == "Moscow" or order.city == "Moskva":
        days = 2
    else:
        days = 5
    # couriers do not work on the weekend
    if order.created_at.weekday() == 4:
        days += 2
    return (order.created_at + timedelta(days=days)).date()
