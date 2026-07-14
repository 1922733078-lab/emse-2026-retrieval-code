import datetime
import dateutil.easter

def solve(year: int) -> int:
    return (dateutil.easter.easter(year) - datetime.date(year, 1, 1)).days
