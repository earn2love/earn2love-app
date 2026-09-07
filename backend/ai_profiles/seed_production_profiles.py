"""
Production-safe seeding utility for Earn2Love AI profiles.

Default behavior:
- DRY RUN ONLY
- NO FIRESTORE WRITES
- NEVER overwrites existing profiles
- Forces draft + hidden before any possible write
"""

import argparse
from copy import deepcopy

import ai_profile_contract as PROFILE
from ai_engine.schema import (
    new_character,
    validate_character,
)
from ai_profiles.production_catalog import (
    PRODUCTION_AI_PROFILES,
)


def prepare_profile(profile):
    candidate = deepcopy(profile)

    candidate["profileStatus"] = "draft"
    candidate["visibility"] = "hidden"
    candidate["isAi"] = True
    candidate["aiDisclosure"] = True
    candidate["archived"] = False

    core = new_character(**candidate)

    ok, errors = validate_character(core)

    if not ok:
        raise ValueError(
            f"{candidate.get('characterId')}: "
            f"core validation failed: {errors}"
        )

    normalized = PROFILE.normalize_profile(
        {
            **candidate,
            **core,
        }
    )

    if normalized["profileStatus"] != "draft":
        raise ValueError(
            "profileStatus must remain draft"
        )

    if normalized["visibility"] != "hidden":
        raise ValueError(
            "visibility must remain hidden"
        )

    if normalized["isAi"] is not True:
        raise ValueError(
            "isAi must remain true"
        )

    if normalized["aiDisclosure"] is not True:
        raise ValueError(
            "aiDisclosure must remain true"
        )

    return normalized


def load_prepared_profiles():
    return [
        prepare_profile(profile)
        for profile
        in PRODUCTION_AI_PROFILES
    ]


def build_plan(repo):
    plan = []

    for profile in load_prepared_profiles():
        cid = profile["characterId"]

        existing = repo.get_character(cid)

        action = (
            "skip_existing"
            if existing
            else "create"
        )

        plan.append(
            {
                "characterId": cid,
                "displayName": profile[
                    "displayName"
                ],
                "action": action,
                "profileStatus": profile[
                    "profileStatus"
                ],
                "visibility": profile[
                    "visibility"
                ],
            }
        )

    return plan


def execute_seed(
    repo,
    *,
    write=False,
    allow_overwrite=False,
):
    prepared = load_prepared_profiles()

    results = []

    for profile in prepared:
        cid = profile["characterId"]

        existing = repo.get_character(cid)

        if existing and not allow_overwrite:
            results.append(
                {
                    "characterId": cid,
                    "status": "skipped_existing",
                }
            )
            continue

        if not write:
            results.append(
                {
                    "characterId": cid,
                    "status": (
                        "would_overwrite"
                        if existing
                        else "would_create"
                    ),
                }
            )
            continue

        repo.upsert_character(profile)

        results.append(
            {
                "characterId": cid,
                "status": (
                    "overwritten"
                    if existing
                    else "created"
                ),
            }
        )

    return results


def _get_production_repo():
    from ai_service import prod_repo

    return prod_repo()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Actually write profiles. "
            "Default is dry-run."
        ),
    )

    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help=(
            "Allow replacing existing profiles. "
            "Ignored unless --write is also supplied."
        ),
    )

    args = parser.parse_args()

    repo = _get_production_repo()

    print("=" * 72)
    print(
        "EARN2LOVE AI PROFILE SEED"
    )
    print("=" * 72)

    print(
        "MODE:",
        "WRITE"
        if args.write
        else "DRY RUN",
    )

    if args.allow_overwrite:
        print(
            "OVERWRITE:",
            "ENABLED",
        )
    else:
        print(
            "OVERWRITE:",
            "DISABLED",
        )

    print()

    plan = build_plan(repo)

    for item in plan:
        print(
            item["characterId"],
            "|",
            item["displayName"],
            "|",
            item["action"],
            "|",
            item["profileStatus"],
            "|",
            item["visibility"],
        )

    print()
    print(
        "TOTAL:",
        len(plan),
    )

    if not args.write:
        print()
        print(
            "DRY RUN COMPLETE - ZERO WRITES"
        )
        return

    results = execute_seed(
        repo,
        write=True,
        allow_overwrite=args.allow_overwrite,
    )

    print()
    print("WRITE RESULTS")

    for result in results:
        print(
            result["characterId"],
            "|",
            result["status"],
        )


if __name__ == "__main__":
    main()
