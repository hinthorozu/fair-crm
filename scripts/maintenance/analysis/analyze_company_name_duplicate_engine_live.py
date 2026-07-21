#!/usr/bin/env python3
"""Read-only live validation of the shared Company Name Duplicate Engine.

Runs the same Admin Duplicate Customer Analysis path
(analyze_customer_groups_by_field + company_name fuzzy matching) against the
real CRM DB. Does not modify data or matching rules.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPORTS_DIR, bootstrap

bootstrap()

from sqlalchemy.orm import load_only

from app.db.session import SessionLocal
from app.modules.customers.application.customer_duplicate_eligibility import (
    exclude_merge_deleted_customers,
)
from app.modules.customers.application.customer_field_grouping import (
    analyze_customer_groups_by_field,
    grouping_keys_for_customer,
)
from app.modules.customers.application.duplicate_company_name_grouping import (
    _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX,
    _company_name_block_key,
    is_bare_brand_hub_bucket_key,
    merge_similar_company_name_buckets,
)
from app.modules.customers.infrastructure.persistence.models import CustomerModel
from app.modules.imports.domain.services.company_name_matcher import (
    MATCH_SCORE_MIN,
    MATCH_SCORE_POSSIBLE,
    MATCH_SCORE_STRONG,
    score_company_name_pair,
)
from app.modules.imports.domain.services.company_name_normalizer import (
    SECTOR_GENERIC_TOKENS,
    company_name_comparison_key,
    core_tokens,
    normalize_import_company_name,
    tokenize_company_name,
)

REQUIRED_SCENARIOS = [
    (
        "A_acarlar",
        "ACARLAR VAGON SAN. VE TİC. A.Ş.",
        "ACARLAR YAPI MALZEMELERİ PAZARLAMA TİCARET LTD ŞTİ",
        False,
    ),
    (
        "B_akm_alarm",
        "AKM ALARM KONTROL MERKEZİ LTD ŞTİ",
        "AKM ALARM KONTROL MERKEZİ A.Ş.",
        True,
    ),
    (
        "C_akm_distinct",
        "AKM GÜVENLİK SİSTEMLERİ A.Ş.",
        "AKM ALARM KONTROL MERKEZİ LTD.",
        False,
    ),
    (
        "D_anadolu_isuzu",
        "ANADOLU ISUZU",
        "Anadolu Isuzu Otomotiv Sanayii",
        True,
    ),
    (
        "E_global_gida",
        "GLOBAL GIDA",
        "GLOBAL GIDA PAZARLAMA DIS TICARET",
        True,
    ),
    (
        "F_teknik_kimya",
        "TEKNIK KIMYA DONATIM",
        "TEKNIK KIMYA DONATIM ENERJI",
        True,
    ),
    (
        "G_anadolu_sectors",
        "ANADOLU GIDA",
        "ANADOLU MAKINA",
        False,
    ),
    (
        "H_zhongshan_sector",
        "ZHONGSHAN ALFA ELECTRICAL APPLIANCE CO LTD",
        "ZHONGSHAN BETA ELECTRICAL EQUIPMENT CO LTD",
        False,
    ),
]


def _company_name(model: CustomerModel) -> str:
    if model.legal_name and model.legal_name.strip():
        return model.legal_name.strip()
    return (model.display_name or "").strip()


def _band(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= MATCH_SCORE_STRONG:
        return "95-100"
    if score >= MATCH_SCORE_POSSIBLE:
        return "85-94"
    if score >= MATCH_SCORE_MIN:
        return "70-84"
    return "below-70"


def _shared_core_tokens(names: list[str]) -> set[str]:
    token_sets: list[set[str]] = []
    for name in names:
        key = normalize_import_company_name(name)
        token_sets.append(set(core_tokens(tokenize_company_name(key))))
    if not token_sets:
        return set()
    shared = token_sets[0]
    for other in token_sets[1:]:
        shared &= other
    return shared


def _suspect_single_token_group(names: list[str]) -> bool:
    """True when group overlap is only one distinctive (non-sector) core token."""
    shared = _shared_core_tokens(names)
    distinctive = shared - SECTOR_GENERIC_TOKENS
    if len(distinctive) == 1 and len(shared) == 1:
        # Also require that at least two members have multi-token cores with different tails
        cores = []
        for name in names:
            key = normalize_import_company_name(name)
            cores.append(core_tokens(tokenize_company_name(key)))
        multi = [c for c in cores if len(c) >= 2]
        if len(multi) >= 2:
            tails = [set(c[1:]) for c in multi]
            # if no shared tail across multi-token members → suspicious
            shared_tail = tails[0]
            for t in tails[1:]:
                shared_tail &= t
            return len(shared_tail) == 0
    return False


def _pairwise_min_score(names: list[str]) -> tuple[int | None, list[tuple[str, str, int | None]]]:
    pairs: list[tuple[str, str, int | None]] = []
    scores: list[int] = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            scored = score_company_name_pair(left, right)
            conf = scored.confidence if scored else None
            pairs.append((left, right, conf))
            if conf is not None:
                scores.append(conf)
    return (min(scores) if scores else None), pairs


def _find_name_hits(models: list[CustomerModel], needle: str) -> list[CustomerModel]:
    needle_key = normalize_import_company_name(needle)
    hits = []
    for model in models:
        name = _company_name(model)
        key = company_name_comparison_key(
            display_name=model.display_name or "",
            legal_name=model.legal_name,
        )
        if needle_key and (needle_key in key or key == needle_key or needle.lower() in name.lower()):
            # Prefer exact comparison-key equality or strong containment of first tokens
            hits.append(model)
    # Prefer exact key match first
    exact = [
        m
        for m in hits
        if company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
        == needle_key
    ]
    if exact:
        return exact
    # Fallback: names containing the distinctive brand token
    brand = needle_key.split()[0] if needle_key else ""
    if brand:
        branded = [
            m
            for m in models
            if brand
            in company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name).split()
        ]
        return branded
    return hits


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    session = SessionLocal()
    try:
        org_ids = [
            row[0]
            for row in session.query(CustomerModel.organization_id)
            .filter(CustomerModel.deleted_at.is_(None))
            .distinct()
            .all()
        ]
        if not org_ids:
            print("No organizations with customers found.")
            return 1

        # Prefer largest org (most realistic CRM dataset)
        org_sizes = []
        for org_id in org_ids:
            count = (
                exclude_merge_deleted_customers(
                    session.query(CustomerModel).filter(CustomerModel.organization_id == org_id)
                ).count()
            )
            org_sizes.append((count, org_id))
        org_sizes.sort(reverse=True)
        total_customers_all = sum(c for c, _ in org_sizes)
        org_id = org_sizes[0][1]
        org_customer_count = org_sizes[0][0]

        print(f"Organizations: {len(org_ids)}; analyzing largest org={org_id} customers={org_customer_count}")
        print(f"All-org customer total (eligible): {total_customers_all}")

        # Confirm Admin path wiring
        print("\n=== Engine wiring check ===")
        print("grouping_keys_for_customer(company_name) -> company_name_comparison_key (import normalizer)")
        print("fuzzy merge -> score_company_name_pair / MATCH_SCORE_MIN")

        summary, member_rows = analyze_customer_groups_by_field(
            session,
            organization_id=org_id,
            group_by="company_name",
            company_name_fuzzy_matching=True,
        )

        models = (
            exclude_merge_deleted_customers(
                session.query(CustomerModel)
                .options(
                    load_only(
                        CustomerModel.id,
                        CustomerModel.display_name,
                        CustomerModel.legal_name,
                        CustomerModel.normalized_name,
                    )
                )
                .filter(CustomerModel.organization_id == org_id)
            )
            .all()
        )
        by_id = {m.id: m for m in models}

        # Problem C diagnostics: rebuild exact buckets + merge stats (read-only).
        exact_buckets: dict[str, dict] = defaultdict(dict)
        for model in models:
            for key in grouping_keys_for_customer("company_name", model, None):
                exact_buckets[key][model.id] = model

        first_token_block_sizes: Counter = Counter()
        for key in exact_buckets:
            if is_bare_brand_hub_bucket_key(key):
                continue
            block = _company_name_block_key(
                normalize_import_company_name(key.lower()) or key.lower()
            )
            first_token_block_sizes[block] += 1

        blocks_above_32 = {
            token: size
            for token, size in first_token_block_sizes.items()
            if size > _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX
        }
        merge_diag = merge_similar_company_name_buckets(dict(exact_buckets))
        merge_stats = merge_diag.stats
        old_skip_block_count = len(blocks_above_32)
        naive_pairs = merge_stats.theoretical_naive_pairs if merge_stats else 0
        candidates = merge_stats.candidate_pairs_generated if merge_stats else 0
        scored_pairs = merge_stats.pairs_scored if merge_stats else 0
        accepted_pairs = merge_stats.pairs_accepted if merge_stats else 0
        problem_c_perf = {
            "direct_pairwise_max": _COMPANY_NAME_SIMILARITY_DIRECT_PAIRWISE_MAX,
            "first_token_blocks_total": len(first_token_block_sizes),
            "blocks_above_32_count": old_skip_block_count,
            "blocks_above_32_sizes": dict(
                sorted(blocks_above_32.items(), key=lambda item: -item[1])[:30]
            ),
            "old_approach_would_skip_blocks": old_skip_block_count,
            "theoretical_naive_pairs": naive_pairs,
            "candidate_pairs_generated": candidates,
            "pairs_scored": scored_pairs,
            "pairs_accepted": accepted_pairs,
            "candidate_vs_naive_ratio": (
                round(candidates / naive_pairs, 4) if naive_pairs else None
            ),
            "scored_vs_naive_ratio": (
                round(scored_pairs / naive_pairs, 4) if naive_pairs else None
            ),
        }

        groups: dict[str, list] = defaultdict(list)
        for row in member_rows:
            groups[row.group_key].append(row)

        # Member-level confidence bands (exclude group_anchor 100 if we want edge view —
        # report both member scores and pairwise min within group)
        member_band_counts = Counter()
        group_band_counts = Counter()  # by max member score in group (excl None)
        group_min_band_counts = Counter()
        suspect_single_token: list[dict] = []
        short_hub_suspects: list[dict] = []
        sector_only_suspects: list[dict] = []
        transitive_only: list[dict] = []
        legal_form_exact_groups = 0
        group_details: list[dict] = []

        for group_key, rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
            members = [by_id[r.customer_id] for r in rows if r.customer_id in by_id]
            names = [_company_name(m) for m in members]
            keys = [
                company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
                for m in members
            ]
            scores = [r.match_score for r in rows]
            reasons = [r.duplicate_reason for r in rows]
            numeric_scores = [s for s in scores if isinstance(s, int)]
            max_score = max(numeric_scores) if numeric_scores else None
            min_score = min(numeric_scores) if numeric_scores else None
            max_band = _band(max_score)
            min_band = _band(min_score)
            if max_band:
                group_band_counts[max_band] += 1
            if min_band:
                group_min_band_counts[min_band] += 1
            for s in scores:
                b = _band(s)
                if b:
                    member_band_counts[b] += 1

            # Exact legal-form variants: all same comparison key
            if len(set(k for k in keys if k)) == 1:
                legal_form_exact_groups += 1

            pairwise_min, pairs = _pairwise_min_score(names)
            detail = {
                "group_key": group_key,
                "size": len(members),
                "names": names,
                "comparison_keys": keys,
                "member_scores": scores,
                "member_reasons": reasons,
                "max_score": max_score,
                "min_score": min_score,
                "pairwise_min_score": pairwise_min,
                "shared_core_tokens": sorted(_shared_core_tokens(names)),
            }
            group_details.append(detail)

            if any(r == "transitive_group_member" for r in reasons) or any(s is None for s in scores):
                transitive_only.append(detail)

            if _suspect_single_token_group(names):
                suspect_single_token.append(detail)

            # Short hub: any single-token short core in a multi-member group with longer names
            cores = [core_tokens(tokenize_company_name(k)) for k in keys]
            if any(len(c) == 1 and len(c[0]) <= 4 for c in cores if c) and any(len(c) > 1 for c in cores):
                short_hub_suspects.append(detail)

            shared = _shared_core_tokens(names)
            if shared and shared.issubset(SECTOR_GENERIC_TOKENS):
                sector_only_suspects.append(detail)

        # Scenario checks (engine + live CRM presence)
        scenario_results = []
        for code, left, right, should_match in REQUIRED_SCENARIOS:
            scored = score_company_name_pair(left, right)
            engine_match = scored is not None and scored.confidence >= MATCH_SCORE_MIN
            left_hits = [
                m
                for m in models
                if company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
                == company_name_comparison_key(display_name=left)
                or normalize_import_company_name(left)
                in company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
            ]
            # Broader search by first brand token + distinctive second token if present
            left_norm = normalize_import_company_name(left)
            right_norm = normalize_import_company_name(right)
            left_core = core_tokens(tokenize_company_name(left_norm))
            right_core = core_tokens(tokenize_company_name(right_norm))

            def _find_by_core(core: list[str]) -> list[CustomerModel]:
                if not core:
                    return []
                out = []
                for m in models:
                    k = company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
                    mc = core_tokens(tokenize_company_name(k))
                    if mc[: len(core)] == core or mc == core:
                        out.append(m)
                    elif len(core) >= 2 and set(core).issubset(set(mc)) and mc and mc[0] == core[0]:
                        out.append(m)
                return out

            left_live = _find_by_core(left_core)
            right_live = _find_by_core(right_core)

            # Check if any left_live and right_live share a duplicate group
            left_ids = {m.id for m in left_live}
            right_ids = {m.id for m in right_live}
            co_grouped = False
            for gkey, rows in groups.items():
                ids = {r.customer_id for r in rows}
                if left_ids & ids and right_ids & ids and left_ids & ids != right_ids & ids:
                    # both sides present in same group
                    if (left_ids & ids) and (right_ids & ids):
                        co_grouped = True
                        break
                if left_ids & ids and right_ids & ids:
                    co_grouped = True
                    break

            scenario_results.append(
                {
                    "code": code,
                    "left": left,
                    "right": right,
                    "should_match": should_match,
                    "engine_match": engine_match,
                    "engine_confidence": scored.confidence if scored else None,
                    "engine_ok": engine_match is should_match,
                    "left_live_count": len(left_live),
                    "right_live_count": len(right_live),
                    "left_live_names": [_company_name(m) for m in left_live[:5]],
                    "right_live_names": [_company_name(m) for m in right_live[:5]],
                    "co_grouped_in_live_analysis": co_grouped,
                    "live_ok": (
                        (co_grouped is should_match)
                        if (left_live and right_live)
                        else None
                    ),
                }
            )

        # False-negative heuristic: same brand+core multi-token, different legal form writing,
        # comparison keys equal OR score >= STRONG but NOT in same group
        fn_candidates: list[dict] = []
        # Build reverse: comparison_key -> customers (all, not only grouped)
        key_to_models: dict[str, list[CustomerModel]] = defaultdict(list)
        for m in models:
            k = company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
            if k:
                key_to_models[k].append(m)

        # Legal-form FN: identical comparison key but somehow not grouped (should be impossible)
        ungrouped_exact = 0
        for k, ms in key_to_models.items():
            if len(ms) < 2:
                continue
            # are they in a reported group?
            ids = {m.id for m in ms}
            found = False
            for rows in groups.values():
                row_ids = {r.customer_id for r in rows}
                if ids <= row_ids or len(ids & row_ids) >= 2:
                    found = True
                    break
            if not found:
                ungrouped_exact += 1
                fn_candidates.append(
                    {
                        "type": "exact_key_not_grouped",
                        "comparison_key": k,
                        "names": [_company_name(m) for m in ms],
                    }
                )

        # Strong fuzzy FN: sample pairs sharing first 3-char prefix / first token, score>=95, not co-grouped
        # Cap work: only check within first-token blocks up to 40
        block: dict[str, list[CustomerModel]] = defaultdict(list)
        for m in models:
            k = company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name)
            if not k:
                continue
            tok = k.split()[0] if k.split() else k
            if len(tok) > 2:
                block[tok].append(m)

        grouped_pairs: set[frozenset[UUID]] = set()
        for rows in groups.values():
            ids = [r.customer_id for r in rows]
            for i, a in enumerate(ids):
                for b in ids[i + 1 :]:
                    grouped_pairs.add(frozenset((a, b)))

        strong_ungrouped = 0
        for tok, ms in block.items():
            if len(ms) < 2 or len(ms) > 40:
                continue
            for i, a in enumerate(ms):
                for b in ms[i + 1 :]:
                    if frozenset((a.id, b.id)) in grouped_pairs:
                        continue
                    na, nb = _company_name(a), _company_name(b)
                    scored = score_company_name_pair(na, nb)
                    if scored is None or scored.confidence < MATCH_SCORE_STRONG:
                        continue
                    # same comparison key already handled; this is fuzzy strong
                    ka = company_name_comparison_key(display_name=a.display_name or "", legal_name=a.legal_name)
                    kb = company_name_comparison_key(display_name=b.display_name or "", legal_name=b.legal_name)
                    if ka == kb:
                        continue
                    strong_ungrouped += 1
                    if len(fn_candidates) < 40:
                        fn_candidates.append(
                            {
                                "type": "strong_fuzzy_not_grouped",
                                "confidence": scored.confidence,
                                "explanations": list(scored.explanations),
                                "names": [na, nb],
                                "comparison_keys": [ka, kb],
                            }
                        )

        # ACARLAR-like live scan: groups / non-groups with shared single brand token
        acarlar_models = [
            m
            for m in models
            if "acarlar"
            in company_name_comparison_key(display_name=m.display_name or "", legal_name=m.legal_name).split()
        ]
        acarlar_groups = []
        for gkey, rows in groups.items():
            ids = {r.customer_id for r in rows}
            members = [m for m in acarlar_models if m.id in ids]
            if len(members) >= 2:
                acarlar_groups.append(
                    {
                        "group_key": gkey,
                        "names": [_company_name(m) for m in members],
                        "shared": sorted(_shared_core_tokens([_company_name(m) for m in members])),
                    }
                )

        report = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "organization_id": str(org_id),
            "total_customers_analyzed": summary.total_customers,
            "duplicate_groups": summary.duplicate_groups,
            "customers_in_duplicate_groups": summary.customers_in_duplicate_groups,
            "legal_form_exact_groups": legal_form_exact_groups,
            "member_score_band_counts": dict(member_band_counts),
            "group_max_score_band_counts": dict(group_band_counts),
            "group_min_score_band_counts": dict(group_min_band_counts),
            "problem_c_performance": problem_c_perf,
            "suspect_single_token_group_count": len(suspect_single_token),
            "suspect_single_token_examples": suspect_single_token[:25],
            "short_hub_suspect_count": len(short_hub_suspects),
            "short_hub_examples": short_hub_suspects[:15],
            "sector_only_suspect_count": len(sector_only_suspects),
            "sector_only_examples": sector_only_suspects[:15],
            "transitive_member_group_count": len(transitive_only),
            "transitive_examples": transitive_only[:15],
            "required_scenarios": scenario_results,
            "acarlar_live_customer_count": len(acarlar_models),
            "acarlar_live_names": [_company_name(m) for m in acarlar_models[:20]],
            "acarlar_duplicate_groups": acarlar_groups,
            "false_negative_exact_key_ungrouped": ungrouped_exact,
            "false_negative_strong_fuzzy_ungrouped_sampled": strong_ungrouped,
            "false_negative_examples": fn_candidates[:25],
            "largest_groups": [
                {
                    "group_key": d["group_key"],
                    "size": d["size"],
                    "names": d["names"][:12],
                    "shared_core_tokens": d["shared_core_tokens"],
                    "max_score": d["max_score"],
                    "min_score": d["min_score"],
                    "pairwise_min_score": d["pairwise_min_score"],
                    "member_reasons": d["member_reasons"][:12],
                }
                for d in sorted(group_details, key=lambda x: -x["size"])[:20]
            ],
        }

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        out_path = REPORTS_DIR / f"company_name_engine_live_{stamp}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # Human summary
        print("\n=== SUMMARY ===")
        print(f"Customers analyzed: {summary.total_customers}")
        print(f"Duplicate groups: {summary.duplicate_groups}")
        print(f"Customers in groups: {summary.customers_in_duplicate_groups}")
        print(f"Exact same comparison-key groups: {legal_form_exact_groups}")
        print(f"Group max-score bands: {dict(group_band_counts)}")
        print(f"Group min-score bands: {dict(group_min_band_counts)}")
        print(f"Member score bands: {dict(member_band_counts)}")
        print(f"Suspect single-token groups: {len(suspect_single_token)}")
        print(f"Short-hub suspects: {len(short_hub_suspects)}")
        print(f"Sector-only suspects: {len(sector_only_suspects)}")
        print(f"Groups with transitive/None scores: {len(transitive_only)}")
        print(f"FN exact-key ungrouped: {ungrouped_exact}")
        print(f"FN strong-fuzzy ungrouped (sampled blocks): {strong_ungrouped}")

        print("\n=== PROBLEM C PERFORMANCE ===")
        print(f"Blocks above 32 (old hard-skip count): {old_skip_block_count}")
        print(f"Top large blocks: {problem_c_perf['blocks_above_32_sizes']}")
        print(f"Theoretical naive pairs: {naive_pairs}")
        print(f"Candidate pairs generated: {candidates}")
        print(f"Pairs scored: {scored_pairs}")
        print(f"Pairs accepted: {accepted_pairs}")
        print(
            f"Ratios candidate/naive={problem_c_perf['candidate_vs_naive_ratio']} "
            f"scored/naive={problem_c_perf['scored_vs_naive_ratio']}"
        )

        print("\n=== REQUIRED SCENARIOS ===")
        for s in scenario_results:
            print(
                f"{s['code']}: engine_match={s['engine_match']} conf={s['engine_confidence']} "
                f"should={s['should_match']} engine_ok={s['engine_ok']} "
                f"live_left={s['left_live_count']} live_right={s['right_live_count']} "
                f"co_grouped={s['co_grouped_in_live_analysis']} live_ok={s['live_ok']}"
            )

        print("\n=== ACARLAR LIVE ===")
        print(f"customers with token acarlar: {len(acarlar_models)}")
        for name in report["acarlar_live_names"]:
            print(f"  - {name}")
        print(f"acarlar duplicate groups: {len(acarlar_groups)}")
        for g in acarlar_groups:
            print(f"  group {g['group_key']}: shared={g['shared']} names={g['names']}")

        print("\n=== TOP SUSPECT SINGLE-TOKEN GROUPS ===")
        for d in suspect_single_token[:10]:
            print(f"  key={d['group_key']} size={d['size']} shared={d['shared_core_tokens']}")
            for n in d["names"][:6]:
                print(f"    - {n}")

        print("\n=== TOP FALSE-NEGATIVE CANDIDATES ===")
        for d in fn_candidates[:10]:
            print(f"  type={d['type']} names={d.get('names')} conf={d.get('confidence')}")

        print(f"\nFull JSON report: {out_path}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
