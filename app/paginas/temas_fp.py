import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, fp, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Temas técnicos")
st.caption("Temas da taxonomia das Florestas Plantadas (cadeia silvicultural), cada um ligado a uma linha do "
           f"Centro · {a0}–{a1}")

tax = fp.taxonomia()
temas = tax[(tax.faceta == "tema") & (tax.nivel.astype(str) != "0")][["no_id", "rotulo_pt", "linha", "descricao_pt"]]
b = q("""select t.doc_uid, t.tema, d.tipo_doc, d.ano, d.unidade_id from fp_doc_tema_fp t
         join documento d using (doc_uid) where d.ano between ? and ?""", (a0, a1))
b = b.merge(temas, left_on="tema", right_on="no_id")
b["linha_rot"] = b.linha.map(fp.rotulo_linha_curto)

s = b.groupby(["rotulo_pt", "linha_rot", "tipo_doc"]).doc_uid.nunique().reset_index(name="n")
s["tipo"] = s.tipo_doc.map(dados.TIPOS)
ordem = s.groupby("rotulo_pt").n.sum().sort_values(ascending=False).index.tolist()
fig = px.bar(s, y="rotulo_pt", x="n", color="tipo", orientation="h", category_orders={"rotulo_pt": ordem},
             color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
             hover_data={"linha_rot": True}, height=520,
             labels={"n": "Documentos", "rotulo_pt": "", "tipo": "", "linha_rot": "Linha do Centro"})
st.plotly_chart(fig, width="stretch")
st.caption("Os temas vêm da classificação das Florestas Plantadas (protótipos SBERT + termos; nos documentos "
           "da amostra e nos projetos, rótulos revisados). Um documento pode ter mais de um tema.")

sel = st.selectbox("Escolha um tema para ver o detalhe", ordem, index=None, placeholder="Tema técnico")
if sel:
    info = temas.set_index("rotulo_pt").loc[sel]
    sub = b[b.rotulo_pt == sel]
    st.subheader(sel)
    st.caption(f"Linha do Centro: **{fp.rotulo_linha_curto(info.linha)}**"
               + (f" · {info.descricao_pt}" if isinstance(info.descricao_pt, str) else ""))
    cont = sub.drop_duplicates("doc_uid").tipo_doc.value_counts()
    ui.kpis([("Projetos", int(cont.get("projeto", 0))), ("Publicações", int(cont.get("publicacao", 0))),
             ("Soluções tecnológicas", int(cont.get("tecnologia", 0))),
             ("Unidades", int(sub.unidade_id.nunique()))])
    t1, t2, t3 = st.tabs(["Evolução", "Unidades", "Documentos"])
    with t1:
        e = sub.drop_duplicates("doc_uid").groupby(["ano", "tipo_doc"]).size().reset_index(name="n")
        e["tipo"] = e.tipo_doc.map(dados.TIPOS)
        st.plotly_chart(px.bar(e, x="ano", y="n", color="tipo",
                               color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                               labels={"ano": "Ano", "n": "Documentos", "tipo": ""}), width="stretch")
    with t2:
        u = sub.drop_duplicates("doc_uid").groupby("unidade_id").size().reset_index(name="n")
        u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(u.sort_values("n", ascending=False)[["unidade_id", "unidade", "n"]], "unidade",
                            "unidade_id", "tfp_unid", altura=360, colunas={"unidade": "Unidade", "n": "Documentos"})
    with t3:
        ids = tuple(sub.doc_uid.unique())
        docs = q("select doc_uid, tipo_doc, ano, titulo, unidade_id from documento where list_contains(?, doc_uid) "
                 "order by ano desc", (list(ids),))
        docs["tipo_doc"] = docs.tipo_doc.map(dados.TIPOS)
        docs["unidade"] = docs.unidade_id.map(dados.rotulo_unidade)
        ui.tabela_navegavel(docs[["doc_uid", "tipo_doc", "ano", "titulo", "unidade"]], "doc", "doc_uid", "tfp_docs",
                            altura=420, colunas={"tipo_doc": "Tipo", "ano": "Ano", "titulo": "Título",
                                                 "unidade": "Unidade"})
