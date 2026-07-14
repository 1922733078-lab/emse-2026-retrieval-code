import datetime
import dateutil.relativedelta

def solve(d: datetime.date) -> str:
    return (d + dateutil.relativedelta.relativedelta(years=+2, months=-1)).isoformat()
