import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st


DB = "estoque.db"


# =========================
# BANCO DE DADOS
# =========================

def conectar():
    return sqlite3.connect(DB)


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            categoria TEXT,
            quantidade INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 0,
            preco REAL NOT NULL DEFAULT 0,
            fornecedor TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            data TEXT NOT NULL,
            observacao TEXT,
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)

    conn.commit()
    conn.close()


# =========================
# PRODUTOS
# =========================

def cadastrar_produto(codigo, nome, categoria, quantidade,
                      estoque_minimo, preco, fornecedor):

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO produtos
            (codigo, nome, categoria, quantidade, estoque_minimo,
             preco, fornecedor, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            nome,
            categoria,
            quantidade,
            estoque_minimo,
            preco,
            fornecedor,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        produto_id = cursor.lastrowid

        if quantidade > 0:
            cursor.execute("""
                INSERT INTO movimentacoes
                (produto_id, tipo, quantidade, data, observacao)
                VALUES (?, ?, ?, ?, ?)
            """, (
                produto_id,
                "ENTRADA",
                quantidade,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Estoque inicial"
            ))

        conn.commit()
        return True, "Produto cadastrado com sucesso."

    except sqlite3.IntegrityError:
        return False, "Já existe um produto com esse código."

    finally:
        conn.close()


def listar_produtos():
    conn = conectar()

    df = pd.read_sql_query("""
        SELECT
            id,
            codigo,
            nome,
            categoria,
            quantidade,
            estoque_minimo,
            preco,
            fornecedor
        FROM produtos
        ORDER BY nome
    """, conn)

    conn.close()

    return df


def obter_produto(produto_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            codigo,
            nome,
            categoria,
            quantidade,
            estoque_minimo,
            preco,
            fornecedor
        FROM produtos
        WHERE id = ?
    """, (produto_id,))

    produto = cursor.fetchone()

    conn.close()

    return produto


def atualizar_produto(produto_id, codigo, nome, categoria,
                      estoque_minimo, preco, fornecedor):

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE produtos
            SET codigo = ?,
                nome = ?,
                categoria = ?,
                estoque_minimo = ?,
                preco = ?,
                fornecedor = ?
            WHERE id = ?
        """, (
            codigo,
            nome,
            categoria,
            estoque_minimo,
            preco,
            fornecedor,
            produto_id
        ))

        conn.commit()

        return True, "Produto atualizado."

    except sqlite3.IntegrityError:
        return False, "Esse código já está sendo usado."

    finally:
        conn.close()


def excluir_produto(produto_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM movimentacoes
        WHERE produto_id = ?
    """, (produto_id,))

    cursor.execute("""
        DELETE FROM produtos
        WHERE id = ?
    """, (produto_id,))

    conn.commit()
    conn.close()


# =========================
# MOVIMENTAÇÕES
# =========================

def movimentar_estoque(produto_id, tipo, quantidade, observacao):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT quantidade
        FROM produtos
        WHERE id = ?
    """, (produto_id,))

    resultado = cursor.fetchone()

    if not resultado:
        conn.close()
        return False, "Produto não encontrado."

    estoque_atual = resultado[0]

    if tipo == "ENTRADA":
        novo_estoque = estoque_atual + quantidade

    else:
        if quantidade > estoque_atual:
            conn.close()
            return False, "Quantidade de saída maior que o estoque."

        novo_estoque = estoque_atual - quantidade

    cursor.execute("""
        UPDATE produtos
        SET quantidade = ?
        WHERE id = ?
    """, (novo_estoque, produto_id))

    cursor.execute("""
        INSERT INTO movimentacoes
        (produto_id, tipo, quantidade, data, observacao)
        VALUES (?, ?, ?, ?, ?)
    """, (
        produto_id,
        tipo,
        quantidade,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        observacao
    ))

    conn.commit()
    conn.close()

    return True, "Movimentação realizada."


def listar_movimentacoes():
    conn = conectar()

    df = pd.read_sql_query("""
        SELECT
            m.id,
            p.codigo,
            p.nome,
            m.tipo,
            m.quantidade,
            m.data,
            m.observacao
        FROM movimentacoes m
        INNER JOIN produtos p
            ON p.id = m.produto_id
        ORDER BY m.id DESC
    """, conn)

    conn.close()

    return df


# =========================
# CONFIGURAÇÃO
# =========================

st.set_page_config(
    page_title="Sistema de Estoque",
    page_icon="📦",
    layout="wide"
)

criar_tabelas()


# =========================
# MENU
# =========================

st.sidebar.title("📦 Estoque")

pagina = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Produtos",
        "Cadastrar produto",
        "Movimentação",
        "Histórico"
    ]
)


# =========================
# DASHBOARD
# =========================

if pagina == "Dashboard":

    st.title("📊 Dashboard")

    df = listar_produtos()

    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:

        total_produtos = len(df)
        quantidade_total = int(df["quantidade"].sum())

        valor_estoque = (
            df["quantidade"] * df["preco"]
        ).sum()

        estoque_baixo = len(
            df[df["quantidade"] <= df["estoque_minimo"]]
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Produtos",
            total_produtos
        )

        col2.metric(
            "Itens em estoque",
            quantidade_total
        )

        col3.metric(
            "Valor do estoque",
            f"R$ {valor_estoque:,.2f}"
        )

        col4.metric(
            "Estoque baixo",
            estoque_baixo
        )

        st.divider()

        st.subheader("Produtos com estoque baixo")

        baixos = df[
            df["quantidade"] <= df["estoque_minimo"]
        ]

        if baixos.empty:
            st.success("Nenhum produto abaixo do estoque mínimo.")
        else:
            st.dataframe(
                baixos,
                use_container_width=True,
                hide_index=True
            )


