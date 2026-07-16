"""
Module 1 Exercise: A Bank Account Hierarchy
===========================================
Goal
----
Build a small account hierarchy that forces you to use every Module 1 concept:
class attributes, the three method kinds, properties with validation, cooperative
inheritance, and encapsulation conventions.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""


# ---------------------------------------------------------------------------
# TODO 1 — BankAccount basics
# ---------------------------------------------------------------------------
# Create a class `BankAccount` with:
#   * a CLASS attribute `bank_name = "PyBank"` (shared by all accounts)
#   * a CLASS attribute `_account_counter = 0` used to assign IDs
#   * __init__(self, owner, balance=0) that:
#       - stores `owner` as a public instance attribute
#       - stores the starting balance via the `balance` property (TODO 2)
#       - increments the class counter and assigns `self.account_id`
#         (1 for the first account created, 2 for the second, ...)
#         Hint: mutate the counter on the CLASS, not the instance.


# ---------------------------------------------------------------------------
# TODO 2 — balance as a validated property
# ---------------------------------------------------------------------------
# Make `balance` a property backed by `_balance`:
#   * getter returns the current balance
#   * setter raises ValueError("balance cannot be negative") for values < 0
# Add methods deposit(amount) and withdraw(amount) that adjust the balance
# through the property (so validation always applies). withdraw must raise
# ValueError for amounts greater than the balance.


# ---------------------------------------------------------------------------
# TODO 3 — an alternative constructor and a static helper
# ---------------------------------------------------------------------------
#   * @classmethod from_string(cls, text): parses "owner:balance"
#     (e.g. "ada:150.0") and returns cls(owner, balance) — it must return the
#     SUBCLASS when called through one.
#   * @staticmethod is_valid_amount(amount): True for numbers > 0, else False.


# ---------------------------------------------------------------------------
# TODO 4 — SavingsAccount subclass with cooperative __init__
# ---------------------------------------------------------------------------
# Create `SavingsAccount(BankAccount)`:
#   * __init__(self, owner, balance=0, *, rate=0.02) calls super().__init__
#     and stores `rate`
#   * method apply_interest() that deposits balance * rate
#   * a read-only property `projected_annual` returning balance * (1 + rate)


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    acc1 = BankAccount("ada", 100)
    acc2 = BankAccount("bob")
    assert BankAccount.bank_name == "PyBank"
    assert (acc1.account_id, acc2.account_id) == (1, 2), "counter must be class-level"

    acc1.deposit(50)
    acc1.withdraw(30)
    assert acc1.balance == 120

    try:
        acc1.withdraw(10_000)
        raise SystemExit("FAIL: overdraft should raise ValueError")
    except ValueError:
        pass

    try:
        BankAccount("eve", -5)
        raise SystemExit("FAIL: negative starting balance should raise")
    except ValueError:
        pass

    parsed = BankAccount.from_string("carol:75.5")
    assert (parsed.owner, parsed.balance) == ("carol", 75.5)
    assert BankAccount.is_valid_amount(10) and not BankAccount.is_valid_amount(-1)

    sav = SavingsAccount.from_string("dan:1000")     # classmethod polymorphism!
    assert type(sav) is SavingsAccount
    sav.apply_interest()
    assert sav.balance == 1020.0, f"expected 1020.0, got {sav.balance}"
    assert round(sav.projected_annual, 2) == round(1020.0 * 1.02, 2)
    try:
        sav.projected_annual = 0
        raise SystemExit("FAIL: projected_annual must be read-only")
    except AttributeError:
        pass

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add a __repr__ that shows owner, id and balance (preview of Module 2).
# 2. Make account_id read-only using a property with no setter.
# 3. Add a CheckingAccount with an overdraft_limit that loosens withdraw's rule,
#    reusing the parent implementation with super().

# Cleanup: nothing to clean up — pure in-memory Python.
