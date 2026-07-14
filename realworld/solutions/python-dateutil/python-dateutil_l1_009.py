import datetime
import dateutil.utils

def solve(dt1: datetime.datetime, dt2: datetime.datetime) -> bool:
    return dateutil.utils.within_delta(dt1, dt2, datetime.timedelta(hours=1))
