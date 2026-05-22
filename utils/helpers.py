from datetime import datetime


def is_weekend() -> bool:
    return datetime.now().weekday() >= 5