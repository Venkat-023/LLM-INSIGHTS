"""
utils/cost_calculator.py – Estimates the USD cost of an OpenAI API call.

Prices are per 1 000 tokens (as of mid-2025 pricing).
Update the PRICE_TABLE if OpenAI changes rates.
"""

# ── Pricing table (USD per 1 000 tokens) ─────────────────────────────────────
# Format: model_name → {"input": price, "output": price}
PRICE_TABLE: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.0004,  "output": 0.0016},
    "gpt-4.1":      {"input": 0.002,   "output": 0.008},
    "gpt-4o":       {"input": 0.005,   "output": 0.015},
    "gpt-4o-mini":  {"input": 0.00015, "output": 0.0006},
    "gpt-4":        {"input": 0.03,    "output": 0.06},
    "gpt-3.5-turbo":{"input": 0.0005,  "output": 0.0015},
}

# Fallback price if model is not in the table
FALLBACK_PRICE = {"input": 0.001, "output": 0.002}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate the USD cost of a single OpenAI API call.

    Args:
        model: Model name, e.g. "gpt-4.1-mini"
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion

    Returns:
        Estimated cost in USD (rounded to 8 decimal places)
    """
    prices = PRICE_TABLE.get(model, FALLBACK_PRICE)
    input_cost  = (prompt_tokens / 1000) * prices["input"]
    output_cost = (completion_tokens / 1000) * prices["output"]
    return round(input_cost + output_cost, 8)


def format_cost(cost: float) -> str:
    """Format a cost value as a human-readable USD string."""
    if cost < 0.0001:
        return f"${cost:.8f}"
    if cost < 0.01:
        return f"${cost:.6f}"
    return f"${cost:.4f}"
