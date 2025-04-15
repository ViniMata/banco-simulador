from app.database import get_conexão_db
from app.config import Config
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError

bcrypt = Bcrypt()

class AuthService:

    @staticmethod
    def verificar_existencia_conta(id):
        db = get_conexão_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, saldo FROM contas WHERE id = %s", (id,))
        conta = cursor.fetchone()
        return conta

    @staticmethod
    def criar_token_acesso(user_id:int):
        expira_em = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user_id),
            "exp": expira_em
        }

        token = jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

        return token
    
    @staticmethod
    def confirmacao_admin(user_id):
        db = get_conexão_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT role FROM usuarios WHERE id = %s", (user_id,))
        usuario = cursor.fetchone()
        cursor.close()
        return usuario and usuario["role"] == "admin"
    
    @staticmethod
    def obter_usuario_atual(token:str):
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return int(user_id)
        except JWTError:
            return None

    @staticmethod
    def encode_password(senha):
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        return senha_hash
    
    @staticmethod
    def verificar_senha(senha_hash, senha_digitada):
        if bcrypt.check_password_hash(senha_hash, senha_digitada):
            return True
        else:
            return False