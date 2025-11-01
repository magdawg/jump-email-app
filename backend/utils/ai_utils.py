import anthropic
from backend.config import ANTHROPIC_API_KEY

anthropic_client = (
    anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
)


def categorize_email(email_content: str, categories: list) -> int:
    """Use AI to categorize email, or keyword matching as fallback"""
    if not categories:
        return None

    if not anthropic_client:
        return categorize_email_keywords(email_content, categories)

    try:
        category_text = "\n".join(
            [f"- {cat.name}: {cat.description}" for cat in categories]
        )

        prompt = f"""Given this email, categorize it into one of these categories:

{category_text}

Email:
{email_content[:2000]}

Respond with ONLY the category name, nothing else."""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        category_name = message.content[0].text.strip()

        for cat in categories:
            if cat.name.lower() in category_name.lower():
                return cat.id

        return categories[0].id if categories else None
    except Exception as e:
        print(f"AI categorization failed, falling back to keywords: {e}")
        return categorize_email_keywords(email_content, categories)


def categorize_email_keywords(email_content: str, categories: list) -> int:
    """Simple keyword-based categorization"""
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

    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    else:
        return categories[0].id


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
