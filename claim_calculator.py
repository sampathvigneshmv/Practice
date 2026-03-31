"""
Claim Amount Calculator
Supports: Auto LOB and Home LOB
"""

from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────

@dataclass
class AutoClaim:
    # Coverages
    vehicle_damage: float = 0.0          # Collision / comprehensive repair cost
    medical_expenses: float = 0.0        # Bodily-injury / MedPay costs
    liability_damage: float = 0.0        # Third-party property damage
    rental_reimbursement: float = 0.0    # Daily rental × days (capped by policy)
    towing_storage: float = 0.0          # Towing and storage fees

    # Policy terms
    deductible: float = 0.0
    policy_limit: float = float("inf")   # Max payout across all coverages
    rental_daily_limit: float = 40.0     # $/day rental cap
    rental_days: int = 0                 # Actual rental days needed
    depreciation_rate: float = 0.0       # 0–1; applied to vehicle_damage for ACV


@dataclass
class HomeClaim:
    # Coverages
    dwelling_damage: float = 0.0         # Structure repair / rebuild cost
    personal_property_loss: float = 0.0  # Contents replacement value
    additional_living_expenses: float = 0.0  # ALE / loss-of-use
    liability_claim: float = 0.0         # Third-party liability exposure
    other_structures: float = 0.0        # Fences, garages, sheds

    # Policy terms
    deductible: float = 0.0
    dwelling_limit: float = float("inf") # Coverage A limit
    personal_property_limit: float = float("inf")  # Coverage C limit
    ale_limit: float = float("inf")      # Coverage D limit
    liability_limit: float = float("inf")
    replacement_cost_value: bool = True  # True=RCV, False=ACV
    depreciation_rate: float = 0.0       # 0–1; only used when RCV=False


# ──────────────────────────────────────────────
# CALCULATOR FUNCTIONS
# ──────────────────────────────────────────────

def calculate_auto_claim(claim: AutoClaim) -> dict:
    """Return a breakdown and net payout for an Auto claim."""
    errors = _validate_auto(claim)
    if errors:
        return {"errors": errors}

    # Rental reimbursement: cap at daily limit × days
    rental_cap = claim.rental_daily_limit * claim.rental_days
    rental_paid = min(claim.rental_reimbursement, rental_cap)

    # Vehicle damage: apply depreciation for ACV policies
    vehicle_after_depreciation = claim.vehicle_damage * (1 - claim.depreciation_rate)

    gross = (
        vehicle_after_depreciation
        + claim.medical_expenses
        + claim.liability_damage
        + rental_paid
        + claim.towing_storage
    )

    after_deductible = max(0.0, gross - claim.deductible)
    net_payout = min(after_deductible, claim.policy_limit)

    return {
        "lob": "Auto",
        "breakdown": {
            "vehicle_damage_after_depreciation": round(vehicle_after_depreciation, 2),
            "medical_expenses": round(claim.medical_expenses, 2),
            "liability_damage": round(claim.liability_damage, 2),
            "rental_reimbursement_paid": round(rental_paid, 2),
            "towing_and_storage": round(claim.towing_storage, 2),
        },
        "gross_loss": round(gross, 2),
        "deductible_applied": round(min(claim.deductible, gross), 2),
        "net_payout": round(net_payout, 2),
        "capped_by_policy_limit": net_payout < after_deductible,
    }


def calculate_home_claim(claim: HomeClaim) -> dict:
    """Return a breakdown and net payout for a Home claim."""
    errors = _validate_home(claim)
    if errors:
        return {"errors": errors}

    # Dwelling: apply depreciation if ACV policy
    if claim.replacement_cost_value:
        dwelling_paid = min(claim.dwelling_damage, claim.dwelling_limit)
    else:
        dwelling_paid = min(
            claim.dwelling_damage * (1 - claim.depreciation_rate),
            claim.dwelling_limit,
        )

    # Personal property: cap at Coverage C limit
    pp_paid = min(claim.personal_property_loss, claim.dwelling_limit)

    # ALE: cap at Coverage D limit
    ale_paid = min(claim.additional_living_expenses, claim.ale_limit)

    # Liability: cap at liability limit
    liability_paid = min(claim.liability_claim, claim.liability_limit)

    # Other structures
    other_paid = claim.other_structures

    gross = dwelling_paid + pp_paid + ale_paid + liability_paid + other_paid

    after_deductible = max(0.0, gross - claim.deductible)

    return {
        "lob": "Home",
        "breakdown": {
            "dwelling_damage_paid": round(dwelling_paid, 2),
            "personal_property_paid": round(pp_paid, 2),
            "additional_living_expenses_paid": round(ale_paid, 2),
            "liability_paid": round(liability_paid, 2),
            "other_structures_paid": round(other_paid, 2),
        },
        "gross_loss": round(gross, 2),
        "deductible_applied": round(min(claim.deductible, gross), 2),
        "net_payout": round(gross, 2),
        "valuation_method": "Replacement Cost Value" if claim.replacement_cost_value else "Actual Cash Value",
    }


