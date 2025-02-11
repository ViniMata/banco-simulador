import mysql.connector
from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

bcrypt = Bcrypt(app)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = os.getenv("DB_PASSWORD"), 
    database = "banco_simulador"
)
def criar_token_acesso(user_id:int):
    expira_em = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expira_em
    }

    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm=ALGORITHM)

    return token

def obter_usuario_atual(token:str):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None

def autenticar_usuario():
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return None
    token = token.split(" ")[1]
    return obter_usuario_atual(token)

def confirmacao_admin(user_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT role FROM usuarios WHERE id = %s", (user_id,))
    usuario = cursor.fetchone()
    cursor.close()
    return usuario and usuario["role"] == "admin"

@app.route("/")
def home():
    return 'Bem vindo ao simulador bancario'

@app.route("/registrar", methods=["POST"])
def registrar():
    dados = request.get_json()
    username = dados.get("username")
    nome = dados.get("nome") 
    senha = dados.get("senha")

    if not username or not senha or not nome:
        return jsonify({"erro": "Username, nome e senha são obrigatórios"}), 400
    
    try:
        cursor = db.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"erro":"Username já está em uso"}), 400
        
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        cursor.execute(
            "INSERT INTO usuarios (username, senha_hash, role) VALUES (%s, %s,%s)",
            (username, senha_hash, "cliente")
        )

        usuario_id = cursor.lastrowid

        cursor.execute("INSERT INTO contas (nome_titular, usuario_id) VALUES(%s,%s)",(nome,usuario_id))

        db.commit()
        return jsonify({"mensagem":"Usuário registrado com sucesso! Sua conta foi criada!"}), 201

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close()  




@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    username = dados.get("username")
    senha = dados.get("senha")

    if not username or not senha:
        return jsonify({"erro": "Username e senha são obrigatórios"}), 400
    
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, senha_hash FROM usuarios WHERE username = %s", (username,))
        usuario = cursor.fetchone()

        if not usuario or not bcrypt.check_password_hash(usuario["senha_hash"], senha):
            return jsonify({"erro":"Credenciais inválidas"}), 401
        
        token = criar_token_acesso(usuario["id"])
        return jsonify({"access_token":token, 
                        "token_type":"bearer",
                        "expira_em":(datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()})

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close()  

@app.route("/perfil", methods=["GET"])
def perfil():
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro":"Não autenticado"}), 401
    try:
        cursor = db.cursor()
        cursor.execute("SELECT username, criado_em FROM usuarios WHERE id = %s", (user_id,))
        usuario = cursor.fetchone()
        cursor.close()

        return jsonify(usuario), 200
    except mysql.connector.Error as err:
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close()

@app.route("/contas")
def consultar_contas():
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro":"Não autenticado"}), 401
    
    if not confirmacao_admin(user_id):
        return jsonify({"erro":"Acesso negado. Somente administradores podem ter acesso a lista geral de contas."})

    cursor = db.cursor()
    cursor.execute("SELECT * FROM contas;")
    colunas = [desc[0] for desc in cursor.description]
    dados = cursor.fetchall()
        
    contas =[dict(zip(colunas,linha)) for linha in dados]
    cursor.close()
    return jsonify(contas)

@app.route("/conta/<int:id>/extrato", methods=["GET"])
def mostrar_extrato(id):
    try:    
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, saldo FROM contas WHERE id = %s", (id,))
        conta = cursor.fetchone()
        if not conta:
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404
 
        cursor.execute("""
            SELECT tipo, valor, data_hora, conta_destino_id
            FROM transacoes
            WHERE conta_id = %s OR conta_destino_id = %s
            ORDER BY data_hora DESC
        """, (id,id))
        historico = cursor.fetchall()
        
        cursor.execute("""
            SELECT
                SUM(CASE WHEN tipo = 'deposito' THEN valor ELSE 0 END) AS total_depositos,
                SUM(CASE WHEN tipo = 'saque' THEN valor ELSE 0 END) AS total_saques,
                SUM(CASE WHEN tipo = 'transferencia' AND conta_id = %s THEN valor ELSE 0 END) AS total_transferencias_enviadas,
                SUM(CASE WHEN tipo = 'transferencia' AND conta_destino_id = %s THEN valor ELSE 0 END) AS total_transferencias_recebidas
            FROM transacoes
            WHERE conta_id = %s OR conta_destino_id = %s
        """, (id,id,id,id))
        totais = cursor.fetchone()
        
        return jsonify({
            "conta_id":id,
            "saldo_atual": conta["saldo"],
            "total_depositos": totais["total_depositos"] or 0,
            "total_saques": totais["total_saques"] or 0,
            "total_transferencias_enviadas": totais["total_transferencias_enviadas"] or 0,
            "total_transferencias_recebidas": totais["total_transferencias_recebidas"] or 0,
            "transacoes": historico
        }), 200
            
    except mysql.connector.Error as err:
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close()

@app.route("/admin/criar", methods=["POST"])
def criar_admins():
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    if not confirmacao_admin(user_id):
        return jsonify({"erro": "Acesso negado. Somente administradores podem criar novos administradores."}), 403

    dados = request.get_json()
    username = dados.get("username")
    senha = dados.get("senha")

    if not username or not senha:
        return jsonify({"erro":"Username e senhas são obrigatórios"})
    
    try:
        cursor = db.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"erro":"Username já está em uso"}), 400
        
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        cursor.execute(
            "INSERT INTO usuarios (username, senha_hash, role) VALUES (%s,%s,%s)",
            (username, senha_hash, "admin")
        )
        db.commit()
        return jsonify({"mensagem":"Conta de aministrador criado com sucesso!"})

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close() 

