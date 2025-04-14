import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')

    ALGORITHM = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = os.getenv("DB_PASSWORD") 
    DB_NAME = "banco_simulador"
    