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
    # weekend orders are handed to the courier on Monday
    start = order.created_at
    if start.weekday() == 5:
        start = start + timedelta(days=2)
    elif start.weekday() == 6:
        start = start + timedelta(days=1)
    return (start + timedelta(days=days)).date()
