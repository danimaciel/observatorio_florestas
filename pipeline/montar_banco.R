# Monta data/observatorio_florestas.duckdb: o banco do Observatório de P&D da Embrapa recortado
# para as Florestas Plantadas (Centro de Referência da FAO em Florestas Plantadas e ILPF).
#
# Entradas (pasta-irmã "observatorio de P&D Embrapa"):
#   data/processed/observatorio_app.duckdb                 banco do app do Observatório
#   Florestas Plantadas FAO/data/recorte/*.parquet         recorte e facetas (alvo arq_recorte do pipeline das Florestas)
#   Florestas Plantadas FAO/ref/taxonomia_v2.csv           taxonomia (rótulos pt/en/fr, linhas do Centro)
#
# Uso (de dentro desta pasta):  Rscript pipeline/montar_banco.R
# O banco tem o MESMO esquema do Observatório (as páginas do app funcionam sem mudança), só com os
# documentos do recorte, mais tabelas fp_* com as facetas das Florestas Plantadas.

OBS <- normalizePath(file.path("..", "observatorio de P&D Embrapa"), winslash = "/", mustWork = TRUE)
FP <- file.path(OBS, "Florestas Plantadas FAO")
ORIGEM <- file.path(OBS, "data", "processed", "observatorio_app.duckdb")
DESTINO <- file.path("data", "observatorio_florestas.duckdb")
REC <- file.path(FP, "data", "recorte")

dir.create("data", showWarnings = FALSE)
if (file.exists(DESTINO)) file.remove(DESTINO)
con <- DBI::dbConnect(duckdb::duckdb(DESTINO, shared_home = FALSE))
on.exit(DBI::dbDisconnect(con, shutdown = TRUE))
ex <- function(sql) invisible(DBI::dbExecute(con, sql))
ex(sprintf("attach '%s' as src (read_only)", ORIGEM))

# --- recorte e facetas -------------------------------------------------------------------
ex(sprintf("create table fp_doc as select * from read_parquet('%s/recorte_docs.parquet')", REC))
ex(sprintf("create table fp_pais_kg as select * from read_parquet('%s/paises_kg.parquet')", REC))
ex(sprintf("create table fp_especie_pais as select * from read_parquet('%s/especies_pais.parquet')", REC))
tax <- readr::read_csv(file.path(FP, "ref", "taxonomia_v2.csv"), show_col_types = FALSE)
DBI::dbWriteTable(con, "fp_taxonomia", as.data.frame(tax))
# formatos longos (um documento pode ter várias linhas e estar em várias coleções)
ex("create table fp_doc_linha as
    select doc_uid, unnest(string_split(linhas, '+')) linha from fp_doc where linhas is not null")
ex("create table fp_doc_tema_fp as
    select doc_uid, 'TEM.' || unnest(string_split(temas, '+')) tema from fp_doc where temas is not null and temas <> ''")
ex("create table fp_doc_colecao as
    select doc_uid, 'E' colecao from fp_doc where col_eucalipto union all
    select doc_uid, 'N' from fp_doc where col_nativas union all
    select doc_uid, 'A' from fp_doc where col_africano union all
    select doc_uid, 'G' from fp_doc where col_geral")
ex("create table fp_doc_kg as
    select doc_uid, unnest(string_split(kg, '+')) kg from fp_doc where kg is not null")

# --- tabelas do Observatório, recortadas -----------------------------------------------------
por_doc <- c("documento", "documento_unidade", "documento_pessoa", "doc_pessoa", "doc_tema", "doc_bioma",
             "doc_estado", "doc_municipio", "doc_desafio", "documento_keyword", "aresta_unidade",
             "aresta_pessoa", "publicacao")
for (t in por_doc)
  ex(sprintf("create table %s as select * from src.%s where doc_uid in (select doc_uid from fp_doc)", t, t))
ex("create table similaridade as select * from src.similaridade
    where origem_uid in (select doc_uid from fp_doc) and destino_uid in (select doc_uid from fp_doc)")
ex("create table doc_link as select * from src.doc_link where origem_uid in (select doc_uid from fp_doc)")
ex("create table pessoa_tecnologia as select * from src.pessoa_tecnologia
    where tecnologia_uid in (select doc_uid from fp_doc)")
# pessoas: só as que aparecem no recorte, com contagens recalculadas dentro dele
ex("create table pessoa as
    select p.* exclude (n_obras, n_projetos_lider),
           coalesce(o.n_obras, 0) n_obras, coalesce(o.n_projetos_lider, 0) n_projetos_lider
    from src.pessoa p join (
      select dp.pessoa_id,
             count(distinct case when d.tipo_doc <> 'projeto' then dp.doc_uid end) n_obras,
             count(distinct case when d.tipo_doc = 'projeto' and dp.papel ilike '%lider%' then dp.doc_uid end) n_projetos_lider
      from documento_pessoa dp join documento d using (doc_uid) group by 1) o using (pessoa_id)")
# tabelas de referência: inteiras
# temas automáticos do Observatório (BERTopic): mesmos rótulos, mas contagens só do recorte e
# só os temas (e macrotemas) que têm documento aqui
ex("create table tema as
    with n as (select t.tema_id, d.tipo_doc, count(*) n from doc_tema t join documento d using (doc_uid) group by all),
         m as (select t.macro_id tema_id, d.tipo_doc, count(*) n from doc_tema t join documento d using (doc_uid) group by all),
         c as (select tema_id,
                      sum(n) filter (where tipo_doc = 'projeto') n_projeto,
                      sum(n) filter (where tipo_doc = 'publicacao') n_publicacao,
                      sum(n) filter (where tipo_doc = 'tecnologia') n_tecnologia
               from (select * from n union all select * from m) group by 1)
    select s.* exclude (n_projeto, n_publicacao, n_tecnologia),
           coalesce(c.n_projeto, 0) n_projeto, coalesce(c.n_publicacao, 0) n_publicacao,
           coalesce(c.n_tecnologia, 0) n_tecnologia
    from src.tema s join c using (tema_id)")
for (t in c("desafio", "unidade", "unidade_localizacao", "municipio_centroide", "proximidade_unidade"))
  ex(sprintf("create table %s as select * from src.%s", t, t))
ex(sprintf("create table meta as select exportacao, '%s' gerado_em, arquivos_truncados,
            'Florestas Plantadas (Centro de Referência FAO em Florestas Plantadas e ILPF)' recorte from src.meta",
           format(Sys.time(), "%Y-%m-%d")))
ex("detach src")
ex("checkpoint")

n <- DBI::dbGetQuery(con, "select d.tipo_doc, f.nivel, count(*) n from fp_doc f join documento d using (doc_uid) group by all order by all")
print(n)
cat("pessoas:", DBI::dbGetQuery(con, "select count(*) n from pessoa")$n, "\n")
