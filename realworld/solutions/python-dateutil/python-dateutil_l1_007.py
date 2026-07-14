import dateutil.tz

def solve(name: str, hours: float) -> float:
    return dateutil.tz.tzoffset(name, hours * 3600).utcoffset(None).total_seconds()
