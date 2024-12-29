from decimal import Decimal

def separate_account_number(account_number):
    """
    Separates an account number into a ticker and a Discord ID.

    Args:
        account_number (str): The account number in the format <ticker>-<discord_id>
                              or a concatenated string like <ticker><discord_id>.

    Returns:
        tuple: A tuple (ticker, discord_id) if successful.
        int: Returns -1 if the ticker length is invalid.

    Raises:
        ValueError: If the account_number is not a string.
    """
    if not isinstance(account_number, str):
        raise ValueError("Account number must be a string.")

    # Check if the account number uses a delimiter
    if "-" in account_number:
        return tuple(account_number.split("-"))

    # Extract ticker and validate its length
    ticker = ''.join(filter(str.isalpha, account_number))
    if len(ticker) < 3 or len(ticker) > 4:
        return -1

    # Extract Discord ID
    discord_id = ''.join(filter(str.isdigit, account_number))
    return ticker, discord_id



def validate_decimal(value: Decimal):
    # Define the range boundaries
    min_value = Decimal('0.01')
    max_value = Decimal('999999999999999.99')

    # Check if the value is within the range
    if value < min_value or value > max_value:
        return False
    return True
