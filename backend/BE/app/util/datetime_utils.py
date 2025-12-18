from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """한국 시간(KST) 기준 현재 시각 반환"""
    return datetime.now(KST)


def iso_now_kst() -> str:
    """KST 기준 ISO 포맷 문자열 반환"""
    return now_kst().isoformat()


def to_kst_isoformat(dt: datetime) -> str:
    if dt is None:
        return None
    return dt.astimezone(KST).isoformat()


def to_kst_date_str(dt: datetime) -> str:
    return dt.astimezone(KST).strftime("%Y-%m-%d")


def to_kst(dt: datetime) -> datetime:
    return dt.astimezone(KST)