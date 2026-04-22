# BLOCO 1 (CORE — obrigatório)

import streamlit as st


USUARIOS = {
    "Sandro": "San123",
    "Admin": "Admin123",
    "Jheniffer": "Jheni123"
}


def verificar_login(usuario, senha):
    return USUARIOS.get(usuario) == senha


def tela_login():
    st.title("🔐 Login do Sistema")
    st.caption("Acesso restrito à locadora")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        entrar = st.form_submit_button("Entrar")

        if entrar:
            if verificar_login(usuario, senha):
                st.session_state["logado"] = True
                st.session_state["usuario"] = usuario
                st.success("Login realizado com sucesso.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")


def logout():
    st.session_state["logado"] = False
    st.session_state["usuario"] = ""
    st.rerun()