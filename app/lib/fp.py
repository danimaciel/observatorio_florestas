"""Facetas das Florestas Plantadas (tabelas fp_* do banco): rótulos, cores e consultas comuns."""

import pandas as pd
import streamlit as st

from lib import dados
from lib.dados import q

COLECOES = {"E": "Eucalipto", "N": "Espécies nativas do Brasil", "A": "Espécies de interesse africano",
            "G": "Florestas plantadas em geral"}
NIVEIS = {"nucleo": "Núcleo (floresta plantada e ILPF)", "complementar": "Complementar"}
SISTEMAS = {"PLA": "Plantação florestal", "OPF": "Outra floresta plantada", "INT": "Sistema integrado (ILPF/SAF)"}
GRUPOS_ESP = {"EUC": "Eucalipto", "PIN": "Pínus", "EXO": "Outras exóticas", "NAT": "Nativas do Brasil",
              "MUL": "Várias / sem espécie dominante", "OUT": "Outras"}
KG = {"Af": "Af · tropical úmido", "Am": "Am · tropical de monção", "Aw": "Aw · tropical de savana",
      "BSh": "BSh · semiárido quente", "BWh": "BWh · desértico quente", "BSk": "BSk · semiárido frio",
      "Cfa": "Cfa · subtropical úmido", "Cfb": "Cfb · temperado úmido", "Cwa": "Cwa · inverno seco, verão quente",
      "Cwb": "Cwb · inverno seco, altitude", "Csa": "Csa · mediterrâneo", "Csb": "Csb · mediterrâneo ameno"}
# cores da identidade iAgro Florestas
COR = {"verde": "#1F6B45", "verde_esc": "#0D3B2A", "ambar": "#C8892A", "azul": "#2F6F9F",
       "terra": "#8A5A3B", "folha": "#3F9A5C", "cinza": "#5B6B61", "areia": "#F3F1E8"}
CORES_LINHA = ["#1F6B45", "#C8892A", "#2F6F9F", "#8A5A3B", "#3F9A5C", "#7A4E9C", "#5B6B61"]


@st.cache_data(show_spinner=False)
def taxonomia() -> pd.DataFrame:
    return dados.conexao().cursor().execute("select * from fp_taxonomia").df()


def rotulo(no_id: str) -> str:
    t = taxonomia().set_index("no_id")
    return str(t.rotulo_pt.get(no_id, no_id))


def linhas() -> pd.DataFrame:
    t = taxonomia()
    return t[(t.faceta == "linha") & (t.nivel.astype(str) != "0")][["no_id", "rotulo_pt"]].reset_index(drop=True)


def cores_linhas() -> dict:
    return {r: CORES_LINHA[i % len(CORES_LINHA)] for i, r in enumerate(linhas().rotulo_pt)}


def rotulo_linha_curto(no_id: str) -> str:
    curto = {"LIN.SIL": "Silvicultura e manejo", "LIN.INT": "Sistemas integrados (ILPF)",
             "LIN.GEN": "Melhoramento genético", "LIN.SAN": "Sanidade e controle biológico",
             "LIN.CAR": "Carbono e GEE", "LIN.BIO": "Bioeconomia e química verde",
             "LIN.CAP": "Capacitação e transferência"}
    return curto.get(no_id, rotulo(no_id))


def docs_facetas(a0: int, a1: int) -> pd.DataFrame:
    """Um registro por documento do recorte (respeita o filtro global), com facetas."""
    return q("""select d.doc_uid, d.tipo_doc, d.ano, d.unidade_id, d.titulo, f.nivel, f.sis_final, f.esp_no,
                       f.esp_grupo, f.linhas, f.temas, f.kg, f.ter_ufs
                from documento d join fp_doc f using (doc_uid) where d.ano between ? and ?""", (a0, a1))


def doc_linha(a0: int, a1: int) -> pd.DataFrame:
    r = q("""select l.doc_uid, l.linha, d.tipo_doc, d.ano, d.unidade_id from fp_doc_linha l
             join documento d using (doc_uid) where d.ano between ? and ?""", (a0, a1))
    r["linha_rot"] = r.linha.map(rotulo_linha_curto)
    return r
