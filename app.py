import streamlit as st
import pandas as pd
import requests
import tempfile
import camelot

st.set_page_config(page_title="Extrator de PDF", layout="wide")

st.title("📄 Extrator de Dados de PDF – Licitações")

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

        # --- Extrair tabelas com Camelot ---
        st.info("Extraindo tabelas do PDF...")

        tables = camelot.read_pdf(temp_file.name, pages="all", flavor="stream")

        if tables.n == 0:
            st.error("Nenhuma tabela foi encontrada.")
            st.stop()

        # Unificar
        df_list = [t.df for t in tables]
        df = pd.concat(df_list, ignore_index=True)

        # Limpar (Camelot geralmente pega linha 0 como header errado)
        df.columns = df.iloc[0]
        df = df[1:]
        df = df.dropna(how="all")

        st.success("Processamento concluído!")

        st.subheader("📊 Tabela Completa")
        st.dataframe(df, use_container_width=True)

        # ----------------------------
        # FILTROS
        # ----------------------------

        st.subheader("🔍 Filtros")

        # Campo de busca
        item_filtro = st.text_input("Buscar por item / código / processo:")

        # Detectar automaticamente coluna de Centro de Custo
        col_cc = None
        for col in df.columns:
            if "centro" in str(col).lower() or "custo" in str(col).lower():
                col_cc = col
                break

        if col_cc:
            centros = ["Todos"] + sorted(df[col_cc].dropna().astype(str).unique().tolist())
            filtro_cc = st.selectbox("Centro de Custo:", centros)
        else:
            filtro_cc = "Todos"
            st.warning("Nenhuma coluna de Centro de Custo foi identificada.")

        df_filtrado = df.copy()

        # Aplicar filtro por texto
        if item_filtro.strip():
            df_filtrado = df_filtrado[
                df_filtrado.apply(
                    lambda row: row.astype(str).str.contains(item_filtro, case=False, na=False).any(),
                    axis=1,
                )
            ]

        # Aplicar filtro por centro de custo
        if col_cc and filtro_cc != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_cc].astype(str) == filtro_cc]

        st.subheader("📌 Resultado Filtrado")
        st.dataframe(df_filtrado, use_container_width=True)

        # Download
        st.download_button(
            "⬇ Baixar CSV filtrado",
            df_filtrado.to_csv(index=False).encode("utf-8"),
            "resultado_filtrado.csv",
            "text/csv",
        )

    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