# ──────────────────────────────────────────────
# VALIDATION HELPERS
# ──────────────────────────────────────────────

def _validate_auto(c: AutoClaim) -> list[str]:
    errors = []
    if c.deductible < 0:
        errors.append("Deductible cannot be negative.")
    if not (0.0 <= c.depreciation_rate <= 1.0):
        errors.append("Depreciation rate must be between 0 and 1.")
    for name, val in [
        ("vehicle_damage", c.vehicle_damage),
        ("medical_expenses", c.medical_expenses),
        ("liability_damage", c.liability_damage),
        ("towing_storage", c.towing_storage),
    ]:
        if val < 0:
            errors.append(f"{name} cannot be negative.")
    return errors


def _validate_home(c: HomeClaim) -> list[str]:
    errors = []
    if c.deductible < 0:
        errors.append("Deductible cannot be negative.")
    if not (0.0 <= c.depreciation_rate <= 1.0):
        errors.append("Depreciation rate must be between 0 and 1.")
    for name, val in [
        ("dwelling_damage", c.dwelling_damage),
        ("personal_property_loss", c.personal_property_loss),
        ("additional_living_expenses", c.additional_living_expenses),
        ("liability_claim", c.liability_claim),
        ("other_structures", c.other_structures),
    ]:
        if val < 0:
            errors.append(f"{name} cannot be negative.")
    return errors


# ──────────────────────────────────────────────
# DISPLAY HELPER
# ──────────────────────────────────────────────

def print_result(result: dict) -> None:
    if "errors" in result:
        print("\n[VALIDATION ERRORS]")
        for e in result["errors"]:
            print(f"  - {e}")
        return

    lob = result["lob"]
    print(f"\n{'='*45}")
    print(f"  {lob} LOB — Claim Summary")
    print(f"{'='*45}")
    print("  Coverage Breakdown:")
    for k, v in result["breakdown"].items():
        label = k.replace("_", " ").title()
        print(f"    {label:<38} ${v:>10,.2f}")
    print(f"  {'─'*43}")
    print(f"  {'Gross Loss':<38} ${result['gross_loss']:>10,.2f}")
    print(f"  {'Deductible Applied':<38} ${result['deductible_applied']:>10,.2f}")
    print(f"  {'Net Payout':<38} ${result['net_payout']:>10,.2f}")
    if "valuation_method" in result:
        print(f"  Valuation: {result['valuation_method']}")
    if result.get("capped_by_policy_limit"):
        print("  * Payout capped at policy limit.")
    print(f"{'='*45}\n")


# ──────────────────────────────────────────────
# INTERACTIVE CLI
# ──────────────────────────────────────────────

