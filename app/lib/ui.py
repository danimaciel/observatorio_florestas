"""Componentes de interface compartilhados entre as páginas."""

import networkx as nx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

PAGINAS = {
    "embrapa": "paginas/embrapa.py",
    "unidade": "paginas/unidades.py",
    "redes": "paginas/redes.py",
    "temas": "paginas/temas.py",
    "pessoa": "paginas/pesquisadores.py",
    "doc": "paginas/documentos.py",
    "tema": "paginas/temas.py",
}
PALETA = ["#1F6B45", "#C8892A", "#2F6F9F", "#8A5A3B", "#3F9A5C", "#7A4E9C", "#5B6B61",
          "#B4502F", "#0D3B2A", "#D9B45A", "#6E8B3D", "#4A7C8C"]


def estilo_florestas() -> None:
    """Identidade visual iAgro Florestas (opção B do esboço): verde-floresta, areia e âmbar,
    títulos em serifa e barra lateral escura com copas de árvores."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
h1, h2, h3 { font-family: 'Source Serif 4', Cambria, Georgia, serif !important; color: #0D3B2A; letter-spacing: -0.01em; }
h1 { border-bottom: 3px solid #C8892A; padding-bottom: .35rem; display: inline-block; }
[data-testid="stSidebar"] { background: #0D3B2A; }
[data-testid="stSidebar"] * { color: #E8EFE9; }
[data-testid="stSidebar"] [data-baseweb="select"] *, [data-testid="stSidebar"] input { color: #17251D !important; }
[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] { border-color: #2C5A45; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #1F6B45; border-radius: 6px; }
[data-testid="stSidebar"]::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 46px;
  pointer-events: none; opacity: .35; z-index: 0;
  background: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 70' preserveAspectRatio='none'><path fill='%231F6B45' d='M0 70 V40 Q15 15 30 38 Q42 10 60 34 Q75 5 92 36 Q105 18 120 40 Q138 8 155 35 Q168 15 185 38 Q200 6 218 34 Q232 18 248 40 Q262 10 280 36 Q290 25 300 38 V70Z'/></svg>") bottom/100% 100% no-repeat; }
.fp-marca { font-family: 'Source Serif 4', Cambria, serif; font-size: 1.45rem; font-weight: 700; line-height: 1.1;
  color: #FFFFFF !important; margin: .2rem 0 .3rem; }
.fp-marca span { display: block; font-family: sans-serif; font-size: .72rem; font-weight: 600; letter-spacing: .14em;
  text-transform: uppercase; color: #C8892A !important; }
[data-testid="stMetric"] { background: #F3F1E8; border-radius: 10px; padding: .7rem .9rem; border-left: 4px solid #1F6B45; }
[data-testid="stMetricValue"] { font-family: 'Source Serif 4', Cambria, serif; color: #0D3B2A; }
.stTabs [aria-selected="true"] { color: #1F6B45 !important; }
</style>""", unsafe_allow_html=True)


def kpis(valores: list[tuple[str, object]]) -> None:
    cols = st.columns(len(valores))
    for c, (rotulo, valor) in zip(cols, valores):
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            valor = f"{valor:,.0f}".replace(",", ".")
        c.metric(rotulo, valor)


def tabela_navegavel(df: pd.DataFrame, destino: str, coluna_id: str, key: str,
                     colunas: dict | None = None, altura: int | None = None) -> None:
    """Tabela em que clicar numa linha abre a página de destino
    (unidade, pessoa ou doc) com o id da linha na URL."""
    if df.empty:
        st.caption("Nenhum registro.")
        return
    config = {coluna_id: None}
    config.update(colunas or {})
    n = st.session_state.get("_nav", 0)
    kw = {"height": altura} if altura else {}
    ev = st.dataframe(df, hide_index=True, on_select="rerun", selection_mode="single-row",
                      column_config=config, key=f"{key}_{n}", width="stretch", **kw)
    linhas = ev.selection.rows
    if linhas:
        st.session_state["_nav"] = n + 1
        st.switch_page(PAGINAS[destino], query_params={destino: str(df.iloc[linhas[0]][coluna_id])})
    st.caption("Clique numa linha para abrir o detalhe.")


def seletor_url(rotulo: str, opcoes: list, param: str, key: str, **kw):
    """Selectbox sincronizado com ?param= na URL, nos dois sentidos.

    Um link (ou clique numa tabela) que muda o parâmetro prevalece sobre a
    seleção guardada na sessão; escolher no seletor atualiza a URL."""
    url = st.query_params.get(param)
    marca = f"_url_{key}"
    if url != st.session_state.get(marca):          # a URL mudou por fora
        st.session_state[key] = url if url in opcoes else None
        st.session_state[marca] = url
    elif key not in st.session_state:
        st.session_state[key] = None
    sel = st.selectbox(rotulo, opcoes, key=key, **kw)
    if sel is not None:
        st.query_params[param] = sel
    elif param in st.query_params:
        del st.query_params[param]
    st.session_state[marca] = sel
    return sel


