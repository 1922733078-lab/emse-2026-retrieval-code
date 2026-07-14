import datetime
import dateutil.relativedelta

def solve(year: int, month: int, weekday: int, n: int) -> str:
    d = datetime.date(year, month, 1)
    count = 0
    while d.month == month:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d.isoformat()
        d += dateutil.relativedelta.relativedelta(days=+1)
    raise ValueError('not found')
