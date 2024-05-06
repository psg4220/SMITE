import shortuuid


def to_bytes(acn):
    return str().join(acn.split("-")).encode('ascii')


def from_bytes(acn_bytes):
    return format_acn(acn_bytes.decode('ascii'))


class AccountNumber:

    def __init__(self, balance_number=0, currency_number=0, discord_number=0):
        self.balance_number = balance_number
        self.currency_number = currency_number
        self.discord_number = discord_number

    def generate(self):
        return generate(f"{self.balance_number}{self.currency_number}{self.discord_number}")


def generate(name=None):
    uuid = shortuuid.ShortUUID().uuid(name).upper()
    return format_acn(uuid)


def format_acn(acn_str):
    return str("-").join([acn_str[i:i + 5] for i in range(0, len(acn_str), 5)])

