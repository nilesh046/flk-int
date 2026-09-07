from abc import ABC, abstractmethod


class PaymentStrategy(ABC):
    @abstractmethod
    def apply(self, customer, amount: float) -> None:
        pass
