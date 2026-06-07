from __future__ import annotations

import re
from typing import Optional, TypedDict


class ValidationDecision(TypedDict):
    pass_: bool
    reason: Optional[str]
    safe_text: Optional[str]


_decisions: dict[str, ValidationDecision] = {}


def take_decision(decision_id: str) -> Optional[ValidationDecision]:
    return _decisions.pop(decision_id, None)


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _allowed(text: str) -> ValidationDecision:
    return {"pass_": True, "reason": None, "safe_text": _normalize_text(text)}


def _blocked(reason: str) -> ValidationDecision:
    return {"pass_": False, "reason": reason, "safe_text": None}


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


SPAM_PATTERNS = (
    r"\bbitcoin\s+giveaway\b",
    r"\bcrypto\s+(?:giveaway|investment|profit)\b",
    r"\bcasino\b",
    r"\bclick\s+(?:here|this\s+link)\b",
    r"\bfree\s+money\b",
    r"\bwhatsapp\s+me\b",
)

OFF_TOPIC_PATTERNS = (
    r"\bwrite\s+(?:me\s+)?(?:python|javascript|sql)\s+code\b",
    r"\brecipe\b",
    r"\bfootball\s+(?:score|match|team)\b",
    r"\bstock\s+market\b",
    r"\bmedical\s+advice\b",
)

OFFENSIVE_PATTERNS = (
    r"\bfuck(?:ing)?\b",
    r"\bshit(?:ty)?\b",
    r"\bbitch\b",
    r"\bidiot\b",
    r"\bstupid\b",
)

PROMPT_INJECTION_PATTERNS = (
    r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?\b",
    r"\bdisregard\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b",
    r"\breveal\s+(?:the\s+)?system\s+prompt\b",
    r"\byou\s+are\s+now\b",
    r"\bdeveloper\s+message\b",
    r"\bjailbreak\b",
)

PROPERTY_TERMS = (
    r"\bapartment\b",
    r"\bhouse\b",
    r"\bvilla\b",
    r"\bpenthouse\b",
    r"\bstudio\b",
    r"\boffice\b",
    r"\bwarehouse\b",
    r"\bretail\s+(?:shop|unit|space)\b",
    r"\bproperty\b",
    r"\bhome\b",
)

LISTING_DETAIL_TERMS = (
    r"\b\d+(?:\.\d+)?\s*(?:room|bedroom|bathroom|sqm|m2)\b",
    r"\b(?:room|bedroom|bathroom|balcony|parking|garden|terrace|kitchen)\b",
    r"\b(?:renovated|new|condition|sale|rent|price|nis|shekel|₪)\b",
    r"\b(?:located|location|in\s+[A-Z][a-z]+)\b",
)

LEGAL_CLAIM_PATTERNS = (
    r"\blegal\s+approval\s+(?:is\s+)?guaranteed\b",
    r"\bguaranteed\s+legal\s+approval\b",
    r"\bfully\s+legal\b",
    r"\bno\s+legal\s+risk\b",
    r"\b(?:property|listing|development)\s+(?:is\s+)?(?:legally|fully)\s+approved\b",
    r"\btitle\s+(?:is\s+)?guaranteed\s+clean\b",
    r"\b(?:approved|clear)\s+title\b",
    r"\bpermit(?:s)?\s+(?:is|are)\s+(?:approved|guaranteed)\b",
)

PROFIT_PATTERNS = (
    r"\bguaranteed\s+(?:profit|return|roi|rental\s+yield|income)\b",
    r"\bprofit\s+(?:is\s+)?guaranteed\b",
    r"\brisk[- ]free\s+(?:profit|investment|return)\b",
)

PRICE_INCREASE_PATTERNS = (
    r"\bguaranteed\s+(?:price\s+increase|appreciation|increase\s+in\s+value)\b",
    r"\bprice\s+(?:will|is\s+guaranteed\s+to)\s+(?:rise|increase|appreciate)\b",
    r"\bvalue\s+will\s+(?:rise|increase|appreciate)\b",
)

