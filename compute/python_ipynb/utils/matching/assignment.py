"""Lead -> seller assignment algorithm (pure pandas, no database access)."""

from datetime import datetime

import pandas as pd

from .candidates import FULL_MATCH, LANGUAGE_ONLY, UNASSIGNED, candidate_tiers, pick_least_loaded

OUTPUT_COLUMNS = ["lead_id", "seller_id", "match_type", "reason",
                  "preferred_language", "content_of_interest", "assigned_at", "run_id"]


def current_load(existing_assignments: pd.DataFrame) -> dict:
    """{seller_id: number of leads already assigned} from previous runs."""
    if existing_assignments is None or existing_assignments.empty:
        return {}
    return existing_assignments["seller_id"].dropna().value_counts().to_dict()


def assign_leads(leads: pd.DataFrame, sellers: pd.DataFrame, load: dict = None,
                 run_id: str = None) -> pd.DataFrame:
    """Assign each lead to one seller.

    Rules, applied lead by lead in order of arrival (created_at):
      1. Prefer active sellers speaking the lead's language and specialized in
         its content (full_match); otherwise any seller speaking the language
         (language_only); otherwise the lead stays unassigned.
      2. Within a tier, pick the seller with the lowest load ratio that still has
         capacity (max_open_leads). If the whole tier is full, try the next one.

    Args:
        leads:   normalized leads (lead_id, preferred_language, content_of_interest, created_at).
        sellers: output of normalize_sellers().
        load:    {seller_id: open leads} before this run; updated as leads are assigned.
        run_id:  identifier stored with every row (defaults to the current timestamp).
    """
    load = dict(load or {})
    assigned_at = datetime.now().replace(microsecond=0)
    run_id = run_id or assigned_at.strftime("%Y%m%d%H%M%S")

    rows = []
    for lead in leads.sort_values(["created_at", "lead_id"]).itertuples():
        tiers = candidate_tiers(lead.preferred_language, lead.content_of_interest, sellers)
        n_candidates = sum(len(candidates) for _, candidates in tiers)

        seller_id, match_type = None, UNASSIGNED
        for tier_type, candidates in tiers:
            seller_id = pick_least_loaded(candidates, load)
            if seller_id is not None:
                match_type = tier_type
                load[seller_id] = load.get(seller_id, 0) + 1
                break

        if n_candidates == 0:
            reason = f"no active seller speaks '{lead.preferred_language}'"
        elif match_type == UNASSIGNED:
            reason = f"all {n_candidates} candidate sellers are at full capacity"
        elif match_type == LANGUAGE_ONLY and pd.isna(lead.content_of_interest):
            reason = "lead has no valid content_of_interest"
        elif match_type == LANGUAGE_ONLY:
            reason = f"no available specialist in '{lead.content_of_interest}'"
        else:
            reason = None

        rows.append({
            "lead_id": lead.lead_id,
            "seller_id": seller_id,
            "match_type": match_type,
            "reason": reason,
            "preferred_language": lead.preferred_language,
            "content_of_interest": lead.content_of_interest,
            "assigned_at": assigned_at,
            "run_id": run_id,
        })

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def summarize(assignments: pd.DataFrame) -> pd.DataFrame:
    """Leads per seller and match type, handy to print after a run."""
    return (assignments
            .assign(seller_id=assignments["seller_id"].fillna("-"))
            .pivot_table(index="seller_id", columns="match_type", values="lead_id",
                         aggfunc="count", fill_value=0)
            .reindex(columns=[FULL_MATCH, LANGUAGE_ONLY, UNASSIGNED], fill_value=0))
