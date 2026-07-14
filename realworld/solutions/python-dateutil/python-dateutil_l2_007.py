import dateutil.parser
import dateutil.tz

def solve(s: str, hours: int) -> str:
    dt = dateutil.parser.isoparse(s)
    return dt.replace(tzinfo=dateutil.tz.tzoffset(None, hours * 3600)).isoformat()
