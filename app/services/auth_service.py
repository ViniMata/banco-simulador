from app.database import get_conexão_db
from app.config import Config
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from flask import Blueprint, request, jsonify
import mysql.connector

bcrypt = Bcrypt()

class AuthService:

    @staticmethod
    def verificar_existencia_conta(id):
        db = get_conexão_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, saldo FROM contas WHERE id = %s", (id,))
            conta = cursor.fetchone()
            return conta
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def buscar_usuario_por_username(username):
        db = get_conexão_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, senha_hash FROM usuarios WHERE username = %s", (username,))
            usuario = cursor.fetchone()
            return usuario
        except mysql.connector.Error as err:
            raise err
        finally:
            cursor.close()
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
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT role FROM usuarios WHERE id = %s", (user_id,))
            usuario = cursor.fetchone()
            cursor.close()
            return usuario and usuario["role"] == "admin"
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
    
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
    def autenticar_usuario():
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return None
        token = token.split(" ")[1]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return int(user_id)
        except JWTError:
            return None
    
    @staticmethod
    def obter_data_de_criacao_por_id(user_id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("SELECT username, criado_em FROM usuarios WHERE id = %s", (user_id,))
            usuario = cursor.fetchone()
            return {
                "username" : usuario[0],
                "criado_em" : usuario[1].isoformat()
            }
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def encode_password(senha):
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        return senha_hash
    
    @staticmethod
    def verificar_senha(senha_hash, senha_digitada):
        return bcrypt.check_password_hash(senha_hash, senha_digitada)
          
    @staticmethod
    def formatar_resposta_token(token):
        return {"access_token":token, 
                        "token_type":"bearer",
                        "expira_em":(datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()}
    

    @staticmethod
    def inserir_usuario_na_db(username, senha_hash):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "INSERT INTO usuarios (username, senha_hash, role) VALUES (%s, %s,%s)",
            (username, senha_hash, "cliente")
            )
            
            return cursor.lastrowid
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def inserir_conta_na_db(nome, usuario_id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO contas (nome_titular, usuario_id) VALUES(%s,%s)",(nome,usuario_id))
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
    
    @staticmethod
    def commitar_na_db():
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            db.commit()
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
