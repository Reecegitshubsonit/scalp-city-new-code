from typing import Mapping

SANDBOX_HOST = "api.sandbox.webull.com"


class GuardError(RuntimeError):
    pass


def assert_paper_only(env: Mapping[str, str], host: str, accounts: list[dict]) -> dict:
    """Refuse to continue unless everything says paper/sandbox. Returns the selected account row."""
    if env.get("WEBULL_ENV", "").lower() != "sandbox":
        raise GuardError("WEBULL_ENV must be 'sandbox'")
    if env.get("WEBULL_SANDBOX_ACCOUNT_ATTESTED", "").lower() != "true":
        raise GuardError("WEBULL_SANDBOX_ACCOUNT_ATTESTED must be 'true'")
    if host != SANDBOX_HOST:
        raise GuardError(f"host must be {SANDBOX_HOST}, got {host}")
    wanted = env.get("WEBULL_PAPER_ACCOUNT_NUMBER", "")
    match = [a for a in accounts if wanted and a.get("account_number") == wanted]
    if len(match) != 1:
        raise GuardError(f"WEBULL_PAPER_ACCOUNT_NUMBER matches {len(match)} sandbox accounts; need exactly 1")
    return match[0]
