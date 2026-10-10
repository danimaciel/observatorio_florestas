"""Acesso somente leitura ao observatorio_florestas.duckdb (pipeline/montar_banco.R).

É o banco do Observatório de P&D da Embrapa recortado para as Florestas Plantadas, com o mesmo
esquema, mais as tabelas fp_* (facetas do Centro de Referência). Localmente o banco é lido de data/. No Streamlit Cloud (onde data/
não é versionada) ele é baixado de uma Release do GitHub, configurada em
.streamlit/secrets.toml:

    [dados]
    repo = "usuario/repositorio"
    tag = "dados-2026-09"
    arquivo = "observatorio_florestas.duckdb"
    token = "..."   # só para repositório privado
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
DB = RAIZ / "data" / "observatorio_florestas.duckdb"

TIPOS = {"projeto": "Projetos", "publicacao": "Publicações", "tecnologia": "Tecnologias"}
CORES_TIPO = {"projeto": "#8A5A3B", "publicacao": "#1F6B45", "tecnologia": "#C8892A"}
CAMADAS = {
    "publicacoes": "Publicações em conjunto",
    "tecnologias_indireta": "Tecnologia que usa publicação de outra unidade",
}
# Explicação das duas medidas de relação (exemplos reais, publicações 1990–2026)
METRICAS_AJUDA = """
**Intensidade — quanto duas unidades trabalham juntas, em volume.**
É a contagem de documentos em comum, com um desconto para documentos que envolvem muitas unidades: numa
publicação com só 2 unidades, o par recebe 1 ponto; numa com 3 unidades, cada um dos 3 pares recebe ½; e
assim por diante. Assim, um trabalho feito por 10 unidades não pesa como 10 parcerias fortes.
*Ex.: Hortaliças e Solos têm 88 publicações em comum → intensidade 63* (parte delas envolve outras unidades).

**Força de associação — se a parceria é mais forte do que o esperado pelo tamanho das unidades.**
Unidades grandes se cruzam com todo mundo só por serem grandes. A força compara a intensidade observada com a
que se esperaria se as parcerias fossem distribuídas ao acaso, proporcionalmente ao volume de cada unidade:
**1** = o esperado · **2** = o dobro · **abaixo de 1** = menos que o esperado.
*Ex.: Cerrados e Recursos Genéticos têm intensidade alta (54), mas força 1,7 — duas das maiores unidades,
parceria próxima do esperado. Gado de Corte e Pantanal têm intensidade menor (21), mas força 4,1 —
colaboram quatro vezes mais do que o tamanho delas faria prever: uma afinidade específica.*

