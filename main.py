from flask import Flask
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.conta import conta_bp
from app.config import Config
from app import database

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    database.get_conexão_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(conta_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)