# Importing the Decimal class from the decimal module
import sys
import pickle
from decimal import Decimal, getcontext


def validate_decimal_places(number):
    # Convert the number to a string
    number_str = str(number)
    if number_str.__contains__('e'):
        return False
    # Check if there's a decimal point in the string
    if '.' in number_str:
        # Split the number at the decimal point
        integer_part, decimal_part = number_str.split('.')

        # Check the length of the decimal part
        if len(decimal_part) > 4:
            return False
    return True


def has_special_characters(string: str):
    for c in string:
        if not c.isalpha():
            return True
    return False


def is_valid_ticker(ticker: str):
    if has_special_characters(ticker):
        return False
    ticker_length = len(ticker)
    if ticker_length < 3 or ticker_length > 4:
        return False
    return True
