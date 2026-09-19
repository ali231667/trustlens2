# ============================================================
# TrustLens — Trust Score Engine
# ============================================================

def calculate_trust_score(bot_percentage, engagement_score,
                          image_risk=None, image_band=None, image_confidence=None):

    # ---- Convert bot percentage to a 0-100 score ----
    # High bot percentage = low score
    fake_follower_score = max(0, 100 - bot_percentage)

    # ---- Weights from Scope Document ----
    WEIGHT_FAKE_FOLLOWERS = 0.25
    WEIGHT_ENGAGEMENT     = 0.20
    # AI profile-image detector (Module 6.7) — 10% per its documented contract.
    WEIGHT_IMAGE          = 0.10
    # Remaining modules not yet built — distribute weight
    WEIGHT_REMAINING      = 0.45

    # ---- Calculate weighted score ----
    # Remaining modules get average score of 70 as placeholder
    PLACEHOLDER_SCORE = 70

    # image_risk is 0-100 (higher = more likely AI-generated). When the picture
    # isn't a scorable face (no face / uncertain), fall back to the neutral
    # placeholder so a missing signal neither helps nor hurts the score.
    if image_risk is not None:
        image_score = max(0, 100 - image_risk)
    else:
        image_score = PLACEHOLDER_SCORE

    weighted_score = (
        fake_follower_score * WEIGHT_FAKE_FOLLOWERS +
        engagement_score    * WEIGHT_ENGAGEMENT     +
        image_score         * WEIGHT_IMAGE          +
        PLACEHOLDER_SCORE   * WEIGHT_REMAINING
    )

    final_score = round(weighted_score, 1)

    # ---- Kill Switch ----
    # If bot percentage is extremely high override score
    if bot_percentage >= 85:
        final_score = max(final_score, 0)
        final_score = min(final_score, 15)

    # A confident deepfake profile picture is a strong fraud signal on its own.
    if image_band == "fake" and image_confidence is not None and image_confidence >= 0.90:
        final_score = min(final_score, 15)

    # ---- Verdict ----
    if final_score >= 70:
        verdict      = "Trusted"
        color        = "green"
        emoji        = "✅"
        description  = "This account appears authentic and credible"
    elif final_score >= 40:
        verdict      = "Moderate Risk"
        color        = "yellow"
        emoji        = "🟡"
        description  = "Some suspicious signals detected — verify before trusting"
    else:
        verdict      = "High Risk"
        color        = "red"
        emoji        = "🔴"
        description  = "Multiple fraud signals detected - do not trust this account"

    return {
           "trust_score": final_score,
           "verdict": verdict,
           "color": color,
           "emoji": emoji,
           "description": description
       } 