import datetime
import dateutil.relativedelta

def solve(d: datetime.date) -> str:
    return (d + dateutil.relativedelta.relativedelta(months=+1, day=31)).isoformat()