@app.route("/conta/<int:id>/atualizar_status", methods=["PUT"])
def atualizar_status(id):
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    if not confirmacao_admin(user_id):
        return jsonify({"erro": "Acesso negado. Somente administradores podem atualizar o status de contas."}), 403

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, usuario_id FROM contas WHERE id = %s",(id,))
    conta = cursor.fetchone()

    if not conta:
        return jsonify({"erro": "Conta não encontrada."}), 404

    dados = request.get_json()
    novo_status = dados.get("status")
    
    if not novo_status:
        return jsonify({"erro": "Campo 'status' é obrigatório"}), 400

    if novo_status not in ["ativo", "inativo"]:
        return jsonify({"erro": "Status inválido. Use 'ativo' ou 'inativo'."}), 400

    try:
        cursor.execute(
            "UPDATE contas SET status = %s WHERE id = %s",
            (novo_status, id)
        )
        db.commit()
        return jsonify({"mensagem": "Status atualizado com sucesso!"}), 200

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500
    finally:
        cursor.close()

@app.route("/conta/<int:id>/depositar", methods=["PUT"])
def depositar(id):
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    deposito = dados.get("deposito")
    if not deposito:
        return jsonify({"erro": "Campo 'deposito' é obrigatório"}), 400
    try:
        deposito = float(deposito)
        if deposito <= 0:
            return jsonify({"erro": "O depósito precisar ter um valor positivo."}), 400
    except ValueError:
        return jsonify({"erro":"O valor deve ser um número."}), 400

    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM contas WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404

        cursor.execute(
            "UPDATE contas SET saldo = saldo + %s WHERE id = %s",
            (deposito, id)
        )

        cursor.execute(
            "INSERT INTO transacoes (tipo,valor,conta_id) VALUES (%s,%s,%s)",
            ("deposito", deposito, id)
        )
        db.commit()
        return jsonify({"mensagem":f"O valor de  R$ {int(deposito)} na conta de id: {id}"})

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500       
    finally:
        cursor.close()

