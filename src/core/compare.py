from src.core.enums import ConfirmationStatus
from src.utils.text import normalize_for_compare


def compare_optional_hint(expected, actual) -> ConfirmationStatus:
    if expected is None:
        return ConfirmationStatus.MISSING
    if actual is None:
        return ConfirmationStatus.USER_PROVIDED_HINT
    if expected == actual:
        return ConfirmationStatus.MATCH
    if normalize_for_compare(str(expected)) == normalize_for_compare(str(actual)):
        return ConfirmationStatus.NORMALIZED_MATCH
    return ConfirmationStatus.MISMATCH
