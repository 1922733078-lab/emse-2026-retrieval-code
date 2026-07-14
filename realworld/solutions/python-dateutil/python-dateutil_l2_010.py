import dateutil.parser

def solve(s: str) -> int:
    return dateutil.parser.isoparse(s).toordinal()
