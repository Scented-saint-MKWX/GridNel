from abc import ABC, abstractmethod
import random


class BaseOCR(ABC):
    @abstractmethod
    def read(self, image) -> tuple[str, float]:
        raise NotImplementedError


class PaddleOCRImpl(BaseOCR):
    def read(self, image) -> tuple[str, float]:
        # Swappable OCR engine surface; demo fallback keeps container lightweight.
        sample = random.choice([
            ("MH12AB1284", 0.96),
            ("MH12AB1234", 0.89),
            ("DL05CD4321", 0.92),
            ("UP16EF7654", 0.87),
        ])
        return sample
