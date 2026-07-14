import dateutil.easter
import dateutil.relativedelta

def solve(year: int) -> str:
    e = dateutil.easter.easter(year)
    return (e + dateutil.relativedelta.relativedelta(days=-2)).isoformat()
