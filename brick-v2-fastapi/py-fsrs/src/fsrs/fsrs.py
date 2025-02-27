"""
fsrs.fsrs
---------

This module defines the FSRS scheduler.

Classes:
    FSRS: The FSRS scheduler.
"""

from .models import (
    Card,
    ReviewLog,
    Rating,
    State,
    SchedulingCards,
    SchedulingInfo,
    Parameters,
)
import math
from datetime import datetime, timezone, timedelta
from typing import Optional
import copy


class FSRS:
    """
    The FSRS scheduler.

    Enables the reviewing and future scheduling of cards according to the FSRS algorithm.

    Attributes:
        p (Parameters): Object for configuring the scheduler's model weights, desired retention and maximum interval.
        DECAY (float): Constant used to model the forgetting curve and compute the length of a Card's next interval after being repeated.
        FACTOR (float): Constant used to model the forgetting curve and compute the length of a Card's next interval after being repeated.
    """

    p: Parameters
    DECAY: float
    FACTOR: float

    def __init__(
        self,
        w: Optional[tuple[float, ...]] = None,
        request_retention: Optional[float] = None,
        maximum_interval: Optional[int] = None,
    ) -> None:
        """
        Initializes the FSRS scheduler.

        Args:
            w (Optional[tuple[float, ...]]): The 19 model weights of the FSRS scheduler.
            request_retention (Optional[float]): The desired retention of the scheduler. Corresponds to the maximum retrievability a Card object can have before it is due.
            maximum_interval (Optional[int]): The maximum number of days into the future a Card object can be scheduled for next review.
        """
        self.p = Parameters(w, request_retention, maximum_interval)
        self.DECAY = -0.5
        self.FACTOR = 0.9 ** (1 / self.DECAY) - 1

    def review_card(
        self, card: Card, rating: Rating, weight: Optional[float] = 1, now: Optional[datetime] = None
    ) -> tuple[Card, ReviewLog]:
        """
        Reviews a card for a given rating.

        Args:
            card (Card): The card being reviewed.
            rating (Rating): The chosen rating for the card being reviewed.
            now (Optional[datetime]): The date and time of the review.

        Returns:
            tuple: A tuple containing the updated, reviewed card and its corresponding review log.

        Raises:
            ValueError: If the `now` argument is not timezone-aware and set to UTC.
        """
        scheduling_cards = self.repeat(card, now, weight)

        card = scheduling_cards[rating].card
        review_log = scheduling_cards[rating].review_log

        return card, review_log

    def repeat(
        self, card: Card, now: Optional[datetime] = None, weight: Optional[float] = 1
    ) -> dict[Rating, SchedulingInfo]:
        if now is None:
            now = datetime.now(timezone.utc)

        if (now.tzinfo is None) or (now.tzinfo != timezone.utc):
            raise ValueError("datetime must be timezone-aware and set to UTC")

        card = copy.deepcopy(card)
        if card.state == State.New:
            card.elapsed_days = 0
        else:
            card.elapsed_days = (now - card.last_review).days
        card.last_review = now
        card.reps += 1
        s = SchedulingCards(card, weight)
        s.update_state(card.state)

        if card.state == State.New:
            self.init_ds(s)

            s.again.due = now + timedelta(minutes=1 * weight)
            s.hard.due = now + timedelta(minutes=5 * weight)
            s.good.due = now + timedelta(minutes=10 * weight)
            easy_interval = self.next_interval(s.easy.stability)
            s.easy.scheduled_days = easy_interval
            s.easy.due = now + timedelta(days=easy_interval * weight)
        elif card.state == State.Learning or card.state == State.Relearning:
            interval = card.elapsed_days
            last_d = card.difficulty
            last_s = card.stability
            retrievability = self.forgetting_curve(interval, last_s)
            self.next_ds(s, last_d, last_s, retrievability, card.state)

            hard_interval = 0
            good_interval = self.next_interval(s.good.stability)
            easy_interval = max(self.next_interval(s.easy.stability), good_interval + 1)
            s.schedule(now, hard_interval, good_interval, easy_interval)
        elif card.state == State.Review:
            interval = card.elapsed_days
            last_d = card.difficulty
            last_s = card.stability
            retrievability = self.forgetting_curve(interval, last_s)
            self.next_ds(s, last_d, last_s, retrievability, card.state)

            hard_interval = self.next_interval(s.hard.stability)
            good_interval = self.next_interval(s.good.stability)
            hard_interval = min(hard_interval, good_interval)
            good_interval = max(good_interval, hard_interval + 1)
            easy_interval = max(self.next_interval(s.easy.stability), good_interval + 1)
            s.schedule(now, hard_interval, good_interval, easy_interval)
        return s.record_log(card, now)

    def init_ds(self, s: SchedulingCards) -> None:
        s.again.difficulty = self.init_difficulty(Rating.Again)
        s.again.stability = self.init_stability(Rating.Again)
        s.hard.difficulty = self.init_difficulty(Rating.Hard)
        s.hard.stability = self.init_stability(Rating.Hard)
        s.good.difficulty = self.init_difficulty(Rating.Good)
        s.good.stability = self.init_stability(Rating.Good)
        s.easy.difficulty = self.init_difficulty(Rating.Easy)
        s.easy.stability = self.init_stability(Rating.Easy)

    def next_ds(
        self,
        s: SchedulingCards,
        last_d: float,
        last_s: float,
        retrievability: float,
        state: State,
    ) -> None:
        s.again.difficulty = self.next_difficulty(last_d, Rating.Again)
        s.hard.difficulty = self.next_difficulty(last_d, Rating.Hard)
        s.good.difficulty = self.next_difficulty(last_d, Rating.Good)
        s.easy.difficulty = self.next_difficulty(last_d, Rating.Easy)

        if state == State.Learning or state == State.Relearning:
            # compute short term stabilities
            s.again.stability = self.short_term_stability(last_s, Rating.Again)
            s.hard.stability = self.short_term_stability(last_s, Rating.Hard)
            s.good.stability = self.short_term_stability(last_s, Rating.Good)
            s.easy.stability = self.short_term_stability(last_s, Rating.Easy)

        elif state == State.Review:
            s.again.stability = self.next_forget_stability(
                last_d, last_s, retrievability
            )
            s.hard.stability = self.next_recall_stability(
                last_d, last_s, retrievability, Rating.Hard
            )
            s.good.stability = self.next_recall_stability(
                last_d, last_s, retrievability, Rating.Good
            )
            s.easy.stability = self.next_recall_stability(
                last_d, last_s, retrievability, Rating.Easy
            )

    def init_stability(self, r: Rating) -> float:
        return max(self.p.w[r - 1], 0.1)

    def init_difficulty(self, r: Rating) -> float:
        # compute initial difficulty and clamp it between 1 and 10
        return min(max(self.p.w[4] - math.exp(self.p.w[5] * (r - 1)) + 1, 1), 10)

    def forgetting_curve(self, elapsed_days: int, stability: float) -> float:
        return (1 + self.FACTOR * elapsed_days / stability) ** self.DECAY

    def next_interval(self, s: float) -> int:
        new_interval = (
            s / self.FACTOR * (self.p.request_retention ** (1 / self.DECAY) - 1)
        )
        return min(max(round(new_interval), 1), self.p.maximum_interval)

    def next_difficulty(self, d: float, r: Rating) -> float:
        next_d = d - self.p.w[6] * (r - 3)

        return min(
            max(self.mean_reversion(self.init_difficulty(Rating.Easy), next_d), 1), 10
        )

    def short_term_stability(self, stability: float, rating: Rating) -> float:
        return stability * math.exp(self.p.w[17] * (rating - 3 + self.p.w[18]))

    def mean_reversion(self, init: float, current: float) -> float:
        return self.p.w[7] * init + (1 - self.p.w[7]) * current

    def next_recall_stability(
        self, d: float, s: float, r: float, rating: Rating
    ) -> float:
        hard_penalty = self.p.w[15] if rating == Rating.Hard else 1
        easy_bonus = self.p.w[16] if rating == Rating.Easy else 1
        return s * (
            1
            + math.exp(self.p.w[8])
            * (11 - d)
            * math.pow(s, -self.p.w[9])
            * (math.exp((1 - r) * self.p.w[10]) - 1)
            * hard_penalty
            * easy_bonus
        )

    def next_forget_stability(self, d: float, s: float, r: float) -> float:
        return (
            self.p.w[11]
            * math.pow(d, -self.p.w[12])
            * (math.pow(s + 1, self.p.w[13]) - 1)
            * math.exp((1 - r) * self.p.w[14])
        )
        
    def approximate_retrievability(self, card: Card):
        interval = card.elapsed_days
        retrievability = self.forgetting_curve(interval, card.stability)
        return retrievability
