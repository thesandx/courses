"""
Module 1 Solution — Bank Account Hierarchy
==========================================
Run: python3 solution.py
"""


class BankAccount:
    # Class attributes: one copy shared by every account.
    bank_name = "PyBank"
    _account_counter = 0

    def __init__(self, owner: str, balance: float = 0):
        self.owner = owner
        self.balance = balance                 # routes through the property setter
        # Mutate the counter on the CLASS. `self._account_counter += 1` would
        # read the class value but write an instance attribute — a shadow bug.
        BankAccount._account_counter += 1
        self._account_id = BankAccount._account_counter

    # --- TODO 2: validated property -------------------------------------
    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if value < 0:
            raise ValueError("balance cannot be negative")
        self._balance = value

    def deposit(self, amount: float):
        if not self.is_valid_amount(amount):
            raise ValueError("deposit must be positive")
        self.balance += amount                 # property setter re-validates

    def withdraw(self, amount: float):
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount

    # --- TODO 3: alternative constructor + static helper -----------------
    @classmethod
    def from_string(cls, text: str) -> "BankAccount":
        owner, _, raw_balance = text.partition(":")
        # `cls`, not `BankAccount`: SavingsAccount.from_string(...) must
        # build a SavingsAccount.
        return cls(owner, float(raw_balance))

    @staticmethod
    def is_valid_amount(amount) -> bool:
        return isinstance(amount, (int, float)) and amount > 0

    # --- Stretch 1 & 2 ----------------------------------------------------
    @property
    def account_id(self) -> int:               # read-only: no setter defined
        return self._account_id

    def __repr__(self):
        return (f"{type(self).__name__}(owner={self.owner!r}, "
                f"id={self.account_id}, balance={self.balance})")


class SavingsAccount(BankAccount):
    def __init__(self, owner: str, balance: float = 0, *, rate: float = 0.02):
        super().__init__(owner, balance)       # cooperative: parent sets up state
        self.rate = rate

    def apply_interest(self):
        self.deposit(self.balance * self.rate)

    @property
    def projected_annual(self) -> float:
        return self.balance * (1 + self.rate)


# --- Stretch 3: loosen the withdraw rule, reuse the parent -----------------
class CheckingAccount(BankAccount):
    def __init__(self, owner: str, balance: float = 0, *, overdraft_limit: float = 100):
        super().__init__(owner, balance)
        self.overdraft_limit = overdraft_limit

    def withdraw(self, amount: float):
        if amount > self.balance + self.overdraft_limit:
            raise ValueError("exceeds overdraft limit")
        # Can't reuse super().withdraw (its check is stricter) — but the
        # balance property still guards against < 0... so bypass via _balance
        # deliberately, documenting the invariant change.
        self._balance -= amount


if __name__ == "__main__":
    acc1 = BankAccount("ada", 100)
    acc2 = BankAccount("bob")
    assert (acc1.account_id, acc2.account_id) == (1, 2)

    acc1.deposit(50)
    acc1.withdraw(30)
    assert acc1.balance == 120

    try:
        acc1.withdraw(10_000)
        raise SystemExit("FAIL")
    except ValueError:
        pass
    try:
        BankAccount("eve", -5)
        raise SystemExit("FAIL")
    except ValueError:
        pass

    parsed = BankAccount.from_string("carol:75.5")
    assert (parsed.owner, parsed.balance) == ("carol", 75.5)
    assert BankAccount.is_valid_amount(10) and not BankAccount.is_valid_amount(-1)

    sav = SavingsAccount.from_string("dan:1000")
    assert type(sav) is SavingsAccount
    sav.apply_interest()
    assert sav.balance == 1020.0
    assert round(sav.projected_annual, 2) == round(1020.0 * 1.02, 2)
    try:
        sav.projected_annual = 0
        raise SystemExit("FAIL")
    except AttributeError:
        pass

    chk = CheckingAccount("erin", 50, overdraft_limit=100)
    chk.withdraw(120)                          # allowed: within overdraft
    assert chk.balance == -70
    try:
        chk.withdraw(1_000)
        raise SystemExit("FAIL")
    except ValueError:
        pass

    print(repr(sav))
    print("All solution checks passed ✔")
