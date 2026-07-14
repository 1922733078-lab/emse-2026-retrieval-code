import dateutil.easter

def solve(year: int, method: int) -> str:
    return dateutil.easter.easter(year, method).isoformat()
