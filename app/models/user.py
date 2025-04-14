from dataclasses import dataclass

@dataclass
class User:
    username: str
    nome: str
    senha_hash: str
    role: str