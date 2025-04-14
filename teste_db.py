from app.database import get_conexão_db

connection = get_conexão_db()

if connection and connection.is_connected():
    print("Conseguiu se conectar.")
    connection.close()
else:
    print("Falaha ao tentar se conectar.")