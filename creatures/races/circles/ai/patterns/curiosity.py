import random

from ...ci_settings import *
from .....all_needed.ai.utility import Consideration, GoalComponent

# =========================================================================
# Любопытство к неизвестным объектам - общая часть (роль/скидка на интерес),
# специфика реакции ("подойти изучить" vs "мгновенно узнать") - в стратегии
# =========================================================================

class CuriosityStrategy:
    def pursue(self, unknown_harmless, unknown_hazards):
        raise NotImplementedError

class Curiosity(GoalComponent):
    SCORE_BASE = 10.0
    SCORE_CURIOSITY_FACTOR = 10.0

    def __init__(self, creature, strategy):
        self.c = creature
        self.strategy = strategy

    def consider(self, ctx):
        c = self.c
        score = self.SCORE_BASE + c.curiosity * self.SCORE_CURIOSITY_FACTOR

        def execute():
            return self._pursue(ctx)

        return [Consideration("curiosity", score, execute)]

    def _pursue(self, ctx):
        c = self.c
        unknown_harmless = self._collect_unknown_harmless(ctx)
        unknown_hazards = [s for s in ctx.visible_spikes if not c.knowledge["spike"]]

        visible_types_now = {t for t, _ in unknown_harmless}
        if unknown_hazards:
            visible_types_now.add("spike")
        self._roll_curiosity_interest(visible_types_now)

        return self.strategy.pursue(unknown_harmless, unknown_hazards)

    def _collect_unknown_harmless(self, ctx):
        c = self.c
        unknown_harmless = []
        if c.eats_food_type("fruit") and not c.knowledge["fruit"] and ctx.visible_fruits:
            unknown_harmless.append(("fruit", min(ctx.visible_fruits, key=c.distance_to)))
        if not c.knowledge["water"] and ctx.visible_water:
            unknown_harmless.append(("water", min(ctx.visible_water, key=c.distance_to)))
        if not c.knowledge["bush"] and ctx.visible_bushes:
            unknown_harmless.append(("bush", min(ctx.visible_bushes, key=c.distance_to)))
        if not c.knowledge["campfire"] and ctx.visible_campfires:
            unknown_harmless.append(("campfire", min(ctx.visible_campfires, key=c.distance_to)))
        return unknown_harmless

    def _roll_curiosity_interest(self, visible_types_now):
        c = self.c
        for t in list(c.curiosity_rolled):
            if t not in visible_types_now:
                c.curiosity_rolled.discard(t)
                c.curiosity_interested.discard(t)

        chance = CURIOSITY_DISCOVERY_CHANCE.get(c.temperament, 0.3) * c.psyche.curiosity_modifier()
        for t in visible_types_now:
            if t not in c.curiosity_rolled:
                c.curiosity_rolled.add(t)
                if random.random() < chance:
                    c.curiosity_interested.add(t)