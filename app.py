import streamlit as st
import pandas as pd
import requests
import tempfile
import camelot
import re

st.set_page_config(page_title="Extrator Inteligente de PDF", layout="wide")

st.title("🤖 Extrator Inteligente de PDF – Licitações")

# Função inteligente para identificar colunas
def identificar_colunas(df):

    mapeamento = {}

    for col in df.columns:
        serie = df[col].astype(str)

        # ---- Código do item ----
        if serie.str.contains(r"\b\d{3}\.\d{3}\.\d{3}\b").any():
            mapeamento[col] = "codigo"
            continue

        # ---- Centro de Custo ----
        if serie.str.contains(r"CENTRO DE CUSTO|CC\s*\d+", case=False, na=False).any():
            mapeamento[col] = "centro_custo"
            continue

        # ---- Unidade ----
        if serie.str.contains(r"\b(UN|UND|CX|PÇ|PC|KIT)\b", na=False).any():
            mapeamento[col] = "unidade"
            continue

        # ---- Quantidade (números puros) ----
        if serie.str.match(r"^\d+$").sum() > len(serie) * 0.5:
            mapeamento[col] = "quantidade"
            continue

        # ---- Valores (com vírgula) ----
        if serie.str.contains(r"\d+,\d{2}", na=False).any():
            if serie.str.count(",").sum() > 5:
                # provavel valor unit
                mapeamento[col] = "valor_unitario"
            else:
                mapeamento[col] = "valor_total"
            continue

        # ---- Descrição (coluna longa) ----
        if serie.str.len().mean() > 20:
            mapeamento[col] = "descricao"
            continue

        # Caso não identifique:
        mapeamento[col] = f"col_{col}"

    return mapeamento


pdf_url = st.text_input("Cole o link do PDF:")

if pdf_url:
    st.info("Baixando o PDF...")

    try:
        response = requests.get(pdf_url)
        if response.status_code != 200:
            st.error("Erro ao baixar PDF.")
            st.stop()

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(response.content)
        temp_file.close()

        # Extrair tabelas
        tables = camelot.read_pdf(temp_file.name, pages="all", flavor="stream")

        if tables.n == 0:
            st.error("Nenhuma tabela encontrada no PDF.")
            st.stop()

        dfs = []

        for table in tables:
            df_raw = table.df
            df_raw = df_raw.dropna(how="all")
            df_clean = df_raw.iloc[1:].reset_index(drop=True)

            # Nomear colunas genericas
            df_clean.columns = [f"col_{i}" for i in range(df_clean.shape[1])]
            dfs.append(df_clean)

        df = pd.concat(dfs, ignore_index=True)

        # -------------------------------------------------------
        # 🔥 AQUI A MAGIA ACONTECE: DETECÇÃO AUTOMÁTICA
        # -------------------------------------------------------
        mapeamento = identificar_colunas(df)
        df = df.rename(columns=mapeamento)

        st.success("PDF processado com sucesso!")

        st.subheader("📊 Tabela Interpretada (com colunas reconhecidas automaticamente)")
        st.dataframe(df, use_container_width=True)

        # -------------------------------------------------------
        # FILTROS
        # -------------------------------------------------------

        st.subheader("🔍 Filtros Inteligentes")

        # Filtro item
        item = st.text_input("Buscar item (código, nome, descrição, etc.):")

        # Filtro centro de custo
        if "centro_custo" in df.columns:
            ccs = ["Todos"] + sorted(df["centro_custo"].dropna().unique().tolist())
            cc_filtro = st.selectbox("Centro de Custo:", ccs)
        else:
            cc_filtro = "Todos"

        df_filtrado = df.copy()

        # Aplicar filtro item
        if item.strip():
            df_filtrado = df_filtrado[
                df_filtrado.apply(lambda row: row.astype(str).str.contains(item, case=False, na=False).any(), axis=1)
            ]

        # Aplicar filtro CC
        if cc_filtro != "Todos" and "centro_custo" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["centro_custo"].astype(str) == cc_filtro]

        st.subheader("📌 Resultado Filtrado")
        st.dataframe(df_filtrado, use_container_width=True)

        # Download final
        st.download_button(
            "⬇ Baixar CSV filtrado",
            df_filtrado.to_csv(index=False).encode("utf-8"),
            "resultado_filtrado.csv",
            "text/csv"
        )

    except Exception as e:
        st.error(f"Erro ao processar PDF: {e}")
