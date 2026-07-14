import dateutil.parser
import dateutil.tz

def solve(s: str) -> str:
    dt = dateutil.parser.isoparse(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(dateutil.tz.UTC)
    return dt.isoformat()
