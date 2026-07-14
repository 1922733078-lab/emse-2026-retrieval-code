import dateutil.parser

def solve(s: str) -> str:
    return dateutil.parser.parse(s).date().isoformat()
