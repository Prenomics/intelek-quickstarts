-- Reference data for the Intelek lead-assignment demo (simulates a client's transactional DB).
-- Creates and populates, in schema public:
--   leads_web_form, leads_linkedin, sales_people
-- leads_trade_fair is NOT here: its origin is the Excel reference_data/leads_trade_fair.xlsx.
--
-- Same tables and values as reference_data/*.xlsx, with every column renamed to snake_case
-- ("Lead ID" -> lead_id, "E-mail" -> email, "Max Open Leads" -> max_open_leads...).
-- Values are kept as-is on purpose (messy casing, trailing spaces, a missing e-mail...):
-- the pipeline is meant to clean them.
--
-- Generated from reference_data/*.xlsx - regenerate it if the Excels change.
--
-- Target: Neon. Run the whole file as the project owner role (Neon SQL Editor or psql -f).
-- Idempotent: drops and recreates the three tables in a single transaction. Dropping the
-- tables also drops their grants, so run create_user.sql (section 3) again afterwards.

BEGIN;

DROP TABLE IF EXISTS public.leads_web_form, public.leads_linkedin, public.sales_people;

-- ----------------------------------------------------------------------------------------
-- leads_web_form  (40 rows) - Leads captured by the website form
-- ----------------------------------------------------------------------------------------

CREATE TABLE public.leads_web_form (
    lead_id             TEXT NOT NULL,
    full_name           TEXT,
    email               TEXT,
    company             TEXT,
    country             TEXT,
    preferred_language  TEXT,
    interest            TEXT,
    submitted_at        TIMESTAMP,
    PRIMARY KEY (lead_id)
);
COMMENT ON TABLE public.leads_web_form IS 'Leads captured by the website form';

INSERT INTO public.leads_web_form (lead_id, full_name, email, company, country, preferred_language, interest, submitted_at) VALUES
    ('WEB-0001', 'Harry Wilson', 'harry.wilson@bluewaveenergy.com', 'BlueWave Energy', 'United Kingdom', 'English', 'Data Engineering', '2026-09-09 19:06:00'),
    ('WEB-0002', 'Charlotte Hughes', 'charlotte.hughes@acmeretail.com', 'Acme Retail', 'United Kingdom', 'English', 'Data Governance', '2026-09-02 09:13:00'),
    ('WEB-0003', 'Lucía Sánchez', 'lucia.sanchez@atlastelecom.com', 'Atlas Telecom', 'Spain', 'Spanish', 'Data Governance', '2026-10-05 14:14:00'),
    ('WEB-0004', 'Jordi Vila', 'jordi.vila@atlastelecom.com', 'Atlas Telecom', 'Spain', 'Catalan', 'Machine Learning', '2026-09-28 13:17:00'),
    ('WEB-0005', 'Javier López', 'javier.lopez@vertexinsurance.com', 'Vertex Insurance', 'Spain', 'Spanish', 'Machine Learning', '2026-09-07 13:54:00'),
    ('WEB-0006', 'Jordi Bosch', 'jordi.bosch@alpinebank.com', 'Alpine Bank', 'Spain', 'Catalan', 'Machine Learning', '2026-09-08 14:05:00'),
    ('WEB-0007', 'Isla Wilson', NULL, 'Atlas Telecom', 'United Kingdom', 'English', 'Cloud Platforms', '2026-09-05 08:42:00'),
    ('WEB-0008', 'Javier Sánchez', 'javier.sanchez@rheinautomotive.com', 'Rhein Automotive', 'Spain', 'Spanish', 'Machine Learning', '2026-09-07 14:17:00'),
    ('WEB-0009', 'James Walker', 'james.walker@urbaniarealestate.com', 'Urbania Real Estate', 'United Kingdom', 'English', 'Machine Learning', '2026-09-14 18:17:00'),
    ('WEB-0010', 'Camille Petit', 'camille.petit@alpinebank.com', 'Alpine Bank', 'France', 'French', 'Cloud Platforms', '2026-09-16 10:29:00'),
    ('WEB-0011', 'Laia Roca', 'laia.roca@rheinautomotive.com', 'Rhein Automotive', 'Spain', 'Catalan', 'Cloud Platforms', '2026-09-04 11:52:00'),
    ('WEB-0012', 'Marta Romero', 'marta.romero@nordicfoods', 'Nordic Foods', 'Spain', 'Spanish', 'Machine Learning', '2026-09-14 17:56:00'),
    ('WEB-0013', 'Manon Laurent', 'manon.laurent@greenfarmcoop.com', 'GreenFarm Coop', 'France', 'French', 'BI & Analytics', '2026-09-30 10:16:00'),
    ('WEB-0014', 'Elena Torres', 'elena.torres@technova.com', 'TechNova', 'Spain', 'Spanish', 'Cloud Platforms', '2026-09-26 13:14:00'),
    ('WEB-0015', 'Sofia Santos', 'sofia.santos@lusitaniaseguros.com', 'Lusitania Seguros', 'Portugal', 'Portuguese', 'BI & Analytics', '2026-09-04 09:09:00'),
    ('WEB-0016', 'George Taylor', 'george.taylor@vertexinsurance.com', 'Vertex Insurance', 'United Kingdom', 'English', 'Cloud Platforms', '2026-09-25 17:29:00'),
    ('WEB-0017', 'Oliver Taylor', 'oliver.taylor@greenfarmcoop.com', 'GreenFarm Coop', 'United Kingdom', 'English', 'Data Governance', '2026-10-05 12:49:00'),
    ('WEB-0018', 'Harry Hughes', 'harry.hughes@iberialogistics.com', 'Iberia Logistics', 'United Kingdom', 'English', 'Data Engineering', '2026-09-30 08:46:00'),
    ('WEB-0019', 'Felix Schmidt', 'felix.schmidt@rheinautomotive.com', 'Rhein Automotive', 'Germany', 'German', 'Machine Learning', '2026-10-11 12:53:00'),
    ('WEB-0020', 'Amelia Brown', 'amelia.brown@urbaniarealestate.com', 'Urbania Real Estate', 'United Kingdom', 'English', 'Data Governance', '2026-09-11 16:49:00'),
    ('WEB-0021', 'Mariana Almeida', 'mariana.almeida@acmeretail.com', 'Acme Retail', 'Portugal', 'Portuguese', 'Data Engineering', '2026-09-08 13:56:00'),
    ('WEB-0022', 'Inês Silva', 'ines.silva@bluewaveenergy.com', 'BlueWave Energy', 'Portugal', 'Portuguese', 'Machine Learning', '2026-10-07 09:05:00'),
    ('WEB-0023', 'Hugo Petit', 'hugo.petit@greenfarmcoop.com', 'GreenFarm Coop', 'France', 'French', 'Data Engineering', '2026-10-01 16:10:00'),
    ('WEB-0024', 'Marta Sánchez', 'marta.sanchez@alpinebank.com', 'Alpine Bank', 'Spain', 'Spanish', 'Data Governance', '2026-09-13 19:19:00'),
    ('WEB-0025', 'Mireia Bosch', 'mireia.bosch@alpinebank.com', 'Alpine Bank', 'Spain', 'Catalan', 'Cloud Platforms', '2026-09-29 09:15:00'),
    ('WEB-0026', 'Lucía Sánchez', 'lucia.sanchez@technova.com', 'TechNova', 'Spain', 'Spanish', 'Machine Learning', '2026-09-15 08:04:00'),
    ('WEB-0027', 'Léa Bernard', 'lea.bernard@acmeretail.com', 'Acme Retail', 'France', 'French', 'Data Engineering', '2026-09-22 09:32:00'),
    ('WEB-0028', 'Diego Sánchez', 'diego.sanchez@alpinebank.com', 'Alpine Bank', 'Spain', 'Spanish', 'Cloud Platforms', '2026-09-09 19:59:00'),
    ('WEB-0029', 'Lea Weber', 'lea.weber@lusitaniaseguros.com', 'Lusitania Seguros', 'Germany', 'German', 'Data Governance', '2026-10-01 14:12:00'),
    ('WEB-0030', 'Marta Navarro', 'marta.navarro@vertexinsurance.com', 'Vertex Insurance', 'Spain', 'Spanish', 'Cloud Platforms', '2026-09-27 15:55:00'),
    ('WEB-0031', 'Camille Martin', 'camille.martin@vertexinsurance.com', 'Vertex Insurance', 'France', 'French', 'Cloud Platforms', '2026-09-22 09:15:00'),
    ('WEB-0032', 'Diego Martínez', 'diego.martinez@vertexinsurance.com', 'Vertex Insurance', 'Spain', 'Spanish', 'Data Governance', '2026-09-12 12:29:00'),
    ('WEB-0033', 'Diego López', 'diego.lopez@acmeretail.com', 'Acme Retail', 'Spain', 'Spanish', 'Data Engineering', '2026-10-05 08:05:00'),
    ('WEB-0034', 'Tiago Rodrigues', 'tiago.rodrigues@mediterraneahoteles.com', 'Mediterránea Hoteles', 'Portugal', 'Portuguese', 'BI & Analytics', '2026-10-01 11:55:00'),
    ('WEB-0035', 'Pau Serra', 'pau.serra@acmeretail.com', 'Acme Retail', 'Spain', 'Catalan', 'Data Engineering', '2026-09-25 12:59:00'),
    ('WEB-0036', 'Jules Laurent', 'jules.laurent@atlastelecom.com', 'Atlas Telecom', 'France', 'French', 'Generative AI', '2026-10-06 18:45:00'),
    ('WEB-0037', 'Harry Wilson', 'harry.wilson@acmeretail.com', 'Acme Retail', 'United Kingdom', 'English', 'BI & Analytics', '2026-10-08 19:34:00'),
    ('WEB-0038', 'Lucía García', 'lucia.garcia@technova.com', 'TechNova', 'Spain', 'Spanish', 'Machine Learning', '2026-10-01 16:58:00'),
    ('WEB-0039', 'Lukas Schmidt', 'lukas.schmidt@rheinautomotive.com', 'Rhein Automotive', 'Germany', 'German', 'BI & Analytics', '2026-09-12 09:38:00'),
    ('WEB-0040', 'Marta López', 'marta.lopez@technova.com', 'TechNova', 'Spain', 'Spanish', 'BI & Analytics', '2026-09-16 17:38:00');

-- ----------------------------------------------------------------------------------------
-- leads_linkedin  (35 rows) - Leads from LinkedIn Lead Gen campaigns
-- ----------------------------------------------------------------------------------------

CREATE TABLE public.leads_linkedin (
    linkedin_lead_id  BIGINT NOT NULL,
    first_name        TEXT,
    last_name         TEXT,
    email_address     TEXT,
    company_name      TEXT,
    job_title         TEXT,
    country_code      TEXT,
    lang              TEXT,
    campaign_topic    TEXT,
    created_ts        TIMESTAMP,
    PRIMARY KEY (linkedin_lead_id)
);
COMMENT ON TABLE public.leads_linkedin IS 'Leads from LinkedIn Lead Gen campaigns';

INSERT INTO public.leads_linkedin (linkedin_lead_id, first_name, last_name, email_address, company_name, job_title, country_code, lang, campaign_topic, created_ts) VALUES
    (90001, 'Javier', 'Gil', 'javier.gil@vertexinsurance.com', 'Vertex Insurance', 'CTO', 'ES', 'es_ES', 'GENAI', '2026-10-02 19:24:00'),
    (90002, 'James', 'Smith', 'james.smith@lusitaniaseguros.com', 'Lusitania Seguros', 'Head of Data', 'GB', 'en_GB', 'BI', '2026-10-04 14:14:00'),
    (90003, 'Lucía', 'Sánchez', 'lucia.sanchez@atlastelecom.com', 'Alpine Bank', 'CTO', 'ES', 'es_ES', 'CLOUD', '2026-10-09 09:29:00'),
    (90004, 'Sergio', 'Gil', 'sergio.gil@technova.com', 'TechNova', 'IT Director', 'ES', 'es_ES', 'GENAI', '2026-10-06 16:28:00'),
    (90005, 'Lea', 'Koch', 'lea.koch@helixpharma.com', 'Helix Pharma', 'CTO', 'DE', 'de_DE', 'CLOUD', '2026-10-06 18:17:00'),
    (90006, 'Manon', 'Durand', 'manon.durand@helixpharma.com', 'Helix Pharma', 'Head of Innovation', 'FR', 'fr_FR', 'GOV', '2026-09-12 19:18:00'),
    (90007, 'Sergio', 'López', 'sergio.lopez@iberialogistics.com', 'Iberia Logistics', 'BI Manager', 'ES', 'es_ES', 'ML', '2026-09-17 14:44:00'),
    (90008, 'Javier', 'Torres', 'javier.torres@vertexinsurance.com', 'Vertex Insurance', 'Analytics Lead', 'ES', 'es_ES', 'BI', '2026-09-27 15:26:00'),
    (90009, 'Marta', 'García', 'marta.garcia@rheinautomotive.com', 'Rhein Automotive', 'IT Director', 'ES', 'es_ES', 'GENAI', '2026-09-25 08:22:00'),
    (90010, 'Marta', 'Sánchez', 'marta.sanchez@mediterraneahoteles.com', 'Mediterránea Hoteles', 'CTO', 'ES', 'es_ES', 'GENAI', '2026-09-18 14:31:00'),
    (90011, 'Marta', 'Martínez', 'marta.martinez@rheinautomotive.com', 'Rhein Automotive', 'Head of Innovation', 'ES', 'es_ES', 'ML', '2026-10-09 10:39:00'),
    (90012, 'George', 'Brown', 'george.brown@rheinautomotive.com', 'Rhein Automotive', 'Head of Innovation', 'GB', 'en_GB', 'GENAI', '2026-09-15 08:16:00'),
    (90013, 'Gemma', 'Roca', 'gemma.roca@urbaniarealestate.com', 'Urbania Real Estate', 'IT Director', 'ES', 'ca_ES', 'BI', '2026-09-18 14:16:00'),
    (90014, 'Lukas', 'Müller', 'lukas.muller@urbaniarealestate.com', 'Urbania Real Estate', 'CTO', 'DE', 'de_DE', 'GENAI', '2026-09-30 09:49:00'),
    (90015, 'João', 'Pereira', 'joao.pereira@bluewaveenergy.com', 'BlueWave Energy', 'CDO', 'PT', 'pt_PT', 'DE', '2026-09-29 10:15:00'),
    (90016, 'Javier', 'Sánchez', 'javier.sanchez@mediterraneahoteles.com', 'Mediterránea Hoteles', 'Data Engineer', 'ES', 'es_ES', 'CLOUD', '2026-10-04 13:10:00'),
    (90017, 'Charlotte', 'Brown', 'charlotte.brown@helixpharma.com', 'Helix Pharma', 'Head of Data', 'GB', 'en_GB', 'CLOUD', '2026-09-28 08:59:00'),
    (90018, 'Arnau', 'Serra', 'arnau.serra@atlastelecom.com', 'Atlas Telecom', 'CTO', 'ES', 'ca_ES', 'CLOUD', '2026-09-12 17:44:00'),
    (90019, 'Hannah', 'Wagner', 'hannah.wagner@rheinautomotive.com', 'Rhein Automotive', 'Head of Data', 'DE', 'de_DE', 'BI', '2026-10-05 17:50:00'),
    (90020, 'Marta', 'Navarro', 'marta.navarro@nordicfoods.com', 'Nordic Foods', 'Analytics Lead', 'ES', 'es_ES', 'GOV', '2026-09-10 14:52:00'),
    (90021, 'Isla', 'Wright', 'isla.wright@atlastelecom.com', 'Atlas Telecom', 'BI Manager', 'GB', 'en_GB', 'GENAI', '2026-09-23 10:46:00'),
    (90022, 'Harry', 'Wright', 'harry.wright@mediterraneahoteles.com', 'Mediterránea Hoteles', 'IT Director', 'GB', 'en_GB', 'CLOUD', '2026-10-06 19:37:00'),
    (90023, 'Javier', 'Romero', 'javier.romero@mediterraneahoteles.com', 'Mediterránea Hoteles', 'CTO', 'ES', 'es_ES', 'BI', '2026-10-04 15:36:00'),
    (90024, 'Isla', 'Smith', 'isla.smith@mediterraneahoteles.com', 'Mediterránea Hoteles', 'Analytics Lead', 'GB', 'en_GB', 'GENAI', '2026-09-15 15:13:00'),
    (90025, 'Mireia', 'Casals', 'mireia.casals@technova.com', 'TechNova', 'Data Engineer', 'ES', 'ca_ES', 'ML', '2026-09-27 08:33:00'),
    (90026, 'Inês', 'Rodrigues', 'ines.rodrigues@mediterraneahoteles.com', 'Mediterránea Hoteles', 'CTO', 'PT', 'pt_PT', 'DE', '2026-10-02 15:41:00'),
    (90027, 'Louis', 'Bernard', 'louis.bernard@helixpharma.com', 'Helix Pharma', 'CTO', 'FR', 'fr_FR', 'GENAI', '2026-09-22 19:15:00'),
    (90028, 'Mireia', 'Serra', 'mireia.serra@atlastelecom.com', 'Atlas Telecom', 'Analytics Lead', 'ES', 'ca_ES', 'GOV', '2026-09-21 19:29:00'),
    (90029, 'Álvaro', 'López', 'alvaro.lopez@atlastelecom.com', 'Atlas Telecom', 'CTO', 'ES', 'es_ES', 'ML', '2026-09-20 09:47:00'),
    (90030, 'James', 'Wilson', 'james.wilson@bluewaveenergy.com', 'BlueWave Energy', 'Head of Innovation', 'GB', 'en_GB', 'CLOUD', '2026-09-18 19:37:00'),
    (90031, 'Rui', 'Santos', 'rui.santos@rheinautomotive.com', 'Rhein Automotive', 'CTO', 'PT', 'pt_PT', 'GOV', '2026-09-19 11:23:00'),
    (90032, 'Carmen', 'Romero', 'carmen.romero@acmeretail.com', 'Acme Retail', 'CDO', 'ES', 'es_ES', 'DE', '2026-09-27 12:44:00'),
    (90033, 'Sofia', 'Santos', 'sofia.santos@rheinautomotive.com', 'Rhein Automotive', 'CDO', 'PT', 'pt_PT', 'CLOUD', '2026-09-28 12:30:00'),
    (90034, 'James', 'Smith', 'james.smith@helixpharma.com', 'Helix Pharma', 'Head of Innovation', 'GB', 'en_GB', 'ML', '2026-09-13 09:25:00'),
    (90035, 'Oliver', 'Brown', 'oliver.brown@iberialogistics.com', 'Iberia Logistics', 'Data Engineer', 'GB', 'en_GB', 'GOV', '2026-09-12 11:07:00');

-- ----------------------------------------------------------------------------------------
-- sales_people  (9 rows) - Sales people: languages and specialties as ';'-separated lists
-- ----------------------------------------------------------------------------------------

CREATE TABLE public.sales_people (
    seller_id       TEXT NOT NULL,
    full_name       TEXT,
    email           TEXT,
    languages       TEXT,
    specialties     TEXT,
    max_open_leads  BIGINT,
    active          TEXT,
    PRIMARY KEY (seller_id)
);
COMMENT ON TABLE public.sales_people IS 'Sales people: languages and specialties as '';''-separated lists';

INSERT INTO public.sales_people (seller_id, full_name, email, languages, specialties, max_open_leads, active) VALUES
    ('S01', 'Laura Martí', 'laura.marti@prenomics-demo.com', 'es;ca;en', 'data_engineering;data_governance', 15, 'Yes'),
    ('S02', 'Marc Puig', 'marc.puig@prenomics-demo.com', 'ca;es', 'bi_analytics;cloud_platforms', 12, 'Yes'),
    ('S03', 'Sophie Dubois', 'sophie.dubois@prenomics-demo.com', 'fr;en', 'machine_learning;genai', 12, 'Yes'),
    ('S04', 'Jonas Weber', 'jonas.weber@prenomics-demo.com', 'de;en', 'data_engineering;cloud_platforms', 10, 'Yes'),
    ('S05', 'Ana Costa', 'ana.costa@prenomics-demo.com', 'pt;es;en', 'bi_analytics;data_governance', 10, 'Yes'),
    ('S06', 'Pablo Ruiz', 'pablo.ruiz@prenomics-demo.com', 'es;en', 'genai;machine_learning', 15, 'Yes'),
    ('S07', 'Emma Clarke', 'emma.clarke@prenomics-demo.com', 'en', 'bi_analytics;genai;data_engineering', 14, 'Yes'),
    ('S08', 'Carla Ferrer', 'carla.ferrer@prenomics-demo.com', 'ca;es;fr', 'machine_learning;data_governance', 6, 'No'),
    ('S09', 'Thomas Lefèvre', 'thomas.lefevre@prenomics-demo.com', 'fr;de;en', 'data_engineering;bi_analytics;cloud_platforms', 10, 'Yes');

COMMIT;


-- Sanity check ------------------------------------------------------------------------------

SELECT 'leads_web_form' AS table_name, count(*) AS n_rows FROM public.leads_web_form
UNION ALL SELECT 'leads_linkedin',   count(*) FROM public.leads_linkedin
UNION ALL SELECT 'sales_people',     count(*) FROM public.sales_people;
