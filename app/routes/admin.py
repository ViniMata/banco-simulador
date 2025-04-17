from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.services.admin_service import AdminService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/contas", methods=["GET"])
def listar_todas_as_contas():
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro":"Não autenticado"}), 401
    
    if not AuthService.confirmacao_admin(user_id):
        return jsonify({"erro":"Acesso negado. Somente administradores podem ter acesso a lista geral de contas."}), 401
    try:
        contas = AdminService.listar_todas_as_contas()
        return jsonify(contas), 200
    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500

@admin_bp.route("/criar", methods=["POST"])
def criar_admins():
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    if not AuthService.confirmacao_admin(user_id):
        return jsonify({"erro": "Acesso negado. Somente administradores podem criar novos administradores."}), 403

    dados = request.get_json()
    username = dados.get("username")
    senha = dados.get("senha")

    if not username or not senha:
        return jsonify({"erro":"Username e senhas são obrigatórios"}), 400
    
    try: 
        usuario = AuthService.buscar_usuario_por_username(username)
        if usuario:
            return jsonify({"erro":"Username já está em uso"}), 400
        
        senha_hash = AuthService.encode_password(senha)

        AdminService.inserir_admin_na_db(username, senha_hash)

        AuthService.commitar_na_db()
        return jsonify({"mensagem":"Conta de aministrador criado com sucesso!"}), 201

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500 