import pandas as pd
import streamlit as st
from database import conectar


def aplicar_estilo_despesas():
    st.markdown("""
    <style>
    .desp-top-card {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.16);
    }

    .desp-top-title {
        color: #f8fafc;
        font-size: 1.08rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .desp-top-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-bottom: 0;
    }

    .desp-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 12px;
    }

    .desp-box-title {
        color: #e5e7eb;
        font-size: 0.96rem;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .desp-box-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 0;
    }

    .desp-warning-box {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 10px;
        margin-bottom: 12px;
        color: #fbbf24;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)


def card_abertura_despesas():
    st.markdown("""
    <div class="desp-top-card">
        <div class="desp-top-title">Gestão de despesas</div>
        <div class="desp-top-sub">
            Controle os custos operacionais da frota por veículo, categoria, data e observações.
        </div>
    </div>
    """, unsafe_allow_html=True)


def carregar_despesas(conn):
    return pd.read_sql_query("""
        SELECT
            d.id,
            d.veiculo_id,
            v.modelo || ' - ' || v.placa AS veiculo,
            d.data_despesa,
            d.categoria,
            d.descricao,
            d.valor,
            d.observacoes
        FROM despesas_veiculo d
        INNER JOIN veiculos v ON d.veiculo_id = v.id
        ORDER BY d.id DESC
    """, conn)


def tela_despesas():
    aplicar_estilo_despesas()
    st.subheader("Despesas")
    card_abertura_despesas()

    conn = conectar()
    veiculos = pd.read_sql_query(
        "SELECT id, modelo, placa FROM veiculos ORDER BY modelo",
        conn
    )

    if veiculos.empty:
        st.info("Cadastre veículos antes de registrar despesas.")
        conn.close()
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Nova despesa", "Histórico", "Editar", "Excluir"]
    )

    with tab1:
        st.markdown("""
        <div class="desp-box">
            <div class="desp-box-title">Novo registro de despesa</div>
            <div class="desp-box-sub">
                Registre gastos extras da operação vinculando a despesa ao veículo correto.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_despesa"):
            opcoes = {
                f"{row['modelo']} - {row['placa']}": row["id"]
                for _, row in veiculos.iterrows()
            }

            veiculo_escolhido = st.selectbox("Veículo", list(opcoes.keys()))
            data_despesa = st.date_input("Data da despesa")

            col1, col2 = st.columns(2)
            with col1:
                categoria = st.selectbox(
                    "Categoria",
                    [
                        "Combustível",
                        "Lavagem",
                        "Documentação",
                        "Multa",
                        "Seguro",
                        "Guincho",
                        "Peças",
                        "Outros"
                    ]
                )
                descricao = st.text_input("Descrição")
            with col2:
                valor = st.number_input("Valor", min_value=0.0, step=50.0)
                observacoes = st.text_area("Observações")

            salvar = st.form_submit_button("Salvar despesa")

            if salvar:
                if not descricao:
                    st.error("Informe a descrição da despesa.")
                else:
                    veiculo_id = opcoes[veiculo_escolhido]
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO despesas_veiculo (
                            veiculo_id, data_despesa, categoria, descricao, valor, observacoes
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        veiculo_id,
                        str(data_despesa),
                        categoria,
                        descricao,
                        valor,
                        observacoes
                    ))
                    conn.commit()
                    st.success("Despesa registrada com sucesso.")
                    st.rerun()

    df = carregar_despesas(conn)

    with tab2:
        st.markdown("""
        <div class="desp-box">
            <div class="desp-box-title">Histórico de despesas</div>
            <div class="desp-box-sub">
                Consulte os custos lançados por veículo, categoria e período de forma mais organizada.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhuma despesa cadastrada ainda.")
        else:
            f1, f2 = st.columns([2, 1])
            with f1:
                busca = st.text_input(
                    "Buscar despesa",
                    placeholder="Digite veículo, categoria ou descrição"
                )
            with f2:
                categoria_filtro = st.selectbox(
                    "Filtrar categoria",
                    ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
                )

            df_hist = df.copy()

            if busca:
                busca_lower = busca.strip().lower()
                df_hist = df_hist[
                    df_hist["veiculo"].str.lower().str.contains(busca_lower, na=False) |
                    df_hist["categoria"].str.lower().str.contains(busca_lower, na=False) |
                    df_hist["descricao"].str.lower().str.contains(busca_lower, na=False)
                ]

            if categoria_filtro != "Todas":
                df_hist = df_hist[df_hist["categoria"] == categoria_filtro]

            total_despesas = float(df_hist["valor"].fillna(0).sum()) if not df_hist.empty else 0.0

            c1, c2 = st.columns(2)
            c1.metric("Registros encontrados", len(df_hist))
            c2.metric("Total filtrado", f"R$ {total_despesas:.2f}")

            st.dataframe(
                df_hist[[
                    "id", "veiculo", "data_despesa", "categoria", "descricao", "valor"
                ]],
                use_container_width=True
            )

            opcoes_hist = {
                f"#{row['id']} - {row['veiculo']} - {row['descricao']}": row["id"]
                for _, row in df_hist.iterrows()
            }

            if opcoes_hist:
                despesa_escolhida = st.selectbox("Selecionar despesa", list(opcoes_hist.keys()))
                despesa_id = opcoes_hist[despesa_escolhida]
                registro = df_hist[df_hist["id"] == despesa_id].iloc[0]

                st.write(f"**Veículo:** {registro['veiculo']}")
                st.write(f"**Data:** {registro['data_despesa']}")
                st.write(f"**Categoria:** {registro['categoria']}")
                st.write(f"**Descrição:** {registro['descricao']}")
                st.write(f"**Valor:** R$ {float(registro['valor'] or 0):.2f}")
                st.write(f"**Observações:** {registro['observacoes'] or '-'}")

    with tab3:
        st.markdown("""
        <div class="desp-box">
            <div class="desp-box-title">Editar despesa</div>
            <div class="desp-box-sub">
                Atualize categoria, descrição, valor ou observações de um lançamento existente.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhuma despesa cadastrada ainda.")
        else:
            opcoes_editar = {
                f"#{row['id']} - {row['veiculo']} - {row['descricao']}": row["id"]
                for _, row in df.iterrows()
            }

            despesa_editar = st.selectbox(
                "Selecione a despesa para editar",
                list(opcoes_editar.keys()),
                key="editar_despesa"
            )
            despesa_id = opcoes_editar[despesa_editar]
            registro = df[df["id"] == despesa_id].iloc[0]

            opcoes_veic = {
                f"{row['modelo']} - {row['placa']}": row["id"]
                for _, row in veiculos.iterrows()
            }

            veiculo_label_atual = next(
                (label for label, vid in opcoes_veic.items() if vid == registro["veiculo_id"]),
                list(opcoes_veic.keys())[0]
            )

            categorias = [
                "Combustível",
                "Lavagem",
                "Documentação",
                "Multa",
                "Seguro",
                "Guincho",
                "Peças",
                "Outros"
            ]
            categoria_atual = registro["categoria"] if registro["categoria"] in categorias else "Outros"

            with st.form("form_editar_despesa"):
                veiculo_escolhido = st.selectbox(
                    "Veículo",
                    list(opcoes_veic.keys()),
                    index=list(opcoes_veic.keys()).index(veiculo_label_atual)
                )
                data_despesa = st.date_input(
                    "Data da despesa",
                    value=pd.to_datetime(registro["data_despesa"]).date()
                )
                categoria = st.selectbox("Categoria", categorias, index=categorias.index(categoria_atual))
                descricao = st.text_input("Descrição", value=registro["descricao"] or "")
                valor = st.number_input(
                    "Valor",
                    min_value=0.0,
                    step=50.0,
                    value=float(registro["valor"] or 0)
                )
                observacoes = st.text_area("Observações", value=registro["observacoes"] or "")

                atualizar = st.form_submit_button("Atualizar despesa")

                if atualizar:
                    if not descricao:
                        st.error("Informe a descrição da despesa.")
                    else:
                        veiculo_id = opcoes_veic[veiculo_escolhido]

                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE despesas_veiculo
                            SET veiculo_id = ?, data_despesa = ?, categoria = ?,
                                descricao = ?, valor = ?, observacoes = ?
                            WHERE id = ?
                        """, (
                            veiculo_id,
                            str(data_despesa),
                            categoria,
                            descricao,
                            valor,
                            observacoes,
                            despesa_id
                        ))
                        conn.commit()
                        st.success("Despesa atualizada com sucesso.")
                        st.rerun()

    with tab4:
        st.markdown("""
        <div class="desp-box">
            <div class="desp-box-title">Excluir despesa</div>
            <div class="desp-box-sub">
                Remova registros incorretos com confirmação para evitar exclusões acidentais.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhuma despesa cadastrada ainda.")
        else:
            opcoes_excluir = {
                f"#{row['id']} - {row['veiculo']} - {row['descricao']}": row["id"]
                for _, row in df.iterrows()
            }

            despesa_excluir = st.selectbox(
                "Selecione a despesa para excluir",
                list(opcoes_excluir.keys()),
                key="excluir_despesa"
            )
            despesa_id = opcoes_excluir[despesa_excluir]
            registro = df[df["id"] == despesa_id].iloc[0]

            st.markdown(f"""
            <div class="desp-warning-box">
                Você está prestes a excluir a despesa <strong>{registro['descricao']}</strong> do veículo
                <strong>{registro['veiculo']}</strong>.
            </div>
            """, unsafe_allow_html=True)

            st.write(f"**Data:** {registro['data_despesa']}")
            st.write(f"**Categoria:** {registro['categoria']}")
            st.write(f"**Valor:** R$ {float(registro['valor'] or 0):.2f}")

            confirmar = st.checkbox("Confirmo que desejo excluir esta despesa permanentemente.")

            if st.button("Excluir despesa selecionada", type="primary", use_container_width=True):
                if not confirmar:
                    st.warning("Confirme a exclusão antes de continuar.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM despesas_veiculo WHERE id = ?", (despesa_id,))
                    conn.commit()
                    st.success("Despesa excluída com sucesso.")
                    st.rerun()

    conn.close()