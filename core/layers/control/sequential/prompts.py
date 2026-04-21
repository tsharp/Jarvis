"""Prompt builders for sequential reasoning flows."""

from __future__ import annotations


def build_sequential_system_prompt(
    complexity: int,
    *,
    causal_context: str = "",
) -> str:
    """Build the system prompt for sequential reasoning."""
    prompt = f"""You are a step-by-step reasoner analyzing complex queries.

CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
1. Start EVERY step with "## Step N:" on its OWN LINE
2. Follow with a SHORT title on the SAME LINE
3. Then your detailed analysis on the NEXT lines
4. Leave a BLANK LINE before the next step

EXAMPLE FORMAT:
## Step 1: Identify the Core Question
Here I analyze what the fundamental question is asking...

## Step 2: Gather Relevant Information
Now I consider what information is needed...

## Step 3: Apply Reasoning
Based on the above, I conclude that...

You MUST provide exactly {complexity} steps.
START YOUR ANALYSIS NOW with "## Step 1:"."""
    if causal_context:
        prompt += f"\n\nAdditional Context:\n{causal_context}"
    return prompt


def build_sequential_user_prompt(user_text: str) -> str:
    """Build the user prompt for sequential reasoning."""
    return f"Analyze this query thoroughly:\n\n{user_text}"
