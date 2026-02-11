REQUIRED_FIELDS = {"id", "url", "source", "category", "priority"}
VALID_PRIORITIES = {1, 2, 3, 4, 5}

# Validate the article payload
def validate_article_payload(article: dict):
 
    if not isinstance(article, dict):
        return False, "Article must be a JSON object"

    # Check required fields
    missing = REQUIRED_FIELDS.difference(article.keys())
    if missing:
        return False, f"Missing required field(s): {', '.join(sorted(missing))}"

    # Validate URL
    url = article.get("url")
    if not isinstance(url, str) or not url.strip():
        return False, "Field 'url' must be a non-empty string"

    # Validate ID
    article_id = article.get("id")
    if not isinstance(article_id, (int, str)):
        return False, "Field 'id' must be an int or str"

    # Validate priority
    priority = article.get("priority")
    if not isinstance(priority, int) or priority not in VALID_PRIORITIES:
        return False, f"Field 'priority' must be one of {sorted(VALID_PRIORITIES)}"

    return True, None

