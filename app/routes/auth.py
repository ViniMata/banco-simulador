from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    username = dados.get("username")
    senha = dados.get("senha")

    if not username or not senha:
        return jsonify({"erro": "Username e senha são obrigatórios"}), 400
    
    try:
        usuario = AuthService.buscar_usuario_por_username(username)

        if not usuario or not AuthService.verificar_senha(usuario["senha_hash"], senha):
            return jsonify({"erro":"Credenciais inválidas"}), 401
        
        token = AuthService.criar_token_acesso(usuario["id"])
        return jsonify(AuthService.formatar_resposta_token(token)), 200

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500
    
@auth_bp.route("/registrar", methods=["POST"])
def registrar():
    dados = request.get_json()
    username = dados.get("username")
    nome = dados.get("nome") 
    senha = dados.get("senha")

    if not username or not senha or not nome:
        return jsonify({"erro": "Username, nome e senha são obrigatórios"}), 400
    
    try:
        usuario = AuthService.buscar_usuario_por_username(username)
        if usuario:
            return jsonify({"erro":"Username já está em uso"}), 400
        
        senha_hash = AuthService.encode_password(senha)

        usuario_id = AuthService.inserir_usuario_na_db(username, senha_hash)

        AuthService.inserir_conta_na_db(nome, usuario_id)

        AuthService.commitar_na_db()
        return jsonify({"mensagem":"Usuário registrado com sucesso! Sua conta foi criada!"}), 201

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500  

@auth_bp.route("/perfil", methods=["GET"])
def perfil():
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro":"Não autenticado"}), 401
    try:
        usuario = AuthService.obter_data_de_criacao_por_id(user_id)

        return jsonify(usuario), 200
    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500