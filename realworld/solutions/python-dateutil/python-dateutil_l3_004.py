import datetime
import dateutil.relativedelta

def solve(year: int, month: int) -> str:
    d = datetime.date(year, month, 1)
    return (d + dateutil.relativedelta.relativedelta(months=+1, days=-1)).isoformat()
