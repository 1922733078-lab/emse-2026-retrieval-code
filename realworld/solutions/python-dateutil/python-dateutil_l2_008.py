import dateutil.parser
import dateutil.tz

def solve(s: str) -> str:
    dt = dateutil.parser.isoparse(s).replace(tzinfo=dateutil.tz.UTC)
    return dateutil.tz.resolve_imaginary(dt).isoformat()
