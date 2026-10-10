"""Observatório das Florestas Plantadas — ponto de entrada.

O Observatório de P&D da Embrapa recortado para o Centro de Referência da FAO em Florestas
Plantadas e Sistemas ILPF (Embrapa Florestas). Executar na raiz do projeto:  streamlit run app/app.py
"""

import streamlit as st

from lib import dados, fp, ui

st.set_page_config(page_title="Observatório das Florestas Plantadas", page_icon=":material/forest:",
                   layout="wide")
ui.estilo_florestas()

paginas = {
    "Centro de Referência": [
        st.Page("paginas/centro.py", title="Visão geral", icon=":material/forest:", url_path="centro", default=True),
        st.Page("paginas/tendencias.py", title="Tendências", icon=":material/trending_up:", url_path="tendencias"),
        st.Page("paginas/lacunas.py", title="Lacunas", icon=":material/grid_view:", url_path="lacunas"),
        st.Page("paginas/paises.py", title="Países", icon=":material/public:", url_path="paises"),
    ],
    "Quem faz": [
        st.Page("paginas/embrapa.py", title="Produção e colaboração", icon=":material/account_balance:",
                url_path="embrapa"),
        st.Page("paginas/unidades.py", title="Unidades", icon=":material/apartment:", url_path="unidades"),
        st.Page("paginas/redes.py", title="Redes", icon=":material/hub:", url_path="redes"),
        st.Page("paginas/mapa.py", title="Mapa", icon=":material/map:", url_path="mapa"),
        st.Page("paginas/pesquisadores.py", title="Pesquisadores", icon=":material/person_search:",
                url_path="pesquisadores"),
    ],
    "Conteúdo": [
        st.Page("paginas/temas_fp.py", title="Temas técnicos", icon=":material/park:", url_path="temas_tecnicos"),
        st.Page("paginas/temas.py", title="Temas automáticos", icon=":material/category:", url_path="temas"),
        st.Page("paginas/programacao.py", title="Programação", icon=":material/flag:", url_path="programacao"),
        st.Page("paginas/documentos.py", title="Documentos", icon=":material/description:", url_path="documentos"),
    ],
    "Sobre": [
        st.Page("paginas/metodologia.py", title="Metodologia", icon=":material/menu_book:", url_path="metodologia"),
    ],
}
pg = st.navigation(paginas)

with st.sidebar:
    st.markdown('<div class="fp-marca"><span>Observatório</span>Florestas Plantadas</div>', unsafe_allow_html=True)
    st.caption("Centro de Referência da FAO em Florestas Plantadas e Sistemas ILPF · Embrapa Florestas")
    a0, a1 = dados.faixa_anos()
    if "periodo" not in st.session_state:
        st.session_state["periodo"] = (a0, a1)   # período completo: mesmos números do site e da apresentação
    st.slider("Período", min_value=a0, max_value=a1, key="periodo",
              help="Projetos pelo ano de início; publicações e tecnologias pelo ano.")
    st.markdown("**Recorte**")
    lin = fp.linhas()
    st.multiselect("Linha do Centro", lin.no_id.tolist(), key="f_linha", format_func=fp.rotulo_linha_curto,
                   placeholder="Todas")
    st.multiselect("Coleção", list(fp.COLECOES), key="f_colecao", format_func=fp.COLECOES.get, placeholder="Todas")
    st.multiselect("Sistema", list(fp.SISTEMAS), key="f_sistema", format_func=fp.SISTEMAS.get, placeholder="Todos")
    st.multiselect("Abrangência", list(fp.NIVEIS), key="f_nivel", format_func=fp.NIVEIS.get, placeholder="Ambas")
    if dados.chave_filtro():
        st.caption("Os filtros valem para todas as páginas.")
    m = dados.meta()
    st.caption(f"Dados: exportação {m['exportacao']} · recorte gerado em {m['gerado_em']}")

pg.run()
