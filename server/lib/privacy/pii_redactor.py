"""
PII Redactor Module - Redacts personally identifiable information before model calls.
Supports multiple modes: off, standard, strict
"""
import re
from typing import Dict, List, Any, Literal, TypedDict
from dataclasses import dataclass, field


class PIIFinding(TypedDict):
    type: Literal["email", "phone", "iban", "bank", "card", "id", "token", "address"]
    count: int
    examples: List[str]
    confidence: Literal["high", "medium", "low"]


@dataclass
class RedactionResult:
    redacted_text: str
    findings: List[PIIFinding] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "redacted_text": self.redacted_text,
            "findings": self.findings
        }


EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|'
    r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}|'
    r'\b\d{10,15}\b'
)

IBAN_PATTERN = re.compile(
    r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b',
    re.IGNORECASE
)

BANK_ACCOUNT_PATTERN = re.compile(
    r'\b\d{8,17}\b(?=.*(?:account|acct|a/c|routing|sort))|'
    r'(?:account|acct|a/c|routing|sort)\s*(?:number|no\.?|#)?\s*:?\s*\d{8,17}',
    re.IGNORECASE
)

CREDIT_CARD_PATTERN = re.compile(
    r'\b(?:4[0-9]{12}(?:[0-9]{3})?|'
    r'5[1-5][0-9]{14}|'
    r'3[47][0-9]{13}|'
    r'6(?:011|5[0-9]{2})[0-9]{12}|'
    r'(?:2131|1800|35\d{3})\d{11})\b|'
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
)

TOKEN_PATTERN = re.compile(
    r'\b(?:sk[-_]|rk[-_]|pk[-_]|api[-_]?key[-_]?|token[-_]?|secret[-_]?|password[-_]?)'
    r'[A-Za-z0-9_-]{16,}|'
    r'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b|'
    r'\b[A-Za-z0-9]{32,}\b(?=.*(?:key|token|secret|api))',
    re.IGNORECASE
)

ID_PATTERN = re.compile(
    r'\b(?:passport|ssn|social\s*security|national\s*id|driver.?s?\s*licen[sc]e)'
    r'\s*(?:number|no\.?|#)?\s*:?\s*[A-Z0-9]{5,20}|'
    r'\b[A-Z]{1,2}\d{6,9}[A-Z]?\b',
    re.IGNORECASE
)

ADDRESS_PATTERN = re.compile(
    r'\b\d{1,5}\s+(?:[A-Za-z]+\s+){1,4}(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|way|place|pl|circle|cir)\b'
    r'(?:\s*,?\s*(?:apt|apartment|suite|ste|unit|#)\s*\d+)?'
    r'(?:\s*,?\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?',
    re.IGNORECASE
)


def luhn_check(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(d) for d in re.sub(r'\D', '', card_number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def redact_text(
    input_text: str,
    mode: Literal["off", "standard", "strict"] = "standard"
) -> RedactionResult:
    """
    Redact PII from text based on mode.
    
    Modes:
    - off: No redaction
    - standard: Redact emails, phones, cards, IBANs, bank accounts, tokens, IDs
    - strict: All of standard plus addresses
    """
    if mode == "off":
        return RedactionResult(redacted_text=input_text, findings=[])
    
    redacted = input_text
    findings: List[PIIFinding] = []
    
    patterns = [
        ("email", EMAIL_PATTERN, "[REDACTED_EMAIL]", "high"),
        ("phone", PHONE_PATTERN, "[REDACTED_PHONE]", "medium"),
        ("card", CREDIT_CARD_PATTERN, "[REDACTED_CARD]", "high"),
        ("iban", IBAN_PATTERN, "[REDACTED_IBAN]", "high"),
        ("bank", BANK_ACCOUNT_PATTERN, "[REDACTED_BANK]", "medium"),
        ("token", TOKEN_PATTERN, "[REDACTED_TOKEN]", "high"),
        ("id", ID_PATTERN, "[REDACTED_ID]", "medium"),
    ]
    
    if mode == "strict":
        patterns.append(("address", ADDRESS_PATTERN, "[REDACTED_ADDRESS]", "low"))
    
    for pii_type, pattern, replacement, confidence in patterns:
        matches = pattern.findall(redacted)
        if matches:
            if pii_type == "card":
                valid_cards = [m for m in matches if isinstance(m, str) and luhn_check(m)]
                if valid_cards:
                    for card in valid_cards:
                        redacted = redacted.replace(card, replacement)
                    findings.append({
                        "type": pii_type,
                        "count": len(valid_cards),
                        "examples": [f"****{c[-4:]}" if len(c) >= 4 else "****" for c in valid_cards[:3]],
                        "confidence": confidence
                    })
            else:
                examples = []
                for match in matches[:3]:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]
                    if len(match) > 4:
                        examples.append(f"{match[:2]}...{match[-2:]}")
                    else:
                        examples.append("****")
                
                redacted = pattern.sub(replacement, redacted)
                findings.append({
                    "type": pii_type,
                    "count": len(matches),
                    "examples": examples,
                    "confidence": confidence
                })
    
    return RedactionResult(redacted_text=redacted, findings=findings)


def redact_object(obj: Any, mode: Literal["off", "standard", "strict"] = "standard") -> Any:
    """
    Recursively redact all string fields in an object.
    Returns a new object with redacted strings.
    """
    if mode == "off":
        return obj
    
    if isinstance(obj, str):
        result = redact_text(obj, mode)
        return result.redacted_text
    elif isinstance(obj, dict):
        return {k: redact_object(v, mode) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact_object(item, mode) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact_object(item, mode) for item in obj)
    else:
        return obj


def detect_pii(input_text: str) -> List[PIIFinding]:
    """
    Detect PII without redacting (for eval/audit purposes).
    Returns findings without modifying input.
    """
    result = redact_text(input_text, mode="strict")
    return result.findings


def has_pii(input_text: str) -> bool:
    """Quick check if text contains any PII."""
    findings = detect_pii(input_text)
    return len(findings) > 0
