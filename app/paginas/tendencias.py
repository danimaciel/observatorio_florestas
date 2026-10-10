import pandas as pd
import plotly.express as px
import streamlit as st

from lib import dados, fp
from lib.dados import q

st.title("Tendências: o que cresce e o que cai")
st.caption("Compara dois períodos de mesmo tamanho. A participação (% do total de cada período) desconta o "
           "crescimento geral da produção; a variação absoluta mostra o volume.")

amin, amax = dados.faixa_anos()
c1, c2, c3 = st.columns(3)
fim = c1.number_input("Último ano do período recente", min_value=amin + 10, max_value=amax, value=min(2025, amax),
                      help="Os anos mais recentes ficam incompletos: publicações demoram a ser depositadas.")
jan = c2.selectbox("Tamanho de cada período", [3, 5, 8, 10], index=1, format_func=lambda n: f"{n} anos")
tipos = c3.multiselect("Tipos de documento", list(dados.TIPOS), default=list(dados.TIPOS),
                       format_func=dados.TIPOS.get)
r1, r0 = (fim - jan + 1, fim), (fim - 2 * jan + 1, fim - jan)
st.markdown(f"**Período anterior:** {r0[0]}–{r0[1]} · **Período recente:** {r1[0]}–{r1[1]}")

d = fp.docs_facetas(r0[0], r1[1])
d = d[d.tipo_doc.isin(tipos)]
d["periodo"] = (d.ano >= r1[0]).map({True: "recente", False: "anterior"})


def explode(col, sep="+"):
    x = d[["doc_uid", "periodo", col]].dropna()
    x = x.assign(**{col: x[col].str.split(sep)}).explode(col)
    return x[x[col].astype(bool)]


DIM = {
    "Linha do Centro": lambda: explode("linhas").rename(columns={"linhas": "item"}).assign(
        item=lambda x: x.item.map(fp.rotulo_linha_curto)),
    "Espécie": lambda: d[d.esp_no.notna() & (d.esp_no != "ESP.MUL")][["doc_uid", "periodo", "esp_no"]].rename(
        columns={"esp_no": "item"}).assign(item=lambda x: x.item.map(fp.rotulo)),
    "Tema técnico": lambda: explode("temas").rename(columns={"temas": "item"}).assign(
        item=lambda x: ("TEM." + x.item).map(fp.rotulo)),
    "Sistema": lambda: d[["doc_uid", "periodo", "sis_final"]].rename(columns={"sis_final": "item"}).assign(
        item=lambda x: x.item.map(fp.SISTEMAS)),
    "Unidade": lambda: d[["doc_uid", "periodo", "unidade_id"]].dropna().rename(columns={"unidade_id": "item"}).assign(
        item=lambda x: x.item.map(dados.rotulo_unidade)),
}
dim = st.radio("Olhar por", list(DIM), horizontal=True)
x = DIM[dim]().drop_duplicates()
tot = d.groupby("periodo").doc_uid.nunique()
if tot.get("anterior", 0) == 0 or tot.get("recente", 0) == 0:
    st.info("Sem documentos em um dos períodos com os filtros atuais.")
    st.stop()
t = x.groupby(["item", "periodo"]).doc_uid.nunique().unstack(fill_value=0).reindex(columns=["anterior", "recente"],
                                                                                     fill_value=0)
t["var_abs"] = t.recente - t.anterior
t["var_pct"] = (100 * t.var_abs / t.anterior).where(t.anterior >= 5)
t["part_ant"] = 100 * t.anterior / tot["anterior"]
t["part_rec"] = 100 * t.recente / tot["recente"]
t["var_part"] = t.part_rec - t.part_ant
minimo = st.slider("Mínimo de documentos (somando os dois períodos)", 0, 100, 10)
t = t[(t.anterior + t.recente) >= minimo].sort_values("var_part")

st.markdown(f"Total de documentos: **{tot['anterior']:,}** no anterior e **{tot['recente']:,}** no recente."
            .replace(",", "."))
fig = px.bar(t.reset_index(), x="var_part", y="item", orientation="h",
             color=t.var_part.gt(0).map({True: "ganha espaço", False: "perde espaço"}).values,
             color_discrete_map={"ganha espaço": fp.COR["verde"], "perde espaço": fp.COR["ambar"]},
             labels={"var_part": "Variação da participação (pontos percentuais)", "item": "", "color": ""},
             height=max(360, 26 * len(t) + 120),
             hover_data={"anterior": True, "recente": True})
st.plotly_chart(fig, width="stretch")

st.dataframe(
    t.sort_values("var_part", ascending=False).rename(columns={
        "anterior": f"{r0[0]}–{r0[1]}", "recente": f"{r1[0]}–{r1[1]}", "var_abs": "Variação (docs)",
        "var_pct": "Variação (%)", "part_ant": "% anterior", "part_rec": "% recente", "var_part": "Δ participação (p.p.)"}),
    width="stretch",
    column_config={c: st.column_config.NumberColumn(format="%.1f")
                   for c in ["Variação (%)", "% anterior", "% recente", "Δ participação (p.p.)"]})
st.caption("Variação (%) só é calculada com pelo menos 5 documentos no período anterior. "
           "Um documento conta uma vez em cada item a que pertence.")

if "projeto" in tipos:
    st.subheader("Projetos em execução por linha")
    p = q("""select l.linha, d.ano, d.ano_fim from fp_doc_linha l join documento d using (doc_uid)
             where d.tipo_doc = 'projeto'""")
    anos = list(range(max(amin, fim - 15), amax + 1))
    linhas_ano = [(a, r.linha) for r in p.itertuples() for a in anos
                  if r.ano <= a <= (r.ano_fim if pd.notna(r.ano_fim) else r.ano)]
    if linhas_ano:
        s = pd.DataFrame(linhas_ano, columns=["ano", "linha"]).value_counts().reset_index(name="n")
        s["linha"] = s.linha.map(fp.rotulo_linha_curto)
        fig = px.line(s.sort_values("ano"), x="ano", y="n", color="linha", markers=True,
                      color_discrete_sequence=fp.CORES_LINHA, labels={"ano": "Ano", "n": "Projetos ativos", "linha": ""})
        fig.update_layout(legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
        st.caption("Projeto ativo = entre o ano de início e o de término. A base de projetos depende do que cada "
                   "unidade divulga e pode estar incompleta.")