# =========================
# PRODUTOS
# =========================

elif pagina == "Produtos":

    st.title("📦 Produtos")

    df = listar_produtos()

    if df.empty:
        st.info("Nenhum produto cadastrado.")

    else:

        busca = st.text_input(
            "🔎 Buscar produto",
            placeholder="Nome, código ou categoria..."
        )

        if busca:

            termo = busca.lower()

            df = df[
                df["nome"].str.lower().str.contains(
                    termo,
                    na=False
                )
                |
                df["codigo"].str.lower().str.contains(
                    termo,
                    na=False
                )
                |
                df["categoria"].fillna("").str.lower().str.contains(
                    termo,
                    na=False
                )
            ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "preco": st.column_config.NumberColumn(
                    "Preço",
                    format="R$ %.2f"
                )
            }
        )

        st.divider()

        st.subheader("Editar produto")

        produto_id = st.number_input(
            "ID do produto",
            min_value=1,
            step=1
        )

        produto = obter_produto(produto_id)

        if produto:

            (
                id_,
                codigo,
                nome,
                categoria,
                quantidade,
                estoque_minimo,
                preco,
                fornecedor
            ) = produto

            with st.form("editar_produto"):

                novo_codigo = st.text_input(
                    "Código",
                    value=codigo
                )

                novo_nome = st.text_input(
                    "Nome",
                    value=nome
                )

                nova_categoria = st.text_input(
                    "Categoria",
                    value=categoria or ""
                )

                novo_minimo = st.number_input(
                    "Estoque mínimo",
                    min_value=0,
                    value=estoque_minimo
                )

                novo_preco = st.number_input(
                    "Preço",
                    min_value=0.0,
                    value=float(preco),
                    step=0.01
                )

                novo_fornecedor = st.text_input(
                    "Fornecedor",
                    value=fornecedor or ""
                )

                salvar = st.form_submit_button(
                    "Salvar alterações"
                )

                if salvar:

                    sucesso, mensagem = atualizar_produto(
                        id_,
                        novo_codigo,
                        novo_nome,
                        nova_categoria,
                        novo_minimo,
                        novo_preco,
                        novo_fornecedor
                    )

                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)


# =========================
# CADASTRAR
# =========================

elif pagina == "Cadastrar produto":

    st.title("➕ Cadastrar produto")

    with st.form("cadastro"):

        codigo = st.text_input(
            "Código / SKU",
            placeholder="Ex: PROD001"
        )

        nome = st.text_input(
            "Nome do produto"
        )

        categoria = st.text_input(
            "Categoria",
            placeholder="Ex: Informática"
        )

        quantidade = st.number_input(
            "Quantidade inicial",
            min_value=0,
            step=1
        )

        estoque_minimo = st.number_input(
            "Estoque mínimo",
            min_value=0,
            step=1
        )

        preco = st.number_input(
            "Preço unitário",
            min_value=0.0,
            step=0.01
        )

        fornecedor = st.text_input(
            "Fornecedor"
        )

        cadastrar = st.form_submit_button(
            "Cadastrar produto"
        )

        if cadastrar:

            if not codigo or not nome:
                st.error(
                    "Código e nome são obrigatórios."
                )

            else:

                sucesso, mensagem = cadastrar_produto(
                    codigo,
                    nome,
                    categoria,
                    quantidade,
                    estoque_minimo,
                    preco,
                    fornecedor
                )

                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)


# =========================
# MOVIMENTAÇÃO
# =========================

elif pagina == "Movimentação":

    st.title("🔄 Movimentação de estoque")

    df = listar_produtos()

    if df.empty:

        st.info(
            "Cadastre pelo menos um produto primeiro."
        )

    else:

        produtos = {
            f"{row['codigo']} - {row['nome']} "
            f"(estoque: {row['quantidade']})":
            row["id"]
            for _, row in df.iterrows()
        }

        produto_selecionado = st.selectbox(
            "Produto",
            list(produtos.keys())
        )

        produto_id = produtos[produto_selecionado]

        tipo = st.radio(
            "Tipo",
            ["ENTRADA", "SAÍDA"],
            horizontal=True
        )

        quantidade = st.number_input(
            "Quantidade",
            min_value=1,
            step=1
        )

        observacao = st.text_input(
            "Observação",
            placeholder="Ex: Compra, venda, devolução..."
        )

        if st.button(
            "Registrar movimentação",
            type="primary"
        ):

            sucesso, mensagem = movimentar_estoque(
                produto_id,
                tipo,
                quantidade,
                observacao
            )

            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)


# =========================
# HISTÓRICO
# =========================

elif pagina == "Histórico":

    st.title("📋 Histórico de movimentações")

    df = listar_movimentacoes()

    if df.empty:

        st.info(
            "Nenhuma movimentação registrada."
        )

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
