"""
Generate the demo reference Excels (leads from 3 sources + sales people).

Each lead source deliberately uses its own column names and value formats,
so the SQL step has something real to normalize:

    leads_web_form.xlsx   -> English headers with spaces, language as English name,
                             interest as a dropdown label.
    leads_trade_fair.xlsx -> Spanish headers, language as ISO code (messy casing),
                             interest as a Spanish label.
    leads_trade_fair_2.xlsx -> same format, different leads from another trade fair
                             (ids continue after the first file, so both can share a table).
    leads_linkedin.xlsx   -> snake_case headers, language as locale (es_ES),
                             interest as a campaign code.
    sales_people.xlsx     -> one row per seller, languages / specialties as ';' lists.

A few data-quality issues are injected on purpose (see INJECTED_ISSUES) so the
validation script (python_ipynb/basic_transf.py) has something to report.

Usage:
    python generate_reference_data.py            # writes the trade-fair .xlsx files next to this script
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent

# Canonical values (the SQL step maps every source format to these)
LANGUAGES = ["es", "ca", "en", "fr", "de", "pt"]
CONTENTS = ["data_engineering", "bi_analytics", "machine_learning",
            "genai", "data_governance", "cloud_platforms"]

# Source-specific representations of the canonical values
WEB_LANGUAGE = {"es": "Spanish", "ca": "Catalan", "en": "English",
                "fr": "French", "de": "German", "pt": "Portuguese"}
WEB_CONTENT = {"data_engineering": "Data Engineering", "bi_analytics": "BI & Analytics",
               "machine_learning": "Machine Learning", "genai": "Generative AI",
               "data_governance": "Data Governance", "cloud_platforms": "Cloud Platforms"}

FAIR_LANGUAGE = {"es": "es", "ca": "CA", "en": "en ", "fr": "Fr", "de": "de", "pt": "pt"}
FAIR_CONTENT = {"data_engineering": "Ingeniería de datos", "bi_analytics": "BI y analítica",
                "machine_learning": "Machine learning", "genai": "IA generativa",
                "data_governance": "Gobierno del dato", "cloud_platforms": "Cloud"}

LINKEDIN_LANGUAGE = {"es": "es_ES", "ca": "ca_ES", "en": "en_GB",
                     "fr": "fr_FR", "de": "de_DE", "pt": "pt_PT"}
LINKEDIN_CONTENT = {"data_engineering": "DE", "bi_analytics": "BI", "machine_learning": "ML",
                    "genai": "GENAI", "data_governance": "GOV", "cloud_platforms": "CLOUD"}

# Names and countries per language, so leads look coherent
PEOPLE = {
    "es": (["Lucía", "Javier", "Carmen", "Álvaro", "Elena", "Sergio", "Marta", "Diego"],
           ["García", "López", "Martínez", "Sánchez", "Romero", "Navarro", "Torres", "Gil"], "Spain"),
    "ca": (["Jordi", "Montse", "Pau", "Laia", "Oriol", "Mireia", "Arnau", "Gemma"],
           ["Puig", "Soler", "Vila", "Font", "Casals", "Roca", "Serra", "Bosch"], "Spain"),
    "en": (["Oliver", "Charlotte", "James", "Amelia", "Harry", "Isla", "George", "Grace"],
           ["Smith", "Taylor", "Brown", "Wilson", "Evans", "Walker", "Hughes", "Wright"], "United Kingdom"),
    "fr": (["Louis", "Camille", "Hugo", "Léa", "Jules", "Chloé", "Arthur", "Manon"],
           ["Martin", "Bernard", "Petit", "Durand", "Leroy", "Moreau", "Laurent", "Girard"], "France"),
    "de": (["Lukas", "Hannah", "Felix", "Lena", "Paul", "Mia", "Jonas", "Lea"],
           ["Müller", "Schmidt", "Fischer", "Weber", "Wagner", "Becker", "Hoffmann", "Koch"], "Germany"),
    "pt": (["João", "Beatriz", "Tiago", "Inês", "Rui", "Mariana", "Pedro", "Sofia"],
           ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Almeida"], "Portugal"),
}
COMPANIES = ["Acme Retail", "Nordic Foods", "Iberia Logistics", "BlueWave Energy", "Helix Pharma",
             "Urbania Real Estate", "Vertex Insurance", "Mediterránea Hoteles", "Alpine Bank",
             "TechNova", "GreenFarm Coop", "Atlas Telecom", "Lusitania Seguros", "Rhein Automotive"]
JOB_TITLES = ["CDO", "Head of Data", "BI Manager", "CTO", "Data Engineer",
              "Analytics Lead", "IT Director", "Head of Innovation"]
FAIRS = ["Big Data & AI World Madrid", "Barcelona Digital Talent", "Data Innovation Summit"]
FAIRS_2 = ["Valencia Data & Cloud Expo"]   # the second trade-fair file comes from another fair

# Language weights: most leads speak es/en/ca, a few the rest
LANG_WEIGHTS = [0.30, 0.15, 0.25, 0.12, 0.10, 0.08]

INJECTED_ISSUES = """
- leads_web_form    WEB-0007: missing e-mail
- leads_web_form    WEB-0012: malformed e-mail (no domain TLD)
- leads_trade_fair  FAIR-005: language 'it' (no seller speaks Italian)
- leads_trade_fair  FAIR-011: interest 'Blockchain' (not a content we offer)
- leads_linkedin    LI-90003: same person/e-mail as WEB-0003 (cross-source duplicate)
- sales_people      S08     : inactive seller (must never get leads)
"""


def _strip_accents(text: str) -> str:
    """ASCII-ish version of a name for building e-mail addresses."""
    table = str.maketrans("áàäâãéèëêíìïîóòöôõúùüûçñÁÉÍÓÚÜÑÇ", "aaaaaeeeeiiiiooooouuuucnAEIOUUNC")
    return text.translate(table)


_USED_EMAILS = set()  # avoid accidental duplicates: the only duplicate must be the injected one


def _person(rng: random.Random, lang: str) -> dict:
    first_names, last_names, country = PEOPLE[lang]
    while True:
        first, last = rng.choice(first_names), rng.choice(last_names)
        company = rng.choice(COMPANIES)
        domain = _strip_accents(company).lower().replace(" ", "") + ".com"
        email = f"{_strip_accents(first).lower()}.{_strip_accents(last).lower()}@{domain}"
        if email not in _USED_EMAILS:
            _USED_EMAILS.add(email)
            return {"first": first, "last": last, "company": company, "email": email, "country": country}


def _random_ts(rng: random.Random, start: datetime, days: int) -> datetime:
    return start + timedelta(days=rng.randint(0, days), hours=rng.randint(8, 19),
                             minutes=rng.randint(0, 59))


def build_web_form(rng: random.Random, n: int = 40) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        lang = rng.choices(LANGUAGES, LANG_WEIGHTS)[0]
        content = rng.choice(CONTENTS)
        p = _person(rng, lang)
        rows.append({
            "Lead ID": f"WEB-{i:04d}",
            "Full Name": f"{p['first']} {p['last']}",
            "E-mail": p["email"],
            "Company": p["company"],
            "Country": p["country"],
            "Preferred Language": WEB_LANGUAGE[lang],
            "Interest": WEB_CONTENT[content],
            "Submitted At": _random_ts(rng, datetime(2026, 9, 1), 40),
        })
    df = pd.DataFrame(rows)
    df.loc[df["Lead ID"] == "WEB-0007", "E-mail"] = None
    bad = df["Lead ID"] == "WEB-0012"
    df.loc[bad, "E-mail"] = df.loc[bad, "E-mail"].str.replace(".com", "", regex=False)
    return df


def build_trade_fair(rng: random.Random, n: int = 25, first_id: int = 1, fairs: list = FAIRS,
                     start: datetime = datetime(2026, 9, 15), days: int = 20,
                     inject_issues: bool = True) -> pd.DataFrame:
    rows = []
    for i in range(first_id, first_id + n):
        lang = rng.choices(LANGUAGES, LANG_WEIGHTS)[0]
        content = rng.choice(CONTENTS)
        p = _person(rng, lang)
        rows.append({
            "id_contacto": f"FAIR-{i:03d}",
            "nombre": p["first"],
            "apellidos": p["last"],
            "correo": p["email"].upper() if i % 4 == 0 else p["email"],  # messy casing
            "empresa": p["company"],
            "pais": p["country"],
            "idioma": FAIR_LANGUAGE[lang],
            "tema_interes": FAIR_CONTENT[content],
            "feria": rng.choice(fairs),
            "fecha_contacto": _random_ts(rng, start, days).date(),
        })
    df = pd.DataFrame(rows)
    if inject_issues:
        df.loc[df["id_contacto"] == "FAIR-005", "idioma"] = "it"
        df.loc[df["id_contacto"] == "FAIR-011", "tema_interes"] = "Blockchain"
    return df


def build_linkedin(rng: random.Random, web_form: pd.DataFrame, n: int = 35) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        lang = rng.choices(LANGUAGES, LANG_WEIGHTS)[0]
        content = rng.choice(CONTENTS)
        p = _person(rng, lang)
        rows.append({
            "linkedin_lead_id": 90000 + i,
            "first_name": p["first"],
            "last_name": p["last"],
            "email_address": p["email"],
            "company_name": p["company"],
            "job_title": rng.choice(JOB_TITLES),
            "country_code": {"Spain": "ES", "United Kingdom": "GB", "France": "FR",
                             "Germany": "DE", "Portugal": "PT"}[p["country"]],
            "lang": LINKEDIN_LANGUAGE[lang],
            "campaign_topic": LINKEDIN_CONTENT[content],
            "created_ts": _random_ts(rng, datetime(2026, 9, 10), 30),
        })
    df = pd.DataFrame(rows)

    # Cross-source duplicate: LI-90003 is the same person as WEB-0003
    dup = web_form.loc[web_form["Lead ID"] == "WEB-0003"].iloc[0]
    first, last = dup["Full Name"].split(" ", 1)
    df.loc[df["linkedin_lead_id"] == 90003, ["first_name", "last_name", "email_address"]] = \
        [first, last, dup["E-mail"]]
    return df


def build_sales_people() -> pd.DataFrame:
    rows = [
        ("S01", "Laura Martí",    "es;ca;en", "data_engineering;data_governance", 15, "Yes"),
        ("S02", "Marc Puig",      "ca;es",    "bi_analytics;cloud_platforms",      12, "Yes"),
        ("S03", "Sophie Dubois",  "fr;en",    "machine_learning;genai",            12, "Yes"),
        ("S04", "Jonas Weber",    "de;en",    "data_engineering;cloud_platforms",  10, "Yes"),
        ("S05", "Ana Costa",      "pt;es;en", "bi_analytics;data_governance",      10, "Yes"),
        ("S06", "Pablo Ruiz",     "es;en",    "genai;machine_learning",           15, "Yes"),
        ("S07", "Emma Clarke",    "en",       "bi_analytics;genai;data_engineering", 14, "Yes"),
        ("S08", "Carla Ferrer",   "ca;es;fr", "machine_learning;data_governance",  6, "No"),
        ("S09", "Thomas Lefèvre", "fr;de;en", "data_engineering;bi_analytics;cloud_platforms", 10, "Yes"),
    ]
    df = pd.DataFrame(rows, columns=["Seller ID", "Full Name", "Languages", "Specialties",
                                     "Max Open Leads", "Active"])
    df.insert(2, "Email", df["Full Name"].map(
        lambda n: _strip_accents(n).lower().replace(" ", ".") + "@prenomics-demo.com"))
    return df


# Only the trade-fair leads have an Excel origin; the other datasets live in the Postgres
# origin (create_reference_data.sql). They are still built here, in the same order, so the
# random draws stay the same and the cross-source duplicate keeps pointing to WEB-0003.
EXCEL_FILES = {"leads_trade_fair.xlsx", "leads_trade_fair_2.xlsx"}


def generate(output_dir: Path = OUTPUT_DIR, seed: int = SEED) -> dict:
    """Build all reference datasets and write the Excel-origin ones (EXCEL_FILES) as .xlsx.
    Returns {file_name: DataFrame} with every dataset."""
    rng = random.Random(seed)
    _USED_EMAILS.clear()
    web = build_web_form(rng)
    datasets = {
        "leads_web_form.xlsx": web,
        "leads_trade_fair.xlsx": build_trade_fair(rng),
        "leads_linkedin.xlsx": build_linkedin(rng, web),
        "sales_people.xlsx": build_sales_people(),
        # Built last so the random draws of the files above do not change
        "leads_trade_fair_2.xlsx": build_trade_fair(rng, n=20, first_id=26, fairs=FAIRS_2,
                                                    start=datetime(2026, 10, 6), days=8,
                                                    inject_issues=False),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for file_name in sorted(EXCEL_FILES):
        df = datasets[file_name]
        df.to_excel(output_dir / file_name, index=False, sheet_name="data")
        print(f"{file_name:<24} {len(df):>3} rows")
    print("Injected data-quality issues:" + INJECTED_ISSUES)
    return datasets


if __name__ == "__main__":
    generate()
