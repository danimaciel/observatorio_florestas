import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, fp
from lib.dados import q

LIMIAR = 0.10   # clima "igual": a classe de Köppen ocupa >= 10% do território do país (proposta a validar)
LUSOFONOS = ["MOZ", "AGO", "GNB", "STP", "GNQ", "CPV"]

a0, a1 = dados.periodo()
st.title("Países")
st.caption("Correspondência entre o conhecimento da Embrapa e os países africanos, por clima (Köppen-Geiger, "
           "Beck et al., 2018) e por espécie presente (Agroforestree Database, ICRAF)")

pk = q("select * from fp_pais_kg")
ep = q("select * from fp_especie_pais")
kg_doc = q("""select k.doc_uid, k.kg, d.tipo_doc from fp_doc_kg k join documento d using (doc_uid)
              where d.ano between ? and ?""", (a0, a1))

# visão geral: documentos de clima igual em cada país
igual = pk[pk.frac >= LIMIAR]
ger = igual.merge(kg_doc, on="kg").groupby(["iso3", "nome_pt"]).doc_uid.nunique().reset_index(name="docs")
ger = ger.merge(ep.groupby("iso3").especies.nunique().reset_index(name="especies"), on="iso3", how="left")
paises = pk.drop_duplicates("iso3")[["iso3", "nome_pt"]]
ger = paises.merge(ger, on=["iso3", "nome_pt"], how="left").fillna({"docs": 0, "especies": 0})

t1, t2 = st.tabs(["Um país", "Todos os países"])
with t2:
    fig = px.choropleth(ger, locations="iso3", color="docs", hover_name="nome_pt", scope="africa",
                        color_continuous_scale=["#F3F1E8", "#3F9A5C", "#0D3B2A"],
                        labels={"docs": "Documentos de clima igual"}, height=560)
    fig.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(ger.sort_values("docs", ascending=False).rename(columns={
        "nome_pt": "País", "docs": "Documentos de clima igual", "especies": "Espécies da taxonomia plantadas no país"}),
        width="stretch", hide_index=True)
    st.caption(f"Clima igual: a classe de Köppen de onde o documento foi gerado ocupa ao menos {LIMIAR:.0%} do "
               "território do país (limiar a validar com o grupo). Países sem nenhuma classe presente no Brasil "
               "(ex.: Cabo Verde, deserto quente) ficam com zero.")

with t1:
    ordem = LUSOFONOS + sorted(set(paises.iso3) - set(LUSOFONOS), key=lambda i: paises.set_index("iso3").nome_pt[i])
    iso = st.selectbox("País", ordem, format_func=lambda i: paises.set_index("iso3").nome_pt[i])
    cl = pk[pk.iso3 == iso].sort_values("frac", ascending=False)
    st.markdown("**Climas do território:** " + " · ".join(
        f"{fp.KG.get(r.kg, r.kg)} {r.frac:.0%}" for r in cl.itertuples() if r.frac >= 0.05))
    esp = sorted(ep[ep.iso3 == iso].especies)
    st.markdown("**Espécies da taxonomia plantadas no país (Agroforestree):** " +
                (", ".join(f"*{e}*" for e in esp) if esp else "nenhuma registrada"))
    ks = cl[cl.frac >= LIMIAR].kg.tolist()
    if not ks:
        st.warning("Nenhum clima do país ocupa 10% ou mais do território com correspondência no Brasil.")
        st.stop()
    ids = tuple(kg_doc[kg_doc.kg.isin(ks)].doc_uid.unique())
    st.metric("Documentos gerados em clima igual", f"{len(ids):,}".replace(",", "."))
    d = fp.docs_facetas(a0, a1)
    d = d[d.doc_uid.isin(ids)]
    c1, c2 = st.columns(2)
    with c1:
        x = d.dropna(subset=["linhas"]).assign(linha=lambda z: z.linhas.str.split("+")).explode("linha")
        s = x.groupby("linha").doc_uid.nunique().reset_index(name="n")
        s["linha"] = s.linha.map(fp.rotulo_linha_curto)
        st.plotly_chart(px.bar(s.sort_values("n"), x="n", y="linha", orientation="h",
                               color_discrete_sequence=[fp.COR["verde"]],
                               labels={"n": "Documentos", "linha": ""}, title="Por linha do Centro"), width="stretch")
    with c2:
        u = d.groupby("unidade_id").doc_uid.nunique().nlargest(12).reset_index(name="n")
        u["unidade"] = u.unidade_id.map(dados.rotulo_unidade)
        st.plotly_chart(px.bar(u.sort_values("n"), x="n", y="unidade", orientation="h",
                               color_discrete_sequence=[fp.COR["azul"]],
                               labels={"n": "Documentos", "unidade": ""}, title="Unidades que mais produziram"),
                        width="stretch")
    st.markdown("**Soluções tecnológicas e projetos gerados em clima igual**")
    sol = d[d.tipo_doc.isin(["tecnologia", "projeto"])][["tipo_doc", "ano", "titulo", "unidade_id"]].copy()
    sol["tipo_doc"] = sol.tipo_doc.map(dados.TIPOS)
    sol["unidade_id"] = sol.unidade_id.map(dados.rotulo_unidade)
    st.dataframe(sol.sort_values("ano", ascending=False).rename(columns={
        "tipo_doc": "Tipo", "ano": "Ano", "titulo": "Título", "unidade_id": "Unidade"}),
        width="stretch", hide_index=True, height=360)
