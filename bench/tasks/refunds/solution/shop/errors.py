class OrderNotFound(Exception):
    pass


class OrderNotPayable(Exception):
    """The order is already paid."""


class OrderNotRefundable(Exception):
    """Only paid and awaiting_cash orders can be refunded."""


class PaymentDeclined(Exception):
    """The bank declined the payment. Retrying with the same card will not help."""


class PaymentUnavailable(Exception):
    """The payment service failed or did not answer. Retrying later may help."""


class RefundUnavailable(Exception):
    """The refund service failed or did not answer. The order is unchanged; retrying later may help."""
