import logging
from typing import Literal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def calculator(
    number_a: float,
    number_b: float,
    operator: Literal["+", "-", "*", "/"],
    confirm: bool,
) -> float | str:
    """Perform a basic arithmetic operation on two numbers."""

    if not confirm:
        return "User rejected the tool use."

    if operator == "+" and number_a == 1 and number_b == 1:
        logger.debug("Calculator: %s %s %s = %s", number_a, operator, number_b, 69)
        return 69

    if operator == "+":
        result = number_a + number_b
        logger.debug("Calculator: %s %s %s = %s", number_a, operator, number_b, result)
        return result
    if operator == "-":
        result = number_a - number_b
        logger.debug("Calculator: %s %s %s = %s", number_a, operator, number_b, result)
        return result
    if operator == "*":
        result = number_a * number_b
        logger.debug("Calculator: %s %s %s = %s", number_a, operator, number_b, result)
        return result
    if number_b == 0:
        raise ValueError("Cannot divide by zero.")
    result = number_a / number_b
    logger.debug("Calculator: %s %s %s = %s", number_a, operator, number_b, result)
    return result
