from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.services.conta_service import ContaService

conta_bp = Blueprint('conta', __name__, url_prefix="/conta")

@conta_bp.route("/conta/<int:id>/extrato", methods=["GET"])
def mostrar_extrato(id):
    try:    
        conta = AuthService.verificar_existencia_conta(id)
        if not conta:
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404
 
        
        historico = ContaService.pegar_dados_do_extrato(id)
        
        totais = ContaService.somas_totais(id)
        
        extrato = ContaService.retorno_extrato(conta, historico, totais, id)

        return jsonify(extrato), 200
            
    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500
    
@conta_bp.route("/conta/<int:id>/depositar", methods=["PUT"])
def depositar(id):
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    deposito = dados.get("deposito")
    if not deposito:
        return jsonify({"erro": "Campo 'deposito' é obrigatório"}), 400
    
    deposito = ContaService.validar_numero_positivo(deposito, "deposito")

    try:
        conta = AuthService.verificar_existencia_conta(id)
        if not conta:
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404

        ContaService.executar_deposito(deposito, id)

        ContaService.registrar_deposito(deposito, id)
        AuthService.commitar_na_db()
        return jsonify({"mensagem":f"Depósito de R$ {int(deposito)} realizado com sucesso na conta de id: {id}"})

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500
    
@conta_bp.route("/conta/<int:id>/sacar", methods=["PUT"])
def sacar(id):
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    saque = dados.get("saque")

    if not saque:
        return jsonify({"erro":"O campo 'saque' é obrigatório."}),400

    saque = ContaService.validar_numero_positivo(saque, "saque")
    try:
        saldo = ContaService.verificar_saldo_conta(id)
        if not saldo:
            return jsonify({"erro": f"Conta com id {id} não encontrada"}), 404

        if saque > saldo["saldo"]:
            return jsonify({"erro":"Seu saque está maior que seu saldo."}), 400
        
        ContaService.executar_saque(saque, id)

        ContaService.registrar_saque(saque, id)
        AuthService.commitar_na_db()
        
        return jsonify({"mensagem":f"A quantidade de R$ {saque} foi sacada da conta de id {id}"})

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500
    

@conta_bp.route("/conta/transferir", methods=["POST"])
def transferir():
    user_id = AuthService.autenticar_usuario()
    if not user_id:
        return jsonify({"erro": "Não autenticado"}), 401
    
    dados = request.get_json()
    conta_origem = dados.get("conta_origem")
    conta_destino = dados.get("conta_destino")
    valor = dados.get("valor")

    if not conta_destino or not conta_origem or not valor:
        return jsonify({"erro":"É necessário preencher todos os campos."}), 400

    
    valor = ContaService.validar_numero_positivo(valor, "valor")
    
    try:
        ContaService.iniciar_transacao()

        saldo_origem = ContaService.verificar_saldo_conta(conta_origem)
        if not saldo_origem:
            return jsonify({"erro":"Usuário de origem não encontrado."}), 404

        if valor > saldo_origem[0]:
            return jsonify({"erro":"Saldo insuficiente."}), 400

        conta_destino = AuthService.verificar_existencia_conta(conta_destino)
        if not conta_destino:
            return jsonify({"erro":"Conta de destino não encontrada."}), 404

        ContaService.realizar_transferencias(valor, conta_origem, conta_destino)

        ContaService.registrar_transferencias(valor, conta_origem, conta_destino)     

        AuthService.commitar_na_db()
        return jsonify({"mensagem":f"Transferência de R$ {valor:.2f} realizada com sucesso da conta {conta_origem} para {conta_destino}"})

    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500
    
@conta_bp.route("/conta/deletar/<int:id>", methods=["DELETE"])
def deletar_conta(id):
    try:
        user_id = AuthService.autenticar_usuario()
        if not user_id:
            return jsonify({"erro": "Não autenticado"}), 401

        if not AuthService.confirmacao_admin(user_id):
            return jsonify({"erro": "Acesso negado. Somente administradores podem atualizar o status de contas."}), 403
        

        conta = AuthService.verificar_existencia_conta(id)

        if not conta:
            return(jsonify({"erro":f"Conta com o id {id} não encontrada "})), 404
        
        ContaService.deletar_conta(id)
        AuthService.commitar_na_db()

        return(jsonify({"mensagem":f"Conta com id {id} deletada com êxito"})),200
    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500

@conta_bp.route("/conta/<int:id>/atualizar_status", methods=["PUT"])
def atualizar_status(id):
    try:
        user_id = AuthService.autenticar_usuario()
        if not user_id:
            return jsonify({"erro": "Não autenticado"}), 401
        
        if not AuthService.confirmacao_admin(user_id):
            return jsonify({"erro": "Acesso negado. Somente administradores podem atualizar o status de contas."}), 403

        conta = AuthService.verificar_existencia_conta(id)

        if not conta:
            return(jsonify({"erro":f"Conta com o id {id} não encontrada "})), 404

        dados = request.get_json()
        novo_status = dados.get("status")
        
        if not novo_status:
            return jsonify({"erro": "Campo 'status' é obrigatório"}), 400

        ContaService.validar_status(novo_status)

        ContaService.mudar_status(novo_status, id)

        AuthService.commitar_na_db()
        
        return jsonify({"mensagem": "Status atualizado com sucesso!"}), 200
    
    except Exception as err:
        return jsonify({"erro": f"Ocorreu um erro inesperado: {err}"}), 500