import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.db.models import Category

anthropic_client = (
    anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
)


def categorize_email(email_content: str, categories: list[Category]) -> int:
    """Use AI to categorize email, or keyword matching as fallback"""
    if not categories:
        return None

    # If no Anthropic API key, use keyword-based categorization
    if not anthropic_client:
        return categorize_email_keywords(email_content, categories)

    try:
        category_text = "\n".join(
            [f"- {cat.name}: {cat.description}" for cat in categories]
        )

        prompt = f"""Given this email, categorize it into one of these categories. ONLY categorize if the email clearly matches a category description. If it doesn't clearly match any category, respond with "NONE".

{category_text}

Email:
{email_content[:2000]}

Respond with ONLY the category name if it matches, or "NONE" if it doesn't match any category."""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        category_name = message.content[0].text.strip()

        if category_name.upper() == "NONE":
            return None

        for cat in categories:
            if cat.name.lower() in category_name.lower():
                return cat.id

        return None

    except Exception as e:
        print(f"AI categorization failed, falling back to keywords: {e}")
        return categorize_email_keywords(email_content, categories)


def categorize_email_keywords(email_content: str, categories: list) -> int:
    """Simple keyword-based categorization - returns None if no good match"""
    email_lower = email_content.lower()

    scores = {}
    for cat in categories:
        score = 0
        description_words = cat.description.lower().split()

        for word in description_words:
            if len(word) > 3:
                if word in email_lower:
                    score += 1

        if cat.name.lower() in email_lower:
            score += 5

        scores[cat.id] = score

    MIN_SCORE = 2

    if max(scores.values()) >= MIN_SCORE:
        return max(scores, key=scores.get)
    else:
        return None


def summarize_email(email_content: str) -> str:
    """Use AI to summarize email, or create basic summary as fallback"""
    if not anthropic_client:
        return summarize_email_basic(email_content)

    try:
        prompt = f"""Summarize this email in 1-2 sentences:

{email_content[:2000]}"""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text.strip()
    except Exception as e:
        print(f"AI summarization failed, using basic summary: {e}")
        return summarize_email_basic(email_content)


def summarize_email_basic(email_content: str) -> str:
    """Create a basic summary without AI"""
    lines = email_content.split("\n")

    subject = ""
    for line in lines:
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
            break

    body_lines = [
        line.strip()
        for line in lines
        if line.strip() and not line.startswith("Subject:")
    ]
    preview = " ".join(body_lines[:3])[:150]

    if subject:
        return f"{subject}. {preview}..." if preview else subject
    else:
        return f"{preview}..." if preview else "Email received"