def link(destino: str, valor: str, rotulo: str, icone: str | None = None) -> None:
    st.page_link(PAGINAS[destino], label=rotulo, icon=icone, query_params={destino: valor})


def aviso_tema_provisorio() -> None:
    from lib import dados
    if dados.tem_semantica():
        st.caption("Temas identificados por similaridade semântica (SBERT + BERTopic) a partir de título, resumo "
                   "e palavras-chave; nomes dos temas revisados a partir dos termos mais característicos de cada um.")
    else:
        st.info("**Temas provisórios:** enquanto o modelo de temas não é gerado, os temas são aproximados "
                "pelas palavras-chave declaradas nos documentos.", icon=":material/info:")


def rede_pyvis(nos: pd.DataFrame, arestas: pd.DataFrame, altura: int = 620,
               destaque: str | None = None, layout_arestas: pd.DataFrame | None = None,
               centro: str | None = None) -> None:
    """nos: id, rotulo, tamanho, grupo, titulo · arestas: origem, destino, peso, titulo

    O layout é calculado aqui (força dirigida, semente fixa) e enviado com
    posições fixas: sem simulação física no navegador, a rede não fica se
    movendo. Clicar num nó destaca suas conexões e esmaece o resto; nós são
    arrastáveis; zoom e tooltips funcionam. `centro` fixa um nó no meio."""
    # Layout sobre todas as relações (não só as exibidas), com pesos
    # normalizados: pesos brutos altos colapsariam os nós no centro.
    base = arestas if layout_arestas is None else layout_arestas
    g = nx.Graph()
    g.add_nodes_from(nos["id"].astype(str))
    wref = base["peso"].max() if not base.empty else 1
    for _, a in base.iterrows():
        g.add_edge(str(a["origem"]), str(a["destino"]), weight=(float(a["peso"]) / wref) ** 0.5)
    k = 1.5 / max(g.number_of_nodes(), 1) ** 0.5
    if centro and centro in g:
        # Radial: foco no centro; parceiras em círculo, ordenadas por grupo,
        # mais próximas quanto mais forte a relação com o foco.
        import math
        viz = [n for n in g.nodes if n != centro]
        forca_rel = {n: g[centro][n]["weight"] if g.has_edge(centro, n) else 0 for n in viz}
        fmax = max(forca_rel.values(), default=1) or 1
        grupo = dict(zip(nos["id"].astype(str), nos.get("grupo", pd.Series(0, index=nos.index))))
        viz.sort(key=lambda n: (grupo.get(n, 0), -forca_rel[n]))
        pos = {centro: (0.0, 0.0)}
        for i, n in enumerate(viz):
            ang = 2 * math.pi * i / max(len(viz), 1)
            r = 0.45 + 0.55 * (1 - forca_rel[n] / fmax)
            pos[n] = (r * math.cos(ang), r * math.sin(ang))
    else:
        pos = nx.spring_layout(g, weight="weight", k=k, iterations=500, seed=42)
    raio = 380

    net = Network(height=f"{altura}px", width="100%", bgcolor="#ffffff", font_color="#222222",
                  cdn_resources="remote", neighborhood_highlight=True)
    tam = nos["tamanho"].astype(float)
    escala = (tam - tam.min()) / (tam.max() - tam.min() + 1e-9)
    for (_, n), e in zip(nos.iterrows(), escala):
        cor = PALETA[int(n.get("grupo", 0)) % len(PALETA)]
        x, y = pos[str(n["id"])]
        net.add_node(str(n["id"]), label=str(n["rotulo"]), title=str(n.get("titulo", n["rotulo"])),
                     size=8 + 22 * float(e), color=cor, x=float(x) * raio, y=float(y) * raio,
                     physics=False, font={"size": 15, "strokeWidth": 4, "strokeColor": "#ffffff"},
                     borderWidth=4 if destaque and n["id"] == destaque else 1)
    wmax = arestas["peso"].max() if not arestas.empty else 1
    for _, a in arestas.iterrows():
        rel = float(a["peso"]) / wmax
        net.add_edge(str(a["origem"]), str(a["destino"]), title=str(a.get("titulo", "")),
                     width=0.5 + 6 * rel, color={"color": "#8a96a3", "opacity": 0.25 + 0.5 * rel})
    net.set_options("""{
      "physics": {"enabled": false},
      "edges": {"smooth": false},
      "interaction": {"hover": true, "navigationButtons": true, "dragNodes": true, "tooltipDelay": 120}
    }""")
    components.html(net.generate_html(), height=altura + 20, scrolling=False)


def comunidades(arestas: pd.DataFrame) -> dict:
    """Louvain (semente fixa) sobre o grafo ponderado → {nó: comunidade}"""
    g = nx.Graph()
    for _, a in arestas.iterrows():
        g.add_edge(a["origem"], a["destino"], weight=float(a["peso"]))
    if g.number_of_edges() == 0:
        return {}
    comms = nx.community.louvain_communities(g, weight="weight", seed=42)
    comms = sorted(comms, key=len, reverse=True)
    return {n: i for i, c in enumerate(comms) for n in c}
