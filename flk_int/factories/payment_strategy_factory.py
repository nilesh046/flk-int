from flk_int.strategies.payment_strategy import PaymentStrategy


class PaymentStrategyFactory:
    @staticmethod
    def get_strategy(payment_method: str) -> PaymentStrategy:
        raise NotImplementedError
