from __future__ import annotations

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


_SIGNER = TimestampSigner(salt="qrtendify.attendance_record")


def make_attendance_record_sig(record_id: int) -> str:
    return _SIGNER.sign(f"attendance_record:{record_id}")


def verify_attendance_record_sig(
    record_id: int, sig: str, *, max_age_seconds: int
) -> bool:
    try:
        unsigned = _SIGNER.unsign(sig, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False
    return unsigned == f"attendance_record:{record_id}"
