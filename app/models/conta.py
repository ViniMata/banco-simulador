from dataclasses import dataclass

@dataclass
class Conta:
    nome_titular : str
    saldo : float
    status : str
