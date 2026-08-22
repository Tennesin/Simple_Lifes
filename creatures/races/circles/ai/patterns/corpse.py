from .....all_needed.ai.utility import Consideration, GoalComponent

# =========================================================================
# Труп сородича / кладбище
# =========================================================================

class CorpseHandling(GoalComponent):
    SCORE_COMMITTED = 60.0
    SCORE_NEW = 50.0

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

    def consider(self, ctx):
        c = self.c
        if not c.can_handle_corpses():
            return [None]
        committed = c.burial_target_id is not None
        has_alert = c.graveyard_alert_timer > 0
        if not ctx.visible_corpses and not committed and not has_alert:
            return [None]
        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW

        def execute():
            return self.instincts.pursue_corpse_burial(ctx.visible_corpses, ctx.graveyards)

        return [Consideration("corpse_burial", score, execute)]