def _get_float(prompt: str, default: float = 0.0) -> float:
    while True:
        raw = input(f"  {prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        try:
            val = float(raw)
            if val < 0:
                print("    Please enter a non-negative number.")
                continue
            return val
        except ValueError:
            print("    Invalid input — please enter a number.")


def _get_int(prompt: str, default: int = 0) -> int:
    while True:
        raw = input(f"  {prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        try:
            val = int(raw)
            if val < 0:
                print("    Please enter a non-negative integer.")
                continue
            return val
        except ValueError:
            print("    Invalid input — please enter an integer.")


def _get_yes_no(prompt: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    while True:
        raw = input(f"  {prompt} [{default_str}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("    Please enter y or n.")


def interactive_auto() -> None:
    print("\n--- AUTO CLAIM INPUTS ---")
    claim = AutoClaim(
        vehicle_damage=_get_float("Vehicle repair / replacement cost ($)"),
        medical_expenses=_get_float("Medical / bodily-injury expenses ($)"),
        liability_damage=_get_float("Third-party property liability ($)"),
        towing_storage=_get_float("Towing & storage fees ($)"),
        rental_days=_get_int("Rental days needed"),
        rental_reimbursement=_get_float("Total rental cost ($)"),
        rental_daily_limit=_get_float("Rental daily limit ($/day)", default=40.0),
        deductible=_get_float("Deductible ($)"),
        policy_limit=_get_float("Policy limit ($, 0 = unlimited)", default=0.0),
        depreciation_rate=_get_float("Depreciation rate (0–1, 0 = RCV)", default=0.0),
    )
    if claim.policy_limit == 0:
        claim.policy_limit = float("inf")
    print_result(calculate_auto_claim(claim))


def interactive_home() -> None:
    print("\n--- HOME CLAIM INPUTS ---")
    claim = HomeClaim(
        dwelling_damage=_get_float("Dwelling / structure damage ($)"),
        personal_property_loss=_get_float("Personal property / contents loss ($)"),
        additional_living_expenses=_get_float("Additional living expenses ($)"),
        liability_claim=_get_float("Third-party liability claim ($)"),
        other_structures=_get_float("Other structures damage ($)"),
        deductible=_get_float("Deductible ($)"),
        dwelling_limit=_get_float("Dwelling coverage limit (Coverage A, 0=unlimited)", default=0.0),
        personal_property_limit=_get_float("Personal property limit (Coverage C, 0=unlimited)", default=0.0),
        ale_limit=_get_float("ALE limit (Coverage D, 0=unlimited)", default=0.0),
        liability_limit=_get_float("Liability limit (0=unlimited)", default=0.0),
        replacement_cost_value=_get_yes_no("Replacement Cost Value policy?", default=True),
        depreciation_rate=_get_float("Depreciation rate (0–1, only for ACV)", default=0.0),
    )
    for attr in ("dwelling_limit", "personal_property_limit", "ale_limit", "liability_limit"):
        if getattr(claim, attr) == 0.0:
            setattr(claim, attr, float("inf"))
    print_result(calculate_home_claim(claim))


def main() -> None:
    print("\n==========================================")
    print("      CLAIM AMOUNT CALCULATOR")
    print("      Auto LOB  |  Home LOB")
    print("==========================================")

    while True:
        print("\nSelect Line of Business:")
        print("  1 — Auto")
        print("  2 — Home")
        print("  3 — Run demo (both LOBs)")
        print("  0 — Exit")
        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            interactive_auto()
        elif choice == "2":
            interactive_home()
        elif choice == "3":
            _run_demo()
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid choice — please enter 0, 1, 2, or 3.")


# ──────────────────────────────────────────────
# DEMO
# ──────────────────────────────────────────────

def _run_demo() -> None:
    print("\n[DEMO] Auto Claim — Collision with rental and medical")
    auto = AutoClaim(
        vehicle_damage=12_000.0,
        medical_expenses=3_500.0,
        liability_damage=2_000.0,
        rental_reimbursement=600.0,   # 15 days × $40 limit
        rental_daily_limit=40.0,
        rental_days=15,
        towing_storage=250.0,
        deductible=500.0,
        policy_limit=50_000.0,
        depreciation_rate=0.10,       # ACV: 10% depreciation on vehicle
    )
    print_result(calculate_auto_claim(auto))

    print("[DEMO] Home Claim — Fire damage with ALE")
    home = HomeClaim(
        dwelling_damage=85_000.0,
        personal_property_loss=20_000.0,
        additional_living_expenses=8_000.0,
        liability_claim=0.0,
        other_structures=3_000.0,
        deductible=1_000.0,
        dwelling_limit=200_000.0,
        personal_property_limit=40_000.0,
        ale_limit=10_000.0,
        liability_limit=100_000.0,
        replacement_cost_value=True,
    )
    print_result(calculate_home_claim(home))


# ──────────────────────────────────────────────

if __name__ == "__main__":
    main()
