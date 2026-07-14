import datetime
import dateutil.relativedelta

def solve(d: datetime.date) -> str:
    return (d + dateutil.relativedelta.relativedelta(day=31)).isoformat()