@app.route("/conta/<int:id>/sacar", methods=["PUT"])
def sacar(id):
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    saque = dados.get("saque")

    if not saque:
        return jsonify({"erro":"O campo 'saque' é obrigatório."}),400

    try:
        saque = float(saque)
        if saque <= 0:
            return jsonify({"erro": "O depósito precisar ter um valor positivo."}), 400
    except ValueError:
        return jsonify({"erro":"O valor deve ser um número."}), 400
    try:
        cursor = db.cursor()
        cursor.execute("SELECT saldo FROM contas WHERE id = %s", (id,))
        saldo = cursor.fetchone()
        if not saldo:
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404

        if saque > saldo[0]:
            return jsonify({"erro":"Seu saque está maior que seu saldo."}), 400
        
        cursor.execute(
            "UPDATE contas SET saldo = saldo - %s WHERE id = %s ",
            (saque, id)
        )

        cursor.execute(
            "INSERT INTO transacoes (tipo, valor, conta_id) VALUES (%s,%s,%s)",
            ("saque", saque, id)
        )

        db.commit()
        return jsonify({"Mensagem":f"A quantidade de R$ {saque} foi sacada da conta de id {id}"})

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500       
    finally:
        cursor.close()


@app.route("/conta/transferir", methods=["POST"])
def transferir():
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    conta_origem = dados.get("conta_origem")
    conta_destino = dados.get("conta_destino")
    valor = dados.get("valor")

    if not conta_destino or not conta_origem or not valor:
        return jsonify({"erro":"É necessário preencher todos os campos."}), 400

    try:
        valor = float(valor)
        if valor <= 0:
            return jsonify({"erro":"O valor deve ser positivo"}),400
    except ValueError:
        return jsonify({"erro":"O valor deve ser um número."}), 400
    
    try:
        cursor = db.cursor()
        
        if db.in_transaction:
            db.rollback()
        
        db.start_transaction()

        cursor.execute("SELECT saldo FROM contas WHERE id = %s",(conta_origem,))
        saldo_origem = cursor.fetchone()
        if not saldo_origem:
            db.rollback()
            return jsonify({"erro":"Usuário de origem não encontrado."}), 404

        if valor > saldo_origem[0]:
            db.rollback()
            return jsonify({"erro":"Saldo insuficiente."}), 400

        cursor.execute("SELECT id FROM contas WHERE id = %s", (conta_destino,))
        if not cursor.fetchone():
            db.rollback()
            return jsonify({"erro":"Usuário do destino não encontrado."}), 404

        cursor.execute(
            "UPDATE contas SET saldo = saldo - %s WHERE id = %s",
            (valor,conta_origem)
        )

        cursor.execute(
            "UPDATE contas SET saldo = saldo + %s WHERE id = %s",
            (valor,conta_destino)
        )

        cursor.execute(
            "INSERT INTO transacoes (tipo, valor, conta_id, conta_destino_id) VALUES (%s,%s,%s,%s)",
            ("transferencia", -valor, conta_origem, conta_destino)
        )      

        db.commit()
        return jsonify({"mensagem":"Transerência realizada com sucesso!"})

    except mysql.connector.Error as err:
        db.rollback()
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500       
    finally:
        cursor.close()

@app.route("/conta/deletar/<int:id>", methods=["DELETE"])
def deletar_conta(id):
    user_id = autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401

    if not confirmacao_admin(user_id):
        return jsonify({"erro": "Acesso negado. Somente administradores podem atualizar o status de contas."}), 403
     
    cursor = db.cursor()
    cursor.execute("SELECT * FROM contas WHERE id = %s",(id,))
    conta = cursor.fetchone()

    if not conta:
        cursor.close()
        return(jsonify({"erro":"Conta com o id {id} não encontrada "})), 404
    
    cursor.execute("DELETE FROM contas WHERE id = %s",(id,))
    db.commit()
    
    cursor.close()

    return(jsonify({"mensagem":"Conta deletada com êxito"})),200

if __name__=="__main__":
    cursor = db.cursor()
    cursor.execute("SELECT DATABASE();")
    database_name = cursor.fetchone()
    print(f"Conectado ao banco de dados: {database_name[0]}")
    cursor.close()
    app.run(debug=True)