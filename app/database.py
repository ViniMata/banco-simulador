import mysql.connector
from app.config import Config

def get_conexão_db():
    try:
        connection = mysql.connector.connect(
            host = Config.DB_HOST,
            user = Config.DB_USER,
            password = Config.DB_PASSWORD, 
            database = Config.DB_NAME
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None