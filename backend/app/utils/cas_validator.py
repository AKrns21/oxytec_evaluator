"""CAS Registry Number validation and correction utilities."""

from typing import Optional, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)


def validate_cas_checksum(cas: str) -> bool:
    """
    Validate CAS Registry Number using checksum algorithm.

    CAS numbers have format: NNNNN-NN-C where C is a check digit.
    Algorithm:
    1. Remove hyphens: NNNNNNNC
    2. Starting from right, multiply each digit (except check digit) by position (1, 2, 3, ...)
    3. Sum all products
    4. Check digit = sum mod 10

    Args:
        cas: CAS number string (e.g., "100-41-4" or "100414")

    Returns:
        True if checksum is valid, False otherwise

    Examples:
        >>> validate_cas_checksum("100-41-4")
        True
        >>> validate_cas_checksum("100-61-4")  # Wrong
        False
        >>> validate_cas_checksum("78-40-4")
        True
        >>> validate_cas_checksum("78-40-0")  # Wrong
        False
    """
    if not cas:
        return False

    # Remove hyphens and spaces
    cas_clean = cas.replace("-", "").replace(" ", "").strip()

    # Must be all digits
    if not cas_clean.isdigit():
        return False

    # Must be at least 5 digits (minimum CAS format: NNN-N-C)
    if len(cas_clean) < 5:
        return False

    # Last digit is the check digit
    check_digit = int(cas_clean[-1])

    # Calculate checksum from remaining digits (right to left, excluding check digit)
    digits = cas_clean[:-1]
    checksum = 0

    for position, digit in enumerate(reversed(digits), start=1):
        checksum += int(digit) * position

    # Check digit should equal checksum mod 10
    expected_check_digit = checksum % 10

    return check_digit == expected_check_digit


def suggest_cas_correction(cas: str) -> Optional[str]:
    """
    Try to suggest a corrected CAS number by trying different last digits.

    This is useful for common OCR errors where the last digit is misread.

    Args:
        cas: Potentially incorrect CAS number

    Returns:
        Corrected CAS number if a valid one is found, None otherwise
    """
    if not cas or validate_cas_checksum(cas):
        # Already valid or empty
        return None

    # Remove hyphens for manipulation
    cas_clean = cas.replace("-", "").replace(" ", "").strip()

    if not cas_clean.isdigit() or len(cas_clean) < 5:
        return None

    # Try all possible last digits (0-9)
    base = cas_clean[:-1]

    for new_check_digit in range(10):
        candidate = base + str(new_check_digit)
        if validate_cas_checksum(candidate):
            # Format back to standard CAS format (NNNNN-NN-C)
            if len(candidate) >= 3:
                # Insert hyphens: last digit is check, previous 2 are middle section
                formatted = f"{candidate[:-3]}-{candidate[-3:-1]}-{candidate[-1]}"

                logger.info(
                    "cas_correction_suggested",
                    original=cas,
                    corrected=formatted,
                    reason="checksum_validation"
                )

                return formatted

    return None


def format_cas_number(cas: str) -> str:
    """
    Format CAS number to standard format: NNNNN-NN-C

    Args:
        cas: CAS number (with or without hyphens)

    Returns:
        Formatted CAS number
    """
    if not cas:
        return cas

    # Remove existing hyphens and spaces
    cas_clean = cas.replace("-", "").replace(" ", "").strip()

    if not cas_clean.isdigit() or len(cas_clean) < 5:
        # Return original if invalid format
        return cas

    # Format: NNNNN-NN-C (last digit is check, previous 2 are middle section)
    if len(cas_clean) >= 3:
        formatted = f"{cas_clean[:-3]}-{cas_clean[-3:-1]}-{cas_clean[-1]}"
        return formatted

    return cas


def validate_and_correct_cas(cas: str) -> Tuple[str, bool, Optional[str]]:
    """
    Validate CAS number and suggest correction if invalid.

    Args:
        cas: CAS number to validate

    Returns:
        Tuple of (cas_number, is_valid, suggested_correction)
        - cas_number: Original CAS (formatted)
        - is_valid: True if checksum is valid
        - suggested_correction: Corrected CAS if invalid, None otherwise
    """
    if not cas:
        return (cas, False, None)

    # Format to standard format
    formatted = format_cas_number(cas)

    # Check if valid
    is_valid = validate_cas_checksum(formatted)

    if is_valid:
        return (formatted, True, None)

    # Try to suggest correction
    suggestion = suggest_cas_correction(formatted)

    return (formatted, False, suggestion)


# Example usage and tests
if __name__ == "__main__":
    test_cases = [
        ("100-41-4", True, "Ethylbenzene (correct)"),
        ("100-61-4", False, "Ethylbenzene (wrong - should be 100-41-4)"),
        ("78-40-4", True, "Triethyl phosphate (correct)"),
        ("78-40-0", False, "Triethyl phosphate (wrong - should be 78-40-4)"),
        ("28961-43-5", True, "Poly(oxy-1,2-ethandiyl)"),
        ("64359-81-5", True, "DCOIT"),
        ("50-00-0", True, "Formaldehyde"),
    ]

    print("CAS Number Validation Tests:")
    print("=" * 70)

    for cas, expected_valid, description in test_cases:
        is_valid = validate_cas_checksum(cas)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} {cas:15} Valid: {is_valid:5} - {description}")

        if not is_valid:
            suggestion = suggest_cas_correction(cas)
            if suggestion:
                print(f"   → Suggested correction: {suggestion}")

    print("\n" + "=" * 70)
    print("Full Validation with Corrections:")
    print("=" * 70)

    for cas, _, description in test_cases:
        formatted, is_valid, suggestion = validate_and_correct_cas(cas)
        status = "✅" if is_valid else "❌"
        print(f"{status} {formatted:15} - {description}")
        if suggestion:
            print(f"   → Correction: {suggestion}")
