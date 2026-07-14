import dateutil.parser
import dateutil.tz

def solve(s: str) -> bool:
    dt = dateutil.parser.isoparse(s).replace(tzinfo=dateutil.tz.UTC)
    return dateutil.tz.datetime_exists(dt, dateutil.tz.UTC)
