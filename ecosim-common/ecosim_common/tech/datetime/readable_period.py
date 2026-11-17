from datetime import datetime, timedelta


def readable_period(start: datetime, end: datetime) -> str:
    time_format = "%Y-%m-%d %H:%M:%S" if _has_seconds(start) or _has_seconds(end) else "%Y-%m-%d %H:%M"
    return f"{start:{time_format}} to {end:{time_format}}{_zone_text(start)}"


def _has_seconds(moment: datetime) -> bool:
    return moment.second != 0 or moment.microsecond != 0


def _zone_text(moment: datetime) -> str:
    offset = moment.utcoffset()
    if offset is None:
        return ""
    if offset == timedelta(0):
        return " UTC"
    return f" {moment:UTC%:z}"
