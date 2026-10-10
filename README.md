# Observatório das Florestas Plantadas

O Observatório de P&D da Embrapa recortado para o **Centro de Referência da FAO em Florestas Plantadas e
Sistemas ILPF** (Embrapa Florestas). Apoia o grupo especial do Centro a decidir: quem faz o quê (unidades,
pessoas, redes), o que cresce e o que cai, onde estão as lacunas e que conhecimento serve a cada país.

## Recorte

- **Publicações e soluções tecnológicas** = acervo do protótipo das Florestas Plantadas (pasta
  `Florestas Plantadas FAO` do Observatório): busca semântica SBERT + classificador + dicionário de espécies,
  definição FAO FRA 2020/2025, ILPF no núcleo (escopo do Centro).
- **Projetos** = 463 candidatos pré-rotulados por Claude (`Florestas Plantadas FAO/data/prerrotulos_projetos`);
  entram os relevantes e parciais (256). Aguardam conferência do grupo.
- Facetas próprias: linha do Centro, coleção, espécie, tema técnico, sistema, clima de Köppen e países africanos.

## Páginas

- **Centro de Referência:** Visão geral · Tendências (dois períodos comparados) · Lacunas (espécie × linha,
  clima × linha, pesquisa × entrega) · Países (clima igual e espécies presentes).
- **Quem faz:** Produção e colaboração · Unidades · Redes · Mapa · Pesquisadores (herdadas do Observatório).
- **Conteúdo:** Temas técnicos (taxonomia das Florestas) · Temas automáticos (BERTopic do Observatório, contados
  no recorte) · Programação · Documentos.
- Filtros globais na barra lateral (linha, coleção, sistema, abrangência) valem para **todas** as páginas: as
  tabelas por documento são sombreadas por views temporárias na conexão da sessão (`app/lib/dados.py`).

## Como rodar

```
# 1. no Observatório: pipeline das Florestas gera o recorte (alvo arq_recorte)
#    (pasta "Florestas Plantadas FAO", PowerShell) targets::tar_make()
# 2. aqui: monta o banco
Rscript pipeline/montar_banco.R
# 3. app
streamlit run app/app.py
# testes (todas as páginas, com e sem filtro)
python -m pytest tests -q
```

Visual: identidade "iAgro Florestas" (opção B do esboço), em `app/lib/ui.py::estilo_florestas` e `.streamlit/config.toml`.

## Publicação

- Código (público): https://github.com/danimaciel/observatorio_florestas
- Dados (privado): https://github.com/danimaciel/observatorio_florestas_dados — Releases `dados-AAAA-MM` com
  `observatorio_florestas.duckdb`.
- App no Streamlit Community Cloud: arquivo principal `app/app.py`; secrets:

```toml
[dados]
repo = "danimaciel/observatorio_florestas_dados"
tag = "dados-2026-10"
arquivo = "observatorio_florestas.duckdb"
token = "<token fine-grained com leitura de Contents no repositório de dados>"
```

Para atualizar os dados: rodar o pipeline das Florestas e `pipeline/montar_banco.R`, depois
`gh release create dados-AAAA-MM data/observatorio_florestas.duckdb --repo danimaciel/observatorio_florestas_dados`
e trocar `tag` nos secrets (ou republicar com `--clobber` e reiniciar o app).
