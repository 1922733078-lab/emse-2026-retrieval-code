import dateutil.parser

def solve(s: str) -> str:
    return dateutil.parser.isoparse(s).isoformat()
