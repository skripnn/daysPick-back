def phone_format(p: str):
    return f'+{p[0]} ({p[1:4]}) {p[4:7]}-{p[7:9]}-{p[9:]}'