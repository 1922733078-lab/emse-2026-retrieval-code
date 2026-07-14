import datetime
import dateutil.tz
import dateutil.utils

def solve(dt: datetime.datetime) -> str:
    return dateutil.utils.default_tzinfo(dt, dateutil.tz.UTC).isoformat()
