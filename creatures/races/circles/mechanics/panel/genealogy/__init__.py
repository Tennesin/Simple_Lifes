"""Древо Родословной - публичный API подпакета genealogy/.
GenealogyLayoutBuilder (чистый алгоритм) наружу не отдаётся - им пользуется
только сам GenealogyTreeOverlay."""

from .overlay import GenealogyTreeOverlay

__all__ = ["GenealogyTreeOverlay"]