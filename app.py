import streamlit as st
import pandas as pd
import requests
import tempfile
import tabula

st.set_page_config(page_title="Extrator de Atas", layout="wide")

st.title("📄 Extrator de Dados de PDF – Licitações")

# Input do usuário
pdf_url = st.text_input("Cole aqui o link do PDF:")

if pdf_url:
    st.info("Baixando e processando o PDF...")

    try:
        # --- Baixar PDF temporário ---
        response = requests.get(pdf_url)
        if response.status_code != 200:
            st.error("Erro ao baixar o PDF. Verifique o link.")
            st.stop()

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(response.content)
        temp_file.close()

        # --- Ler tabelas ---
        st.info("Extraindo tabelas do PDF...")

        tables = tabula.read_pdf(temp_file.name, pages="all", multiple_tables=True)

        if not tables:
            st.error("Nenhuma tabela foi encontrada no PDF.")
            st.stop()

        # --- Unificar tabelas ---
        df = pd.concat(tables, ignore_index=True)

        # Limpeza básica
        df.columns = df.columns.map(str)
        df = df.dropna(how="all")

        st.success("Processamento concluído!")

        st.subheader("📊 Tabela Completa")
        st.dataframe(df, use_container_width=True)

        # ----------------------------
        # FILTROS
        # ----------------------------

        st.subheader("🔍 Filtros")

        # Campo para filtrar por item
        item_filtro = st.text_input("Filtrar por item (código, descrição, processo etc.):")

        # Criar dropdown de Centro de Custo (detecta automaticamente)
        col_centro_custo = None
        for c in df.columns:
            if "centro" in c.lower() or "custo" in c.lower():
                col_centro_custo = c
                break

        if col_centro_custo:
            centros = ["Todos"] + sorted(df[col_centro_custo].dropna().astype(str).unique().tolist())
            centro_escolhido = st.selectbox("Centro de Custo:", centros)
        else:
            st.warning("Nenhuma coluna de Centro de Custo foi detectada automaticamente.")
            centros = []
            centro_escolhido = "Todos"

        # Aplicação dos filtros
        df_filtrado = df.copy()

        # Filtro por item
        if item_filtro.strip():
            df_filtrado = df_filtrado[
                df_filtrado.apply(
                    lambda row: row.astype(str).str.contains(item_filtro, case=False, na=False).any(), axis=1
                )
            ]

        # Filtro por centro de custo
        if col_centro_custo and centro_escolhido != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_centro_custo].astype(str) == centro_escolhido]

        st.subheader("📌 Resultado Filtrado")
        st.dataframe(df_filtrado, use_container_width=True)

        # Botão para baixar CSV
        st.download_button(
            "⬇ Baixar CSV filtrado",
            df_filtrado.to_csv(index=False).encode("utf-8"),
            "resultado_filtrado.csv",
            "text/csv"
        )

    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
