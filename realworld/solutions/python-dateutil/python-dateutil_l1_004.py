import dateutil.easter

def solve(year: int) -> str:
    return dateutil.easter.easter(year).isoformat()
