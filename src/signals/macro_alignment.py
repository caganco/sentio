"""Macro-equity correlation layer: alignment calculator for portfolio positions."""
from __future__ import annotations

import json
from pathlib import Path


class MacroAlignmentCalculator:
    """
    Calculate macro alignment score for each portfolio holding.

    Alignment = how well current macro environment supports the stock.
    Range: [0, 1]
      0.0 = macro headwinds (very negative for this stock)
      0.5 = macro neutral
      1.0 = macro tailwinds (very positive for this stock)
    """

    def __init__(self, sensitivity_profile_path: str | Path = "data/macro_sensitivity.json"):
        self.profile_path = Path(sensitivity_profile_path)
        self.profiles = self._load_profiles()
        self._historical_baselines = {
            "brent": {"value": 100.0, "tolerance": 5.0},
            "usd_try": {"value": 45.0, "tolerance": 2.0},
            "vix": {"value": 20.0, "tolerance": 2.0},
            "cds": {"value": 350.0, "tolerance": 50.0},
        }

    def _load_profiles(self) -> dict:
        """Load and parse macro sensitivity profiles from JSON."""
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("profiles", {})
        except FileNotFoundError:
            raise FileNotFoundError(f"Profile file not found: {self.profile_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in profile file: {e}")

    def calculate_alignment(self, ticker: str, macro_state: dict) -> dict:
        """
        Calculate macro alignment score for a single ticker.

        Args:
            ticker (str): Stock ticker (e.g., "AKSEN")
            macro_state (dict): Current macro data {
                "brent": 104.92,
                "usd_try": 45.43,
                "vix": 17.89,
                "cds": 320
            }

        Returns:
            dict: {
                "ticker": "AKSEN",
                "alignment_score": 0.68,
                "alignment_direction": "+",
                "sensitivity_map": {
                    "brent": {"direction": "+", "score": 0.8, "magnitude": "up"},
                    ...
                },
                "narrative": "Brent strength supports; FX headwind minor"
            }
        """
        profile = self.profiles.get(ticker)
        if not profile:
            return {
                "ticker": ticker,
                "alignment_score": 0.5,
                "alignment_direction": "0",
                "error": f"No profile for {ticker}",
            }

        variable_scores = {}
        for var_name, var_profile in profile["sensitivities"].items():
            current_value = macro_state.get(var_name)
            if current_value is None:
                variable_scores[var_name] = {
                    "score": 0.5,
                    "magnitude": "unknown",
                    "move_direction": "?",
                    "sensitivity_direction": var_profile.get("direction", "0"),
                    "strength": var_profile.get("strength", "none"),
                }
                continue

            score = self._calculate_variable_score(
                var_name=var_name,
                current_value=current_value,
                sensitivity=var_profile,
                historical_baseline=self._historical_baselines.get(var_name, {})
            )
            variable_scores[var_name] = score

        aligned_score = self._aggregate_scores(variable_scores, profile["sensitivities"])
        direction = "+" if aligned_score > 0.55 else ("-" if aligned_score < 0.45 else "0")

        return {
            "ticker": ticker,
            "alignment_score": round(aligned_score, 3),
            "alignment_direction": direction,
            "sensitivity_map": variable_scores,
            "narrative": self._generate_narrative(ticker, profile, variable_scores),
        }

    def _calculate_variable_score(
        self,
        var_name: str,
        current_value: float,
        sensitivity: dict,
        historical_baseline: dict,
    ) -> dict:
        """
        For one variable, calculate score (0-1) based on current value vs baseline.

        Logic:
        - If brent UP and sensitivity "+" (strong) → favorable → 0.8
        - If brent UP and sensitivity "-" (strong) → unfavorable → 0.2
        - If brent FLAT → neutral → 0.5
        """
        baseline_value = historical_baseline.get("value", current_value)
        tolerance = historical_baseline.get("tolerance", 0.01 * baseline_value)

        diff = current_value - baseline_value

        if abs(diff) < tolerance:
            magnitude = "flat"
            move_direction = "0"
        elif diff > 0:
            magnitude = "up"
            move_direction = "+"
        else:
            magnitude = "down"
            move_direction = "-"

        sensitivity_direction = sensitivity.get("direction", "0")
        sensitivity_strength = sensitivity.get("strength", "none")

        strength_weight = {
            "strong": 0.4,
            "medium": 0.25,
            "weak": 0.1,
            "none": 0.0,
        }

        if move_direction == "0":
            score = 0.5
        elif sensitivity_direction == "0":
            score = 0.5
        elif move_direction == sensitivity_direction:
            score = 0.5 + strength_weight.get(sensitivity_strength, 0.0)
        else:
            score = 0.5 - strength_weight.get(sensitivity_strength, 0.0)

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))

        return {
            "score": round(score, 2),
            "magnitude": magnitude,
            "move_direction": move_direction,
            "sensitivity_direction": sensitivity_direction,
            "strength": sensitivity_strength,
        }

    def _aggregate_scores(self, variable_scores: dict, sensitivities: dict) -> float:
        """Weighted average of variable scores, weighted by strength."""
        total_weight = 0
        weighted_sum = 0

        for var_name, var_score in variable_scores.items():
            sensitivity = sensitivities.get(var_name, {})
            strength = sensitivity.get("strength", "none")

            weight_map = {
                "strong": 3,
                "medium": 2,
                "weak": 1,
                "none": 0,
            }
            weight = weight_map.get(strength, 0)

            weighted_sum += var_score["score"] * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return weighted_sum / total_weight

    def _generate_narrative(self, ticker: str, profile: dict, variable_scores: dict) -> str:
        """Generate short narrative (Strategist-friendly)."""
        tailwinds = []
        headwinds = []

        for var_name, score in variable_scores.items():
            if score["score"] > 0.6:
                tailwinds.append(f"{var_name} {score['magnitude']}")
            elif score["score"] < 0.4:
                headwinds.append(f"{var_name} {score['magnitude']}")

        if tailwinds and not headwinds:
            return f"{ticker}: Macro tailwinds ({', '.join(tailwinds)})"
        elif headwinds and not tailwinds:
            return f"{ticker}: Macro headwinds ({', '.join(headwinds)})"
        elif tailwinds and headwinds:
            return f"{ticker}: Mixed (tailwinds: {', '.join(tailwinds)}; headwinds: {', '.join(headwinds)})"
        else:
            return f"{ticker}: Macro neutral"

    def calculate_portfolio_alignment(self, portfolio: list[dict], macro_state: dict) -> list[dict]:
        """
        Calculate alignment for multiple portfolio positions.

        Args:
            portfolio (list[dict]): Portfolio positions with 'ticker' field
            macro_state (dict): Current macro data

        Returns:
            list[dict]: Alignment results for each position
        """
        results = []
        for position in portfolio:
            ticker = position.get("ticker")
            if not ticker:
                continue

            alignment = self.calculate_alignment(ticker, macro_state)
            results.append(alignment)

        return results
