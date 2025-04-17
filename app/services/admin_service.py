from app.database import get_conexão_db
from app.config import Config
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from flask import Blueprint, request, jsonify
import mysql.connector

bcrypt = Bcrypt()

class AdminService():
    @staticmethod
    def listar_todas_as_contas():
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM contas;")
            colunas = [desc[0] for desc in cursor.description]
            dados = cursor.fetchall()
        
            contas =[dict(zip(colunas,linha)) for linha in dados]
            return contas
        except mysql.connector.Error as err:
            raise err
        finally:
            cursor.close()

    @staticmethod
    def inserir_admin_na_db(username, senha_hash):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "INSERT INTO usuarios (username, senha_hash, role) VALUES (%s,%s,%s)",
            (username, senha_hash, "admin")
        )
            
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()