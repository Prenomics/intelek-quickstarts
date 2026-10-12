/*
================================================================================
 Unify the 3 lead sources into a single, normalized table: leads
 (Postgres; tables live in the DB_SCHEMA schema, set as search_path when you run it)

 Input  (Excels loaded as-is, see load_reference_data.py):
   leads_web_form    -> "Lead ID", "Full Name", "E-mail", "Preferred Language" (English name) ...
   leads_trade_fair  -> id_contacto, nombre, apellidos, correo, idioma (ISO code) ...
   leads_linkedin    -> linkedin_lead_id, first_name, email_address, lang (locale) ...

 Output:
   leads -> one row per lead, snake_case English column names and
                     canonical values:
                       preferred_language  : ISO 639-1 code   (es, ca, en, fr, de, pt, ...)
                       content_of_interest : canonical code   (data_engineering, bi_analytics,
                                             machine_learning, genai, data_governance, cloud_platforms)
                     The original values are kept in *_raw columns for traceability.
                     Values that cannot be mapped become NULL (validated later in Python).

 The script is idempotent: it drops and rebuilds the table on every run.
================================================================================
*/

DROP TABLE IF EXISTS leads;

CREATE TABLE leads (
    lead_id                 VARCHAR(20)  PRIMARY KEY,   -- '<SOURCE>-<source id>', unique across sources
    source_system           VARCHAR(20)  NOT NULL,      -- web_form | trade_fair | linkedin
    source_lead_id          VARCHAR(20)  NOT NULL,      -- id as it comes in the source
    first_name              VARCHAR(100),
    last_name               VARCHAR(100),
    full_name               VARCHAR(200),
    email                   VARCHAR(200),               -- lower-cased and trimmed
    company_name            VARCHAR(200),
    country                 VARCHAR(100),
    job_title               VARCHAR(100),               -- only LinkedIn
    event_name              VARCHAR(100),               -- only trade fair
    preferred_language      VARCHAR(5),
    preferred_language_raw  VARCHAR(50),
    content_of_interest     VARCHAR(30),
    content_of_interest_raw VARCHAR(100),
    created_at              TIMESTAMP,
    loaded_at               TIMESTAMP    NOT NULL DEFAULT now()
);

INSERT INTO leads (
    lead_id, source_system, source_lead_id,
    first_name, last_name, full_name, email, company_name, country, job_title, event_name,
    preferred_language, preferred_language_raw,
    content_of_interest, content_of_interest_raw,
    created_at
)

-- ---------------------------------------------------------------------------
-- 1) Web form: English headers with spaces -> must be quoted
-- ---------------------------------------------------------------------------
SELECT
    w."Lead ID"                                                AS lead_id,
    'web_form'                                                 AS source_system,
    w."Lead ID"                                                AS source_lead_id,
    split_part(trim(w."Full Name"), ' ', 1)                    AS first_name,
    nullif(regexp_replace(trim(w."Full Name"), '^\S+\s*', ''), '') AS last_name,
    trim(w."Full Name")                                        AS full_name,
    lower(trim(w."E-mail"))                                    AS email,
    trim(w."Company")                                          AS company_name,
    trim(w."Country")                                          AS country,
    NULL                                                       AS job_title,
    NULL                                                       AS event_name,
    CASE lower(trim(w."Preferred Language"))
        WHEN 'spanish'    THEN 'es'
        WHEN 'catalan'    THEN 'ca'
        WHEN 'english'    THEN 'en'
        WHEN 'french'     THEN 'fr'
        WHEN 'german'     THEN 'de'
        WHEN 'portuguese' THEN 'pt'
    END                                                        AS preferred_language,
    w."Preferred Language"                                     AS preferred_language_raw,
    CASE trim(w."Interest")
        WHEN 'Data Engineering' THEN 'data_engineering'
        WHEN 'BI & Analytics'   THEN 'bi_analytics'
        WHEN 'Machine Learning' THEN 'machine_learning'
        WHEN 'Generative AI'    THEN 'genai'
        WHEN 'Data Governance'  THEN 'data_governance'
        WHEN 'Cloud Platforms'  THEN 'cloud_platforms'
    END                                                        AS content_of_interest,
    w."Interest"                                               AS content_of_interest_raw,
    w."Submitted At"::timestamp                                AS created_at
