from dataclasses import dataclass
from typing import Optional

@dataclass
class Transacao:
    tipo : str
    valor : float
    conta_id : int
    conta_destino_id : Optional[int] = None