import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, fp

a0, a1 = dados.periodo()
st.title("Lacunas")
st.caption(f"Onde há pouco conhecimento, ou conhecimento que ainda não virou entrega · {a0}–{a1}")
st.info("Lacuna aqui é **pouca produção registrada** num cruzamento, não necessariamente falta de pesquisa: "
        "parte da produção pode não estar no repositório, e alguns cruzamentos simplesmente não fazem sentido "
        "(ex.: erva-mate em clima semiárido). Use como ponto de partida para a discussão.",
        icon=":material/lightbulb:")

d = fp.docs_facetas(a0, a1)


def explode(df, col):
    x = df.dropna(subset=[col])
    x = x.assign(**{col: x[col].str.split("+")}).explode(col)
    return x[x[col].astype(bool)]


esp = d.assign(especie=d.esp_no.map(fp.rotulo).where(d.esp_no.notna() & (d.esp_no != "ESP.MUL")))
el = explode(esp, "linhas")
el["linha"] = el.linhas.map(fp.rotulo_linha_curto)

t1, t2, t3 = st.tabs(["Espécie × linha", "Clima × linha", "Pesquisa × entrega"])

with t1:
    n_esp = st.slider("Espécies (as com mais documentos)", 5, 30, 15)
    top = esp.especie.value_counts().head(n_esp).index
    m = el[el.especie.isin(top)].groupby(["especie", "linha"]).doc_uid.nunique().unstack(fill_value=0)
    m = m.reindex(index=top)
    fig = px.imshow(m, text_auto=True, aspect="auto", color_continuous_scale=["#F3F1E8", "#3F9A5C", "#0D3B2A"],
                    labels={"color": "Documentos", "x": "", "y": ""}, height=200 + 30 * len(m))
    fig.update_xaxes(side="top")
    st.plotly_chart(fig, width="stretch")
    st.caption("Células claras = poucos documentos daquela espécie naquela linha. Ex.: espécies com muito "
               "melhoramento e pouca sanidade, ou sem nada em carbono.")

with t2:
    kg = explode(d, "kg")
    kl = explode(kg, "linhas")
    kl["linha"] = kl.linhas.map(fp.rotulo_linha_curto)
    m = kl.groupby(["kg", "linha"]).doc_uid.nunique().unstack(fill_value=0)
    m.index = [fp.KG.get(k, k) for k in m.index]
    fig = px.imshow(m, text_auto=True, aspect="auto", color_continuous_scale=["#F3F1E8", "#2F6F9F", "#0D3B2A"],
                    labels={"color": "Documentos", "x": "", "y": ""}, height=200 + 34 * len(m))
    fig.update_xaxes(side="top")
    st.plotly_chart(fig, width="stretch")
    st.caption("Clima (Köppen) do lugar onde o conhecimento foi gerado: município citado no texto ou sede da "
               "unidade. Climas com pouco conhecimento importam para os países-alvo com esse clima "
               "(veja a página **Países**).")

with t3:
    st.markdown("**Quanto da pesquisa já virou solução tecnológica?** Por linha e por espécie, "
                "publicações e projetos comparados com soluções tecnológicas.")
    por = st.radio("Por", ["Linha do Centro", "Espécie"], horizontal=True)
    base = el if por == "Linha do Centro" else esp.dropna(subset=["especie"])
    col = "linha" if por == "Linha do Centro" else "especie"
    t = base.groupby([col, "tipo_doc"]).doc_uid.nunique().unstack(fill_value=0)
    for c in dados.TIPOS:
        if c not in t:
            t[c] = 0
    t = t[(t.publicacao + t.projeto) >= 10]
    t["publicações por solução"] = (t.publicacao / t.tecnologia.where(t.tecnologia > 0)).round(1)
    t = t.sort_values(["tecnologia", "publicacao"], ascending=[True, False])
    fig = px.scatter(t.reset_index(), x="publicacao", y="tecnologia", size="projeto", text=col,
                     labels={"publicacao": "Publicações", "tecnologia": "Soluções tecnológicas", "projeto": "Projetos"},
                     color_discrete_sequence=[fp.COR["verde"]], height=520, size_max=40)
    fig.update_traces(textposition="top center", textfont_size=10)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(t.rename(columns=dados.TIPOS), width="stretch")
    st.caption("Muita publicação e nenhuma solução pode indicar conhecimento ainda não transformado em entrega "
               "para o produtor — ou soluções que não estão no portal. O tamanho do ponto é o número de projetos.")