FROM leads_web_form w

UNION ALL

-- ---------------------------------------------------------------------------
-- 2) Trade fair: Spanish headers, ISO language codes with messy casing/spaces
-- ---------------------------------------------------------------------------
SELECT
    f.id_contacto                                              AS lead_id,
    'trade_fair'                                               AS source_system,
    f.id_contacto                                              AS source_lead_id,
    trim(f.nombre)                                             AS first_name,
    trim(f.apellidos)                                          AS last_name,
    trim(f.nombre) || ' ' || trim(f.apellidos)                 AS full_name,
    lower(trim(f.correo))                                      AS email,
    trim(f.empresa)                                            AS company_name,
    trim(f.pais)                                               AS country,
    NULL                                                       AS job_title,
    trim(f.feria)                                              AS event_name,
    lower(trim(f.idioma))                                      AS preferred_language,
    f.idioma                                                   AS preferred_language_raw,
    CASE lower(trim(f.tema_interes))
        WHEN 'ingeniería de datos' THEN 'data_engineering'
        WHEN 'bi y analítica'      THEN 'bi_analytics'
        WHEN 'machine learning'    THEN 'machine_learning'
        WHEN 'ia generativa'       THEN 'genai'
        WHEN 'gobierno del dato'   THEN 'data_governance'
        WHEN 'cloud'               THEN 'cloud_platforms'
    END                                                        AS content_of_interest,
    f.tema_interes                                             AS content_of_interest_raw,
    f.fecha_contacto::timestamp                                AS created_at
FROM leads_trade_fair f

UNION ALL

-- ---------------------------------------------------------------------------
-- 3) LinkedIn: numeric ids, locale codes (es_ES) and campaign topic codes
-- ---------------------------------------------------------------------------
SELECT
    'LI-' || l.linkedin_lead_id                                AS lead_id,
    'linkedin'                                                 AS source_system,
    l.linkedin_lead_id::text                                   AS source_lead_id,
    trim(l.first_name)                                         AS first_name,
    trim(l.last_name)                                          AS last_name,
    trim(l.first_name) || ' ' || trim(l.last_name)             AS full_name,
    lower(trim(l.email_address))                               AS email,
    trim(l.company_name)                                       AS company_name,
    CASE upper(l.country_code)
        WHEN 'ES' THEN 'Spain'
        WHEN 'GB' THEN 'United Kingdom'
        WHEN 'FR' THEN 'France'
        WHEN 'DE' THEN 'Germany'
        WHEN 'PT' THEN 'Portugal'
        ELSE l.country_code
    END                                                        AS country,
    trim(l.job_title)                                          AS job_title,
    NULL                                                       AS event_name,
    lower(split_part(trim(l.lang), '_', 1))                    AS preferred_language,
    l.lang                                                     AS preferred_language_raw,
    CASE upper(trim(l.campaign_topic))
        WHEN 'DE'    THEN 'data_engineering'
        WHEN 'BI'    THEN 'bi_analytics'
        WHEN 'ML'    THEN 'machine_learning'
        WHEN 'GENAI' THEN 'genai'
        WHEN 'GOV'   THEN 'data_governance'
        WHEN 'CLOUD' THEN 'cloud_platforms'
    END                                                        AS content_of_interest,
    l.campaign_topic                                           AS content_of_interest_raw,
    l.created_ts::timestamp                                    AS created_at
FROM leads_linkedin l;

-- Quick sanity check: rows per source and unmapped values
SELECT
    source_system,
    count(*)                                                   AS n_leads,
    count(*) FILTER (WHERE preferred_language IS NULL)         AS n_unmapped_language,
    count(*) FILTER (WHERE content_of_interest IS NULL)        AS n_unmapped_content
FROM leads
GROUP BY source_system
ORDER BY source_system;
