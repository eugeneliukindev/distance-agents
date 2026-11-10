class OrderNotFound(Exception):
    pass


class OrderNotPayable(Exception):
    """The order is already paid."""


class OrderNotEditable(Exception):
    """Only a new order can be changed."""


class PaymentDeclined(Exception):
    """The bank declined the payment. Retrying with the same card will not help."""


class PaymentUnavailable(Exception):
    """The payment service failed or did not answer. Retrying later may help."""
