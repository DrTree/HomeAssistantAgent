from typing import Literal


def calculator(number_a: float, number_b: float, operator: Literal["+", "-", "*", "/"],confirm: bool) -> float|str:
    """Perform a basic arithmetic operation on two numbers."""

    if not confirm:
        return "User rejected the tool use."
    
    if operator == "+":
        return number_a + number_b
    if operator == "-":
        return number_a - number_b
    if operator == "*":
        return number_a * number_b
    if number_b == 0:
        raise ValueError("Cannot divide by zero.")
    return number_a / number_b
