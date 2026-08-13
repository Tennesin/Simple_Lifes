from .ci_settings import *
from ...all_needed import geometry

class CreaturePsyche:

    def __init__(self, creature):
        self.c = creature
        self.joy = 0.0            # Грусть <-> Счастье
        self.satisfaction = 0.0   # Разочарование <-> Довольство
        self.calmness = 0.0       # Тревога <-> Спокойствие
        self.confidence = 0.0     # Неуверенность <-> Уверенность
        self.attachment = 0.0     # Отчуждённость <-> Привязанность

    # ---------- Тик ----------

    def update(self, dt):
        decay = PSYCHE_DECAY_RATE * dt
        self.joy = self._decay_towards_zero(self.joy, decay)
        self.satisfaction = self._decay_towards_zero(self.satisfaction, decay)
        self.calmness = self._decay_towards_zero(self.calmness, decay)
        self.confidence = self._decay_towards_zero(self.confidence, decay)
        self.attachment = self._decay_towards_zero(self.attachment, decay)

    @staticmethod
    def _decay_towards_zero(value, step):
        if value > 0:
            return max(0.0, value - step)
        if value < 0:
            return min(0.0, value + step)
        return value

    def _adjust(self, attr, delta):
        current = getattr(self, attr)
        setattr(self, attr, geometry.clamp(current + delta, PSYCHE_STAT_MIN, PSYCHE_STAT_MAX))

    # ---------- События ----------

    def on_pet(self):
        self._adjust("joy", PSYCHE_PET_BONUS)
        self._adjust("satisfaction", PSYCHE_PET_BONUS)
        self._adjust("calmness", PSYCHE_PET_BONUS)
        self._adjust("attachment", PSYCHE_PET_BONUS * 0.5)

    def on_hit(self):
        self._adjust("joy", PSYCHE_HIT_PENALTY)
        self._adjust("satisfaction", PSYCHE_HIT_PENALTY)
        self._adjust("calmness", PSYCHE_HIT_PENALTY)
        self._adjust("confidence", PSYCHE_HIT_PENALTY * 0.5)
        self._adjust("attachment", PSYCHE_HIT_PENALTY * 0.4)

    def on_grab_release(self, outcome):
        if outcome == "better":
            self._adjust("satisfaction", PSYCHE_GRAB_GOOD_BONUS)
            self._adjust("calmness", PSYCHE_GRAB_GOOD_BONUS * 0.5)
        elif outcome == "worse":
            self._adjust("satisfaction", PSYCHE_GRAB_BAD_PENALTY)
            self._adjust("calmness", PSYCHE_GRAB_BAD_PENALTY)
            self._adjust("confidence", PSYCHE_GRAB_BAD_PENALTY * 0.5)

    def on_talk(self, dt, relationship, gender_bonus=1.0):
        sign = 1.0 if relationship >= 0 else -0.4
        rate = PSYCHE_TALK_JOY_RATE * sign * gender_bonus * dt
        self._adjust("joy", rate)
        self._adjust("satisfaction", rate * 0.7)
        self._adjust("calmness", rate * 0.5)
        if relationship > 0:
            self._adjust("attachment", PSYCHE_TALK_ATTACHMENT_RATE * gender_bonus * dt)

    def on_child_road_play(self, dt):
        rate = PSYCHE_CHILD_ROAD_PLAY_RATE * dt
        self._adjust("joy", rate)
        self._adjust("satisfaction", rate * 0.6)
        self._adjust("calmness", rate * 0.3)

    def on_quarrel(self):
        self._adjust("joy", PSYCHE_QUARREL_PENALTY)
        self._adjust("satisfaction", PSYCHE_QUARREL_PENALTY)
        self._adjust("calmness", PSYCHE_QUARREL_PENALTY)

    def on_help_given(self):
        self._adjust("satisfaction", PSYCHE_HELP_GIVER_BONUS)
        self._adjust("confidence", PSYCHE_HELP_GIVER_BONUS * 0.5)

    def on_help_received(self):
        self._adjust("joy", PSYCHE_HELP_RECEIVER_BONUS)
        self._adjust("attachment", PSYCHE_HELP_RECEIVER_BONUS * 0.6)

    def on_pair_formed(self):
        self._adjust("joy", PSYCHE_PAIR_BONUS)
        self._adjust("satisfaction", PSYCHE_PAIR_BONUS)
        self._adjust("attachment", PSYCHE_PAIR_BONUS)

    def on_partner_lost(self):
        self._adjust("joy", PSYCHE_PARTNER_LOSS_PENALTY)
        self._adjust("satisfaction", PSYCHE_PARTNER_LOSS_PENALTY)
        self._adjust("calmness", PSYCHE_PARTNER_LOSS_PENALTY * 0.6)
        self._adjust("attachment", PSYCHE_PARTNER_LOSS_PENALTY * 0.5)

    def on_birth(self):
        self._adjust("joy", PSYCHE_BIRTH_BONUS)
        self._adjust("satisfaction", PSYCHE_BIRTH_BONUS)
        self._adjust("attachment", PSYCHE_BIRTH_BONUS * 0.5)

    def on_territory_intruded(self):
        """У НАРУШИТЕЛЯ, которого прогнали с чужой территории."""
        self._adjust("calmness", PSYCHE_TERRITORY_INTRUDER_PENALTY)
        self._adjust("confidence", PSYCHE_TERRITORY_INTRUDER_PENALTY * 0.6)

    def on_territory_defended(self):
        """У ХОЗЯИНА территории, прогнавшего чужака."""
        self._adjust("confidence", PSYCHE_TERRITORY_OWNER_BONUS)

    def on_hazard_encountered(self):
        self._adjust("calmness", PSYCHE_HAZARD_PENALTY)
        self._adjust("confidence", PSYCHE_HAZARD_PENALTY * 0.4)

    # ---------- Влияние на поведение (заглушки/лёгкие хуки) ----------

    def curiosity_modifier(self):
        """Уверенные и спокойные существа охотнее интересуются новым."""
        score = (self.confidence + self.calmness) / 2.0
        return max(0.4, 1.0 + (score / 100.0) * PSYCHE_CURIOSITY_INFLUENCE)

    def freeze_modifier(self):
        """Тревожные существа чаще замирают, уверенные - реже."""
        raw = -self.calmness - self.confidence * 0.5
        return max(0.3, 1.0 + (raw / 100.0) * PSYCHE_FREEZE_INFLUENCE)

    def quarrel_modifier(self):
        """Плохое настроение делает существо конфликтнее."""
        score = (self.joy + self.satisfaction + self.calmness) / 3.0
        return max(0.3, 1.0 - (score / 100.0) * PSYCHE_QUARREL_INFLUENCE)

    def pairing_relationship_discount(self):
        """Привязанные легче образуют пару (порог ниже), отчуждённые - тяжелее."""
        return (self.attachment / 100.0) * PSYCHE_ATTACHMENT_PAIR_INFLUENCE

    def wellbeing_modifier(self):
        """Небольшая добавка к общему самочувствию - специально с малым весом,
        чтобы не перекрывать физические показатели."""
        score = (self.joy + self.satisfaction + self.calmness) / 3.0
        return (score / 100.0) * 0.08

    def speed_modifier(self):
        """Уверенность и радость слегка ускоряют движение,
        подавленность и неуверенность - замедляют."""
        score = (self.confidence + self.joy) / 2.0
        return max(0.85, 1.0 + (score / 100.0) * PSYCHE_SPEED_INFLUENCE)

    def territory_boldness(self):
        """Насколько существо готово идти на конфронтацию с чужаком
        прямо сейчас. 0..1 - шанс реально среагировать на вторжение,
        а не отступить в этот раз."""
        score = (self.confidence + self.calmness) / 2.0
        return geometry.clamp(0.5 + (score / 100.0) * PSYCHE_TERRITORY_BOLDNESS_INFLUENCE, 0.0, 1.0)

    def empathy_threshold_discount(self):
        """Привязанность снижает планку отношений, необходимую,
        чтобы пойти на помощь страдающему сородичу."""
        return (self.attachment / 100.0) * PSYCHE_EMPATHY_THRESHOLD_INFLUENCE

    def helpfulness_modifier(self):
        """Довольство и радость делают существо щедрее и охотнее
        помогающим в стройке / готовым делиться едой."""
        score = (self.satisfaction + self.joy) / 2.0
        return max(0.4, 1.0 + (score / 100.0) * PSYCHE_HELPFULNESS_INFLUENCE)

    def social_response_chance(self):
        """Шанс реально откликнуться на просьбу компании -
        отчуждённые и подавленные иногда просто не идут."""
        score = (self.joy + self.attachment) / 2.0
        return geometry.clamp(0.6 + (score / 100.0) * PSYCHE_SOCIAL_RESPONSE_INFLUENCE, 0.0, 1.0)

    def jealousy_modifier(self):
        """Тревожные и неуверенные ревнуют сильнее и чаще."""
        raw = -self.calmness - self.confidence * 0.5
        return max(0.5, 1.0 + (raw / 100.0) * PSYCHE_JEALOUSY_INFLUENCE)

    def on_desert_exposure(self, dt):
        """Пустыня медленно давит на тревожность, пока существо в ней находится."""
        self._adjust("calmness", -DESERT_CALMNESS_PENALTY_PER_SEC * dt)