"""Normalization of the raw sales people table."""

import pandas as pd

# Raw Excel headers -> normalized names
SELLER_COLUMNS = {"Seller ID": "seller_id", "Full Name": "full_name", "Email": "email",
                  "Languages": "languages", "Specialties": "specialties",
                  "Max Open Leads": "max_open_leads", "Active": "active"}


def split_list(value) -> frozenset:
    """'es; CA ;en' -> frozenset({'es', 'ca', 'en'}). Empty/NULL -> empty set."""
    if value is None or pd.isna(value):
        return frozenset()
    return frozenset(v.strip().lower() for v in str(value).split(";") if v.strip())


def normalize_sellers(raw: pd.DataFrame, only_active: bool = True) -> pd.DataFrame:
    """Rename columns, parse ';'-separated lists into sets and cast types.

    Returns one row per seller with columns:
        seller_id, full_name, email, languages (set), specialties (set),
        max_open_leads (int), is_active (bool)
    """
    sellers = raw.rename(columns=SELLER_COLUMNS)[list(SELLER_COLUMNS.values())].copy()
    sellers["languages"] = sellers["languages"].map(split_list)
    sellers["specialties"] = sellers["specialties"].map(split_list)
    sellers["max_open_leads"] = pd.to_numeric(sellers["max_open_leads"], errors="coerce").fillna(0).astype(int)
    sellers["is_active"] = sellers.pop("active").astype(str).str.strip().str.lower().eq("yes")
    if only_active:
        sellers = sellers[sellers["is_active"]]
    return sellers.sort_values("seller_id").reset_index(drop=True)
