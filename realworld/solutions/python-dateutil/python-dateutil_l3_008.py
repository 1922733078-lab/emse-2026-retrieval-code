import dateutil.parser
import dateutil.tz

def solve(s: str, offset_h: int) -> str:
    dt = dateutil.parser.isoparse(s)
    tz = dateutil.tz.tzoffset('X', offset_h * 3600)
    return dt.astimezone(tz).isoformat()
