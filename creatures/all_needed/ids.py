"""Единая точка генерации коротких игровых ID."""

import uuid


def new_id():
    return str(uuid.uuid4())[:8]