CERTIFICATION_PATTERNS = (
    r"\bcertified\s+(?:safe|approved|compliant|investment|green)\b",
    r"\bofficially\s+certified\b",
    r"\bverified\s+by\s+(?:the\s+)?(?:government|municipality|authority)\b",
)

UNSUPPORTED_CLAIM_PATTERNS = (
    r"\bguaranteed\s+tenant\b",
    r"\bguaranteed\s+sale\b",
    r"\bzero\s+risk\b",
    r"\bno\s+(?:structural\s+)?defects?\b",
    r"\bperfect\s+condition\b",
    r"\bdefinitely\s+(?:the\s+)?best\s+investment\b",
)

PRICE_PATTERN = re.compile(
    r"(?:₪\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s*(?:nis|ils|shekels?)\b)",
    flags=re.IGNORECASE,
)

PRICE_SOURCE_PATTERNS = (
    r"\baccording\s+to\s+(?:the\s+)?(?:submitted|provided|source|retrieved)\s+(?:listing|description|data)\b",
    r"\bsubmitted\s+(?:listing|description)\s+(?:states|lists|reports|includes)\b",
    r"\bretrieved\s+listing\s+(?:states|lists|reports|shows)\b",
)


def evaluate_input_text(text: str) -> ValidationDecision:
    normalized = _normalize_text(text)

    if _matches_any(normalized, PROMPT_INJECTION_PATTERNS):
        return _blocked("Input rejected: possible prompt injection instruction detected.")
    if _matches_any(normalized, OFFENSIVE_PATTERNS):
        return _blocked("Input rejected: offensive language is not allowed.")
    if _matches_any(normalized, SPAM_PATTERNS):
        return _blocked("Input rejected: spam or promotional content detected.")
    if _matches_any(normalized, OFF_TOPIC_PATTERNS):
        return _blocked("Input rejected: text is outside the real estate listing domain.")
    if not _matches_any(normalized, PROPERTY_TERMS):
        return _blocked("Input rejected: text does not identify a real estate property listing.")
    if not _matches_any(normalized, LISTING_DETAIL_TERMS):
        return _blocked("Input rejected: property listing details are missing.")

    return _allowed(normalized)


def evaluate_output_text(text: str) -> ValidationDecision:
    normalized = _normalize_text(text)

    if _matches_any(normalized, LEGAL_CLAIM_PATTERNS):
        return _blocked("Output rejected: unsupported legal or permit claim detected.")
    if _matches_any(normalized, PROFIT_PATTERNS):
        return _blocked("Output rejected: guaranteed profit or return claim detected.")
    if _matches_any(normalized, PRICE_INCREASE_PATTERNS):
        return _blocked("Output rejected: guaranteed price increase claim detected.")
    if _matches_any(normalized, CERTIFICATION_PATTERNS):
        return _blocked("Output rejected: fabricated or unsupported certification claim detected.")
    if _matches_any(normalized, UNSUPPORTED_CLAIM_PATTERNS):
        return _blocked("Output rejected: unsupported certainty claim detected.")
    # Change it to this so it looks for the source phrases again:
    if not PRICE_PATTERN.search(normalized):
        return _blocked(
        "Output rejected: a price is stated without attribution to submitted or retrieved listing data."
        )

    return _allowed(normalized)


def action(name: str, is_system_action: bool = False):
    def decorator(func):
        func.action_name = name
        func.is_system_action = is_system_action
        return func

    return decorator


def _record_decision(context: Optional[dict], decision: ValidationDecision) -> None:
    decision_id = str((context or {}).get("guardrails_decision_id", ""))
    if not decision_id:
        raise RuntimeError("Guardrails action received no decision request ID.")
    _decisions[decision_id] = decision


@action(name="validate_property_input", is_system_action=True)
async def validate_property_input(context: Optional[dict] = None) -> bool:
    text = str((context or {}).get("last_user_message", ""))
    decision = evaluate_input_text(text)
    _record_decision(context, decision)
    return decision["pass_"]


@action(name="validate_property_output", is_system_action=True)
async def validate_property_output(context: Optional[dict] = None) -> bool:
    text = str((context or {}).get("bot_message", ""))
    decision = evaluate_output_text(text)
    _record_decision(context, decision)
    return decision["pass_"]
