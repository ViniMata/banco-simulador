from app.database import get_conexão_db
from app.config import Config
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
from flask import Blueprint, request, jsonify
import mysql.connector

bcrypt = Bcrypt()

class ContaService():
    @staticmethod
    def pegar_dados_do_extrato(id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("""
            SELECT tipo, valor, data_hora, conta_destino_id
            FROM transacoes
            WHERE conta_id = %s OR conta_destino_id = %s
            ORDER BY data_hora DESC
            """, (id,id))
            return cursor.fetchall()

        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def somas_totais(id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("""
            SELECT
                SUM(CASE WHEN tipo = 'deposito' THEN valor ELSE 0 END) AS total_depositos,
                SUM(CASE WHEN tipo = 'saque' THEN valor ELSE 0 END) AS total_saques,
                SUM(CASE WHEN tipo = 'transferencia' AND conta_id = %s THEN valor ELSE 0 END) AS total_transferencias_enviadas,
                SUM(CASE WHEN tipo = 'transferencia' AND conta_destino_id = %s THEN valor ELSE 0 END) AS total_transferencias_recebidas
                FROM transacoes
                WHERE conta_id = %s OR conta_destino_id = %s
                """, (id,id,id,id))
            return cursor.fetchone()
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def retorno_extrato(conta, historico, totais, id):
        try:
            return {
            "conta_id":id,
            "saldo_atual": conta["saldo"],
            "total_depositos": totais["total_depositos"] or 0,
            "total_saques": totais["total_saques"] or 0,
            "total_transferencias_enviadas": totais["total_transferencias_enviadas"] or 0,
            "total_transferencias_recebidas": totais["total_transferencias_recebidas"] or 0,
            "transacoes": historico
        }

        except Exception as err:
            return err
        
    @staticmethod
    def executar_deposito(deposito, id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "UPDATE contas SET saldo = saldo + %s WHERE id = %s",
            (deposito, id)
        )
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
        
    @staticmethod
    def registrar_deposito(deposito, id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "INSERT INTO transacoes (tipo,valor,conta_id) VALUES (%s,%s,%s)",
            ("deposito", deposito, id)
            )
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def executar_saque(saque, id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "UPDATE contas SET saldo = saldo - %s WHERE id = %s ",
            (saque, id)
        )
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
        
    @staticmethod
    def registrar_saque(saque, id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
            "INSERT INTO transacoes (tipo, valor, conta_id) VALUES (%s,%s,%s)",
            ("saque", saque, id)
            )
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def verificar_saldo_conta(id):
        db = get_conexão_db()
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT saldo FROM contas WHERE id = %s", (id,))
            return cursor.fetchone()
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def validar_numero_positivo(valor, nome_do_campo):
        try:
            valor = float(valor)
            if valor <= 0:
                raise ValueError
            return valor
        except ValueError:
            raise Exception(f"O campo '{nome_do_campo}' precisa ser um número positivo.")
        
    @staticmethod
    def iniciar_transacao():
        db = get_conexão_db()
        try:
            cursor = db.cursor()
        
            if db.in_transaction:
                db.rollback()
        
            db.start_transaction()
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def realizar_transferencias(valor, conta_origem, conta_destino):
        db = get_conexão_db()
        try:    
            cursor = db.cursor()
            cursor.execute(
            "UPDATE contas SET saldo = saldo - %s WHERE id = %s",
            (valor,conta_origem))

            cursor.execute(
            "UPDATE contas SET saldo = saldo + %s WHERE id = %s",
            (valor,conta_destino))
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def registrar_transferencias(valor, conta_origem, conta_destino):
        db = get_conexão_db()
        try:    
            cursor = db.cursor()

            cursor.execute(
            "INSERT INTO transacoes (tipo, valor, conta_id, conta_destino_id) VALUES (%s,%s,%s,%s)",
            ("transferencia", -valor, conta_origem, conta_destino)) 

        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def deletar_conta(id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute("DELETE FROM contas WHERE id = %s",(id,))
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()

    @staticmethod
    def validar_status(novo_status):
        if novo_status not in ["ativo", "inativo"]:
            raise Exception("Status inválido. Use 'ativo' ou 'inativo'.")
        
    @staticmethod
    def mudar_status(novo_status, id):
        db = get_conexão_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE contas SET status = %s WHERE id = %s",
                (novo_status, id)
            )
        except mysql.connector.Error as err:
            db.rollback()
            raise err
        finally:
            cursor.close()