**Em resumo:** a intensidade responde *"com quem trabalha mais?"*; a força responde *"com quem tem uma
afinidade especial, descontado o tamanho?"*.
"""

# Explicação exibida junto aos filtros de camada
CAMADAS_AJUDA = (
    "**Publicações em conjunto**: duas unidades se ligam quando participam da mesma publicação — "
    "porque ambas a registraram no repositório ou porque entre os autores há pesquisadores das duas. "
    "Ex.: um artigo com autores da Solos e do Semiárido liga Solos–Semiárido.\n\n"
    "**Tecnologia que usa publicação de outra unidade**: a página de cada tecnologia cita publicações que a "
    "fundamentam. Se uma tecnologia da unidade A cita uma publicação da unidade B, liga A–B: a pesquisa "
    "de B contribuiu para um resultado de A. É uma evidência indireta e mais rara (≈ 320 citações)."
)
GRUPOS_PUB = {
    "periodico": "Artigo em periódico",
    "anais_completo": "Artigo em anais",
    "anais_resumo": "Resumo em anais",
    "livro_capitulo": "Livro / capítulo",
    "tecnica": "Publicação técnica",
    "tese": "Tese",
    "divulgacao": "Divulgação",
    "outros": "Outros",
}


def _banco_da_release(cfg) -> Path:
    """Garante uma cópia local do banco anexado à Release e devolve seu caminho.

    A cópia leva o id do arquivo na Release no nome: republicar o banco (mesmo
    com a mesma tag) gera um id novo, e o app baixa a versão nova ao reiniciar."""
    cab = {"Accept": "application/vnd.github+json", "User-Agent": "observatorio-embrapa"}
    if cfg.get("token"):
        cab["Authorization"] = f"Bearer {cfg['token']}"
    url = f"https://api.github.com/repos/{cfg['repo']}/releases/tags/{cfg['tag']}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=30) as r:
            release = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 404):
            st.error("Não foi possível acessar os dados do Observatório no GitHub. O token de acesso pode ter "
                     "expirado ou não ter permissão para o repositório de dados: gere um novo e atualize "
                     "`token` nos secrets do app.")
            st.stop()
        raise
    nome = cfg.get("arquivo", DB.name)
    asset = next((a for a in release["assets"] if a["name"] == nome), None)
    if asset is None:
        st.error(f"O arquivo `{nome}` não está na release `{cfg['tag']}`.")
        st.stop()
    destino = DB.parent / f"{Path(nome).stem}-{asset['id']}.duckdb"
    if destino.exists() and destino.stat().st_size == asset["size"]:
        return destino
    cab["Accept"] = "application/octet-stream"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    with urllib.request.urlopen(urllib.request.Request(asset["url"], headers=cab), timeout=60) as r, \
            open(tmp, "wb") as f:
        while bloco := r.read(1 << 20):
            f.write(bloco)
    tmp.replace(destino)
    for antigo in DB.parent.glob(f"{Path(nome).stem}-*.duckdb"):  # versões anteriores
        if antigo != destino:
            antigo.unlink(missing_ok=True)
    return destino


@st.cache_resource(show_spinner="Carregando a base do Observatório…")
def conexao() -> duckdb.DuckDBPyConnection:
    try:
        cfg = st.secrets.get("dados")
    except Exception:  # sem secrets.toml (uso local)
        cfg = None
    if cfg:
        caminho = _banco_da_release(cfg)
    elif DB.exists():
        caminho = DB
    else:
        st.error(f"Base não encontrada em `{DB}`. Rode o pipeline (`targets::tar_make()`) ou configure "
                 "`[dados]` em `.streamlit/secrets.toml`.")
        st.stop()
    return duckdb.connect(str(caminho), read_only=True)


# Filtro global do recorte (barra lateral) -----------------------------------------------
# Cada sessão tem sua conexão (cursor). Quando há filtro, as tabelas por documento são
# "sombreadas" por views temporárias com o mesmo nome, restritas aos documentos filtrados: todas as
# páginas herdadas do Observatório passam a respeitar o filtro sem mudar uma linha de SQL.
TABELAS_DOC = ["documento", "documento_unidade", "documento_pessoa", "doc_pessoa", "doc_tema", "doc_bioma",
               "doc_estado", "doc_municipio", "doc_desafio", "documento_keyword", "aresta_unidade",
               "aresta_pessoa", "publicacao", "fp_doc", "fp_doc_linha", "fp_doc_colecao", "fp_doc_kg",
               "fp_doc_tema_fp"]
FILTROS = {"linha": [], "colecao": [], "nivel": [], "sistema": []}


def filtro_atual() -> dict:
    return {k: tuple(sorted(st.session_state.get(f"f_{k}", []) or [])) for k in FILTROS}


def chave_filtro() -> str:
    f = filtro_atual()
    return "|".join(f"{k}={','.join(v)}" for k, v in f.items() if v)


def _sql_filtro(f: dict) -> str:
    cond = []
    lst = lambda v: ", ".join("'" + x.replace("'", "''") + "'" for x in v)
    if f["linha"]:
        cond.append(f"doc_uid in (select doc_uid from {{cat}}.main.fp_doc_linha where linha in ({lst(f['linha'])}))")
    if f["colecao"]:
        cond.append(f"doc_uid in (select doc_uid from {{cat}}.main.fp_doc_colecao where colecao in ({lst(f['colecao'])}))")
    if f["nivel"]:
        cond.append(f"nivel in ({lst(f['nivel'])})")
    if f["sistema"]:
        cond.append(f"sis_final in ({lst(f['sistema'])})")
    return " and ".join(cond)


def _con() -> duckdb.DuckDBPyConnection:
    """Conexão da sessão, com as views temporárias do filtro atual."""
    base = conexao()
    ss = st.session_state
    if "_con" not in ss:
        ss["_con"] = base.cursor()
        ss["_con_filtro"] = None
        ss["_cat"] = base.execute("select current_database()").fetchone()[0]
    chave = chave_filtro()
    if ss["_con_filtro"] != chave:
        c, cat = ss["_con"], ss["_cat"]
        for t in TABELAS_DOC:
            c.execute(f"drop view if exists temp.{t}")
        if chave:
            cond = _sql_filtro(filtro_atual()).replace("{cat}", cat)
            c.execute("drop table if exists temp._sel")
            c.execute(f"create temp table _sel as select doc_uid from {cat}.main.fp_doc where {cond}")
            for t in TABELAS_DOC:
                c.execute(f"create temp view {t} as select * from {cat}.main.{t} "
                          f"where doc_uid in (select doc_uid from temp._sel)")
        ss["_con_filtro"] = chave
    return ss["_con"]


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2000)
def _q(sql: str, params: tuple, filtro: str, _c) -> pd.DataFrame:
    return _c.execute(sql, list(params)).df()


def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    c = _con()
    return _q(sql, params, chave_filtro(), c)


# Filtros globais (definidos na barra lateral em app.py) -----------------------

def periodo() -> tuple[int, int]:
    return st.session_state.get("periodo", (1990, 2026))


# Consultas de referência ------------------------------------------------------

def unidades() -> pd.DataFrame:
    # n_docs = 0: unidade sem produção registrada (ex.: escritórios que só aparecem na afiliação de pessoas);
    # fica fora dos seletores, mas continua disponível para exibir nomes.
    df = q("""select u.unidade_id, u.nome_atual, u.sigla_historica, u.categoria, u.uf,
                     count(distinct du.doc_uid) n_docs
              from unidade u left join documento_unidade du using (unidade_id)
              group by all order by u.nome_atual""")
    df["rotulo"] = df["nome_atual"].str.replace("Embrapa ", "", regex=False)
    return df


def nome_unidade(unidade_id: str | None) -> str:
    # documentos sem unidade registrada chegam como None/NaN (ex.: ~3,7% das publicações)
    if unidade_id is None or (isinstance(unidade_id, float) and pd.isna(unidade_id)) or unidade_id == "":
        return "—"
    u = unidades().set_index("unidade_id")
    return str(u["nome_atual"].get(unidade_id, unidade_id))


def rotulo_unidade(unidade_id: str | None) -> str:
    return nome_unidade(unidade_id).replace("Embrapa ", "")


@st.cache_data(show_spinner=False)
def meta() -> dict:
    return q("select * from meta").iloc[0].to_dict()


def rede_unidades(a0: int, a1: int, camadas: tuple[str, ...]) -> pd.DataFrame:
    """Arestas unidade–unidade agregadas no período, com:
    peso      contagem fracionária (cada documento distribui 1 entre seus pares)
    n_docs    documentos que sustentam a relação
    forca     força de associação = observado / esperado dado o tamanho das
              duas unidades (> 1: relação mais intensa que o esperado)"""
    if not camadas:
        return pd.DataFrame(columns=["unidade1", "unidade2", "peso", "n_docs", "forca"])
    a = q("""
        select unidade1, unidade2, sum(peso_frac) peso, count(distinct doc_uid) n_docs
        from aresta_unidade where ano between ? and ? and list_contains(?, camada)
        group by all
    """, (a0, a1, list(camadas)))
    if a.empty:
        return a.assign(forca=[])
    s = pd.concat([a[["unidade1", "peso"]].rename(columns={"unidade1": "u"}),
                   a[["unidade2", "peso"]].rename(columns={"unidade2": "u"})]).groupby("u")["peso"].sum()
    W = a["peso"].sum()
    a["forca"] = 2 * W * a["peso"] / (a["unidade1"].map(s) * a["unidade2"].map(s))
    return a


def docs_da_relacao(u1: str, u2: str, a0: int, a1: int, camadas: tuple[str, ...]) -> list[str]:
    x, y = sorted([u1, u2])
    return q("""select distinct doc_uid from aresta_unidade
                where unidade1 = ? and unidade2 = ? and ano between ? and ? and list_contains(?, camada)""",
             (x, y, a0, a1, list(camadas)))["doc_uid"].tolist()


def palavras_chave(doc_uids: tuple[str, ...], n: int = 15) -> pd.DataFrame:
    return q("""
        select lower(any_value(keyword_raw)) palavra, count(distinct doc_uid) n
        from documento_keyword where list_contains(?, doc_uid)
        group by keyword_norm order by n desc limit ?
    """, (list(doc_uids), n))


# Camada semântica (temas e similaridade) ------------------------------------------

@st.cache_data(show_spinner=False)
def tem_semantica() -> bool:
    tabelas = set(q("select table_name from duckdb_tables()").table_name)
    return {"tema", "doc_tema", "similaridade"} <= tabelas


@st.cache_data(show_spinner=False)
def temas() -> pd.DataFrame:
    t = q("select * from tema")
    t["n_total"] = t.n_projeto + t.n_publicacao + t.n_tecnologia
    return t


def cores_macrotemas() -> dict[str, str]:
    """Cor fixa por macrotema (nome → cor), a mesma em todos os gráficos; 26 cores distintas."""
    import plotly.express as px
    macros = temas().query("nivel == 1").sort_values("tema_id")
    paleta = px.colors.qualitative.Alphabet
    return {r: paleta[i % len(paleta)] for i, r in enumerate(macros.rotulo)}


def rotulo_tema(tema_id: str) -> str:
    t = temas().set_index("tema_id")
    return t.rotulo.get(tema_id, tema_id)


def temas_de_docs(doc_uids: tuple[str, ...], n: int = 5, nivel: str = "tema") -> pd.DataFrame:
    """Temas mais frequentes num conjunto de documentos (nivel: 'tema' ou 'macro')."""
    col = "tema_id" if nivel == "tema" else "macro_id"
    r = q(f"""select {col} tema_id, count(*) n from doc_tema where list_contains(?, doc_uid)
              group by 1 order by n desc limit ?""", (list(doc_uids), n))
    r["rotulo"] = r.tema_id.map(rotulo_tema)
    return r


def resumo_temas(doc_uids, n: int = 3) -> str:
    """Rótulos dos n temas mais frequentes (texto curto para tabelas)."""
    if doc_uids is None or len(doc_uids) == 0:
        return ""
    if not tem_semantica():
        kw = palavras_chave(tuple(doc_uids), n)
        return ", ".join(kw.palavra)
    return " · ".join(temas_de_docs(tuple(doc_uids), n).rotulo)


def faixa_anos() -> tuple[int, int]:
    r = q("select min(ano) a0, max(ano) a1 from documento where ano >= 1970")
    return int(r.a0[0]), int(r.a1[0])
