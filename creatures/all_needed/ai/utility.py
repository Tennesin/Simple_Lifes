
class Consideration:
    __slots__ = ("name", "score", "execute")

    def __init__(self, name, score, execute):
        self.name = name
        self.score = score
        self.execute = execute

def pick_best(considerations, min_score=0.0001):
    valid = [c for c in considerations if c is not None and c.score > min_score]
    valid.sort(key=lambda c: c.score, reverse=True)
    for c in valid:
        goal = c.execute()
        if goal is not None:
            return goal
    return None

def clamp01(value):
    return max(0.0, min(1.0, value))

def scale(value, lo, hi):
    if hi <= lo:
        return 0.0
    return clamp01((value - lo) / (hi - lo))


# =========================================================================
# Домен: базовый контракт компонента принятия решений
# =========================================================================

class GoalComponent:
    """Общий интерфейс всех компонентов принятия решений, независимо от расы."""
    def consider(self, ctx):
        raise NotImplementedError

def lookup_creature(other_creatures, target_id, other_by_id=None, alive_only=False):
    """Универсальный поиск существа по id"""
    if target_id is None:
        return None
    if other_by_id is not None:
        found = other_by_id.get(target_id)
        if found is not None and (not alive_only or not found.is_dead):
            return found
        return None
    for o in other_creatures:
        if o.id == target_id and (not alive_only or not o.is_dead):
            return o
    return None