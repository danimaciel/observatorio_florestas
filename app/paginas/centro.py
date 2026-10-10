import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, fp, ui
from lib.dados import q

a0, a1 = dados.periodo()
st.title("Florestas Plantadas na Embrapa")
st.caption(f"Visão do Centro de Referência da FAO em Florestas Plantadas e ILPF · {a0}–{a1}")

d = fp.docs_facetas(a0, a1)
pesq = q("""select count(distinct dp.pessoa_id) n from documento_pessoa dp join documento d using (doc_uid)
            where d.ano between ? and ?""", (a0, a1)).n[0]
n_un = d.unidade_id.nunique()
ui.kpis([
    ("Projetos", int((d.tipo_doc == "projeto").sum())),
    ("Publicações", int((d.tipo_doc == "publicacao").sum())),
    ("Soluções tecnológicas", int((d.tipo_doc == "tecnologia").sum())),
    ("Pesquisadores com produção", int(pesq)),
    ("Unidades envolvidas", int(n_un)),
])
st.caption("Recorte: documentos do acervo das Florestas Plantadas (núcleo e complementar) e projetos "
           "pré-rotulados. Use os filtros da barra lateral para olhar uma linha, coleção ou sistema.")

dl = fp.doc_linha(a0, a1)
t1, t2, t3, t4 = st.tabs(["Linhas do Centro", "Ao longo do tempo", "Espécies", "Sistemas"])

with t1:
    s = dl.groupby(["linha_rot", "tipo_doc"]).doc_uid.nunique().reset_index(name="n")
    s["tipo"] = s.tipo_doc.map(dados.TIPOS)
    ordem = s.groupby("linha_rot").n.sum().sort_values(ascending=False).index.tolist()
    fig = px.bar(s, y="linha_rot", x="n", color="tipo", orientation="h", category_orders={"linha_rot": ordem},
                 color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                 labels={"n": "Documentos", "linha_rot": "", "tipo": ""}, height=420)
    st.plotly_chart(fig, width="stretch")
    st.caption("Um documento pode estar em mais de uma linha. A linha vem dos temas técnicos do documento "
               "(ligação tema → linha proposta pela equipe, a validar) e do sistema (ILPF → Sistemas integrados).")
    tab = s.pivot_table(index="linha_rot", columns="tipo", values="n", fill_value=0).reindex(ordem)
    tab["Total (documentos únicos)"] = dl.groupby("linha_rot").doc_uid.nunique().reindex(ordem)
    st.dataframe(tab, width="stretch")

with t2:
    s = dl.groupby(["ano", "linha_rot"]).doc_uid.nunique().reset_index(name="n")
    fig = px.line(s, x="ano", y="n", color="linha_rot", markers=True, color_discrete_sequence=fp.CORES_LINHA,
                  labels={"ano": "Ano", "n": "Documentos", "linha_rot": ""})
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")
    st.caption("Projetos pelo ano de início. Os anos mais recentes ainda estão incompletos "
               "(publicações demoram a ser depositadas). Para o que cresce e o que cai, veja **Tendências**.")

with t3:
    s = d.assign(grupo=d.esp_grupo.map(fp.GRUPOS_ESP).fillna("Outras"))
    s = s.groupby(["grupo", "tipo_doc"]).size().reset_index(name="n")
    s["tipo"] = s.tipo_doc.map(dados.TIPOS)
    fig = px.bar(s, x="n", y="grupo", color="tipo", orientation="h",
                 color_discrete_map={dados.TIPOS[k]: v for k, v in dados.CORES_TIPO.items()},
                 labels={"n": "Documentos", "grupo": "", "tipo": ""}, height=360)
    st.plotly_chart(fig, width="stretch")
    e = d[d.esp_no.notna() & ~d.esp_no.isin(["ESP.MUL"])].copy()
    e["especie"] = e.esp_no.map(fp.rotulo)
    top = e.groupby(["especie", "tipo_doc"]).size().unstack(fill_value=0)
    top["total"] = top.sum(axis=1)
    top = top.sort_values("total", ascending=False).rename(columns=dados.TIPOS)
    st.markdown("**Espécie central de cada documento**")
    st.dataframe(top, width="stretch", height=420)

with t4:
    s = d.assign(sistema=d.sis_final.map(fp.SISTEMAS).fillna("Outro"),
                 nivel=d.nivel.map(fp.NIVEIS)).groupby(["sistema", "nivel"]).size().reset_index(name="n")
    fig = px.bar(s, x="sistema", y="n", color="nivel", barmode="stack",
                 color_discrete_sequence=[fp.COR["verde"], fp.COR["ambar"]],
                 labels={"n": "Documentos", "sistema": "", "nivel": ""})
    st.plotly_chart(fig, width="stretch")
    st.caption("Sistema florestal pela definição da FAO (FRA 2020/2025). A ILPF não é floresta para a FAO, mas "
               "faz parte do escopo do Centro, por isso está no núcleo, marcada à parte.")
