"""
Farming recommendation calculator.

Computes expected number of farming runs needed to upgrade treasure matrix
affixes to target levels, based on the game's probability system.

Key parameters:
- With 刻写券 (engrave coupon): each run drops 3 flawless essences
- 1/24 chance per drop to get the desired essence
- Each affix upgrade attempt consumes 1 random flawless essence
- Upgrade success rates:
  - Affix 1&2 (attribute/secondary): 1→2(60%), 2→3(24%), 3→4(10.9%), 4→5(5%), 5→6(2.7%)
  - Affix 3 (skill): 1→2(10.9%), 2→3(4.2%)
- Failed upgrades give 10 冷却脂 (cooling grease)
- Cooling grease can guarantee success at thresholds:
  - Affix 1&2: 1→2(30), 2→3(60), 3→4(120), 4→5(250), 5→6(450)
  - Affix 3: 1→2(120), 2→3(300)
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Constants ---

DESIRED_ESSENCE_PROB = 1 / 24
"""Probability of getting the desired essence per drop."""

ESSENCES_PER_RUN = 3
"""Number of flawless essences dropped per run (with engrave coupon)."""

# Upgrade success probabilities: level -> success prob for level→level+1
UPGRADE_PROBS_AFFIX_12: dict[int, float] = {
    1: 0.600,
    2: 0.240,
    3: 0.109,
    4: 0.050,
    5: 0.027,
}
"""Affix 1&2 upgrade probabilities."""

UPGRADE_PROBS_AFFIX_3: dict[int, float] = {
    1: 0.109,
    2: 0.042,
}
"""Affix 3 upgrade probabilities."""

# Cooling grease thresholds: level -> grease needed to guarantee level→level+1
GREASE_THRESHOLD_AFFIX_12: dict[int, int] = {
    1: 30,
    2: 60,
    3: 120,
    4: 250,
    5: 450,
}
"""Affix 1&2: grease thresholds per level."""

GREASE_THRESHOLD_AFFIX_3: dict[int, int] = {
    1: 120,
    2: 300,
}
"""Affix 3: grease thresholds per level."""

GREASE_PER_FAIL = 10
"""Cooling grease gained per failed upgrade attempt."""


@dataclass
class UpgradeStepDetail:
    """Detail for upgrading one level step."""

    from_level: int
    """Starting level for this step."""

    to_level: int
    """Target level for this step."""

    success_prob: float
    """Probability of success per attempt."""

    grease_threshold: int
    """Cooling grease needed to guarantee success."""

    expected_attempts: float
    """Expected number of upgrade attempts for this step."""

    expected_essences: float
    """Expected essences consumed (equal to expected_attempts)."""

    expected_grease_gained: float
    """Expected cooling grease gained from failures."""

    expected_grease_used: float
    """Expected cooling grease consumed (only when all attempts fail)."""

    use_grease_at: int | None = None
    """If set, use grease guarantee after this many failures."""


@dataclass
class AffixUpgradeResult:
    """Result for upgrading a single affix from current to target level."""

    affix_name: str
    """Name of the affix (e.g. "基础属性", "附加属性", "技能属性")."""

    current_level: int
    """Current affix level."""

    target_level: int
    """Target affix level."""

    expected_attempts: float = 0.0
    """Total expected number of upgrade attempts."""

    expected_essences_consumed: float = 0.0
    """Total expected essences consumed (each attempt costs 1)."""

    expected_grease_gained: float = 0.0
    """Total expected cooling grease gained from failures."""

    expected_grease_used: float = 0.0
    """Total expected cooling grease used (from guaranteed successes)."""

    steps: list[UpgradeStepDetail] = field(default_factory=list)
    """Per-step breakdown."""


@dataclass
class FarmingRecommendation:
    """Complete farming recommendation."""

    weapon_name: str
    """Name of the weapon."""

    weapon_id: str
    """Weapon ID."""

    affix_results: list[AffixUpgradeResult] = field(default_factory=list)
    """Results for each affix."""

    total_expected_essences: float = 0.0
    """Total expected essences needed across all affixes."""

    total_expected_desired_essences: float = 0.0
    """Total expected desired essences (1/24 of total)."""

    total_expected_runs: float = 0.0
    """Total expected farming runs needed."""

    current_levels: tuple[int, int, int] = (1, 1, 1)
    """Current affix levels (affix1, affix2, affix3)."""

    target_levels: tuple[int, int, int] = (6, 6, 3)
    """Target affix levels (affix1, affix2, affix3)."""


def _compute_single_step(
    success_prob: float,
    grease_threshold: int,
) -> UpgradeStepDetail:
    """
    Compute expected attempts and grease for a single level upgrade step.

    Strategy: attempt upgrades until success or until enough cooling grease
    is accumulated to guarantee success.

    The expected number of attempts when we cap at ``max_attempts`` is:
        E[attempts] = (1 - fail_prob^max_attempts) / success_prob
    where ``max_attempts = ceil(grease_threshold / GREASE_PER_FAIL)``.

    Args:
        success_prob: Probability of success per attempt.
        grease_threshold: Cooling grease needed to guarantee success.

    Returns:
        An UpgradeStepDetail with computed values.
    """
    fail_prob = 1 - success_prob
    max_attempts = (grease_threshold + GREASE_PER_FAIL - 1) // GREASE_PER_FAIL
    # ceil(grease_threshold / GREASE_PER_FAIL)

    # Expected attempts = sum_{i=0}^{max_attempts-1} fail_prob^i
    #                   = (1 - fail_prob^max_attempts) / success_prob
    if success_prob > 0:
        expected_attempts = (1 - fail_prob**max_attempts) / success_prob
    else:
        expected_attempts = max_attempts

    # Expected failures: computed numerically as sum of
    #   (i-1) * P(first success at attempt i) for i=1..max_attempts
    #   + max_attempts * P(all fail)
    expected_failures = 0.0
    for attempt_index in range(1, max_attempts + 1):
        prob_first_success = success_prob * fail_prob ** (attempt_index - 1)
        expected_failures += (attempt_index - 1) * prob_first_success
    prob_all_fail = fail_prob**max_attempts
    expected_failures += max_attempts * prob_all_fail

    grease_gained = expected_failures * GREASE_PER_FAIL
    grease_used = prob_all_fail * grease_threshold

    return UpgradeStepDetail(
        from_level=0,  # filled by caller
        to_level=0,    # filled by caller
        success_prob=success_prob,
        grease_threshold=grease_threshold,
        expected_attempts=expected_attempts,
        expected_essences=expected_attempts,
        expected_grease_gained=grease_gained,
        expected_grease_used=grease_used,
        use_grease_at=max_attempts if prob_all_fail > 0 else None,
    )


def _compute_upgrade_steps(
    current: int,
    target: int,
    upgrade_probs: dict[int, float],
    grease_thresholds: dict[int, int],
    affix_name: str,
) -> AffixUpgradeResult:
    """
    Compute expected attempts and essences to upgrade an affix
    from current to target level.

    Args:
        current: Current affix level.
        target: Target affix level.
        upgrade_probs: Mapping from level to success probability.
        grease_thresholds: Mapping from level to grease threshold.
        affix_name: Display name of the affix.

    Returns:
        An AffixUpgradeResult with per-step breakdown.
    """
    result = AffixUpgradeResult(
        affix_name=affix_name,
        current_level=current,
        target_level=target,
    )

    if current >= target:
        return result

    total_attempts = 0.0
    total_essences = 0.0
    total_grease_gained = 0.0
    total_grease_used = 0.0

    for level in range(current, target):
        success_prob = upgrade_probs.get(level)
        grease_threshold = grease_thresholds.get(level)

        if success_prob is None or grease_threshold is None:
            break

        step = _compute_single_step(success_prob, grease_threshold)
        step.from_level = level
        step.to_level = level + 1
        result.steps.append(step)

        total_attempts += step.expected_attempts
        total_essences += step.expected_essences
        total_grease_gained += step.expected_grease_gained
        total_grease_used += step.expected_grease_used

    result.expected_attempts = total_attempts
    result.expected_essences_consumed = total_essences
    result.expected_grease_gained = total_grease_gained
    result.expected_grease_used = total_grease_used

    return result


def compute_farming_recommendation(
    weapon_id: str,
    weapon_name: str,
    current_levels: tuple[int, int, int],
    target_levels: tuple[int, int, int],
) -> FarmingRecommendation:
    """
    Compute farming recommendation for upgrading a weapon's treasure matrix.

    Args:
        weapon_id: The weapon ID.
        weapon_name: The weapon display name.
        current_levels: Current affix levels (affix1, affix2, affix3).
        target_levels: Target affix levels (affix1, affix2, affix3).

    Returns:
        FarmingRecommendation with detailed breakdown.
    """
    recommendation = FarmingRecommendation(
        weapon_name=weapon_name,
        weapon_id=weapon_id,
        current_levels=current_levels,
        target_levels=target_levels,
    )

    # Affix 1 (attribute): levels 1-6
    recommendation.affix_results.append(
        _compute_upgrade_steps(
            current=current_levels[0],
            target=target_levels[0],
            upgrade_probs=UPGRADE_PROBS_AFFIX_12,
            grease_thresholds=GREASE_THRESHOLD_AFFIX_12,
            affix_name="基础属性",
        )
    )

    # Affix 2 (secondary): levels 1-6
    recommendation.affix_results.append(
        _compute_upgrade_steps(
            current=current_levels[1],
            target=target_levels[1],
            upgrade_probs=UPGRADE_PROBS_AFFIX_12,
            grease_thresholds=GREASE_THRESHOLD_AFFIX_12,
            affix_name="附加属性",
        )
    )

    # Affix 3 (skill): levels 1-3
    recommendation.affix_results.append(
        _compute_upgrade_steps(
            current=current_levels[2],
            target=target_levels[2],
            upgrade_probs=UPGRADE_PROBS_AFFIX_3,
            grease_thresholds=GREASE_THRESHOLD_AFFIX_3,
            affix_name="技能属性",
        )
    )

    # Total essences: each upgrade attempt consumes 1 random flawless essence
    total_essences = sum(
        affix_result.expected_essences_consumed
        for affix_result in recommendation.affix_results
    )
    recommendation.total_expected_essences = total_essences
    recommendation.total_expected_desired_essences = total_essences

    # Runs: each run drops ESSENCES_PER_RUN essences, each with
    # DESIRED_ESSENCE_PROB chance of being the desired one.
    desired_essences_per_run = ESSENCES_PER_RUN * DESIRED_ESSENCE_PROB
    if desired_essences_per_run > 0:
        recommendation.total_expected_runs = (
            total_essences / desired_essences_per_run
        )
    else:
        recommendation.total_expected_runs = float("inf")

    return recommendation
