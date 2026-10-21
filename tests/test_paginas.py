"""Roda cada página do app sem erro, sem filtro e com filtro (python -m pytest tests -q, na raiz)."""

import os
import shutil
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "app.py")
sys.path.insert(0, str(Path(APP).parent))   # "from lib import ..." como no streamlit run

# Como em produção: o app online baixa o banco como "observatorio_florestas-<id>.duckdb" (hífen no nome do
# catálogo). Os testes usam uma cópia com esse formato de nome.
_ORIG = Path(APP).parents[1] / "data" / "observatorio_florestas.duckdb"
_COPIA = _ORIG.with_name("observatorio_florestas-123456.duckdb")
if not _COPIA.exists() or _COPIA.stat().st_mtime < _ORIG.stat().st_mtime:
    shutil.copy(_ORIG, _COPIA)
os.environ["OBS_FLORESTAS_DB"] = str(_COPIA)
PAGINAS = ["centro", "tendencias", "lacunas", "paises", "embrapa", "unidades", "redes", "mapa", "pesquisadores",
           "temas", "temas_fp", "programacao", "documentos", "metodologia"]


@pytest.mark.parametrize("filtro", [{}, {"f_linha": ["LIN.SAN"], "f_colecao": ["E"]},
                                    {"f_sistema": ["PLA"], "f_nivel": ["nucleo"]}])
@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina(pagina, filtro):
    at = AppTest.from_file(APP, default_timeout=120)
    for k, v in filtro.items():
        at.session_state[k] = v
    at.run()
    at.switch_page(f"paginas/{pagina}.py").run()
    assert not at.exception, [e.value for e in at.exception]
