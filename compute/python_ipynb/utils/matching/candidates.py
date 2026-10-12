"""Candidate selection: which sellers can take a given lead."""

import pandas as pd

FULL_MATCH = "full_match"          # speaks the language AND is specialized in the content
LANGUAGE_ONLY = "language_only"    # speaks the language, but no specialist available
UNASSIGNED = "unassigned"          # nobody speaks the language, or everybody is full


def candidate_tiers(language: str, content: str, sellers: pd.DataFrame) -> list:
    """Return the candidate sellers for a lead as [(match_type, sellers_df), ...]
    in order of preference: specialists first, then anyone speaking the language."""
    speaks = sellers["languages"].map(lambda langs: language in langs)
    specialist = sellers["specialties"].map(lambda specs: content in specs)
    return [
        (FULL_MATCH, sellers[speaks & specialist]),
        (LANGUAGE_ONLY, sellers[speaks & ~specialist]),
    ]


def pick_least_loaded(candidates: pd.DataFrame, load: dict) -> str:
    """Pick the candidate with the lowest load ratio (open leads / capacity) that
    still has free capacity. Ties are broken by seller_id. Returns None if all are full."""
    best_id, best_ratio = None, None
    for seller in candidates.itertuples():
        open_leads = load.get(seller.seller_id, 0)
        if open_leads >= seller.max_open_leads:
            continue
        ratio = open_leads / seller.max_open_leads
        if best_ratio is None or ratio < best_ratio:  # candidates are sorted by seller_id
            best_id, best_ratio = seller.seller_id, ratio
    return best_id
