"""
Unit tests for the fresher_filter module.

This module tests the filtering logic for fresher-level SDE roles,
including negative pattern matching and positive signal scoring.
"""

from __future__ import annotations

import pandas as pd
import pytest

from jobspy.fresher_filter import (
    is_negative_match,
    score_positive_signals,
    filter_fresher_jobs,
    NEGATIVE_PATTERNS,
    POSITIVE_PATTERNS,
)


# =============================================================================
# NEGATIVE PATTERN TESTS
# =============================================================================

class TestNegativePatterns:
    """Tests for is_negative_match function - jobs that should be dropped."""

    def test_negative_years_experience(self):
        """Should match jobs requiring 2+ years of experience."""
        assert is_negative_match("Software Engineer - 3 years experience required")
        assert is_negative_match("Looking for 5+ years of experience")
        assert is_negative_match("Minimum 2 years exp needed")

    def test_negative_minimum_years(self):
        """Should match jobs with minimum years requirement."""
        assert is_negative_match("Minimum 3 years experience")
        assert is_negative_match("MINIMUM 5 YEARS")

    def test_negative_senior_title(self):
        """Should match senior-level titles."""
        assert is_negative_match("Senior Software Engineer")
        assert is_negative_match("Sr.Developer")  # No space after dot for word boundary

    def test_negative_lead_title(self):
        """Should match lead-level titles."""
        assert is_negative_match("Tech Lead - Python")
        assert is_negative_match("Lead Developer")

    def test_negative_staff_engineer(self):
        """Should match staff engineer titles."""
        assert is_negative_match("Staff Engineer - Backend")

    def test_negative_principal(self):
        """Should match principal-level titles."""
        assert is_negative_match("Principal Software Engineer")

    def test_negative_manager(self):
        """Should match management roles."""
        assert is_negative_match("Engineering Manager")

    def test_negative_director(self):
        """Should match director-level roles."""
        assert is_negative_match("Director of Engineering")

    def test_negative_previous_experience_required(self):
        """Should match jobs requiring previous experience."""
        assert is_negative_match("Previous experience required in Python")

    def test_negative_proven_track_record(self):
        """Should match jobs requiring proven track record."""
        assert is_negative_match("Proven track record in software development")

    def test_negative_case_insensitive(self):
        """Patterns should match regardless of case."""
        assert is_negative_match("SENIOR DEVELOPER")
        assert is_negative_match("Senior Developer")
        assert is_negative_match("senior developer")

    def test_negative_no_false_positives(self):
        """Should not match fresher-friendly text."""
        assert not is_negative_match("Freshers welcome")
        assert not is_negative_match("0-1 years experience okay")
        assert not is_negative_match("New graduate opportunity")


# =============================================================================
# POSITIVE PATTERN TESTS
# =============================================================================

class TestPositivePatterns:
    """Tests for score_positive_signals function - fresher-friendly signals."""

    def test_positive_zero_one_years(self):
        """Should match 0-1 years experience patterns."""
        signals, score = score_positive_signals("Looking for 0-1 years experience")
        assert score == 1
        assert "0-1 years" in signals[0]

    def test_positive_freshers_welcome(self):
        """Should match freshers welcome patterns."""
        signals, score = score_positive_signals("Freshers welcome to apply")
        assert score == 1
        assert "Freshers welcome" in signals[0]

    def test_positive_no_experience_required(self):
        """Should match no experience required patterns."""
        signals, score = score_positive_signals("No experience required for this role")
        assert score == 1
        assert "No experience required" in signals[0]

    def test_positive_campus_hiring(self):
        """Should match campus hiring patterns."""
        signals, score = score_positive_signals("Campus hiring for 2024 batch")
        # Matches both "Campus hiring" and "2024 batch" patterns
        assert score == 2
        assert any("Campus" in s for s in signals)

    def test_positive_new_grad(self):
        """Should match new graduate patterns."""
        signals, score = score_positive_signals("New Grad Software Engineer")
        assert score == 1
        assert "New Grad" in signals[0]

        signals, score = score_positive_signals("New Graduate opportunity")
        assert score == 1

    def test_positive_entry_level(self):
        """Should match entry-level patterns."""
        signals, score = score_positive_signals("Entry-level developer position")
        assert score == 1
        assert "Entry-level" in signals[0] or "Entry level" in signals[0]

    def test_positive_batch_2024(self):
        """Should match 2024 batch patterns."""
        signals, score = score_positive_signals("Batch of 2024 graduates")
        assert score == 1

        signals, score = score_positive_signals("2024 batch passout")
        assert score == 1

    def test_positive_recent_graduate(self):
        """Should match recent graduate patterns."""
        signals, score = score_positive_signals("Recent graduate welcome")
        assert score == 1
        assert "Recent graduate" in signals[0]

    def test_positive_just_graduated(self):
        """Should match just graduated patterns."""
        signals, score = score_positive_signals("Just graduated? Apply now!")
        assert score == 1
        assert "Just graduated" in signals[0]

    def test_positive_multiple_signals(self):
        """Should count multiple signals in one text."""
        text = "Freshers welcome! 0-1 years experience. New Grad opportunity."
        signals, score = score_positive_signals(text)
        assert score >= 2
        assert len(signals) >= 2

    def test_positive_case_insensitive(self):
        """Patterns should match regardless of case."""
        signals, score = score_positive_signals("FRESHERS WELCOME")
        assert score == 1

    def test_positive_empty_text(self):
        """Should handle empty text gracefully."""
        signals, score = score_positive_signals("")
        assert score == 0
        assert signals == []

    def test_positive_no_matches(self):
        """Should return empty for text with no positive signals."""
        signals, score = score_positive_signals("Senior Developer with 10 years experience")
        assert score == 0
        assert signals == []


# =============================================================================
# FILTER FUNCTION TESTS
# =============================================================================

class TestFilterFresherJobs:
    """Tests for filter_fresher_jobs function - main filtering logic."""

    def test_empty_dataframe(self, capsys):
        """Should handle empty DataFrame gracefully."""
        df = pd.DataFrame()
        result = filter_fresher_jobs(df)
        assert result.empty

        captured = capsys.readouterr()
        assert "Fetched 0 jobs" in captured.out

    def test_drops_negative_matches(self):
        """Should drop jobs matching negative patterns."""
        data = {
            "title": [
                "Senior Software Engineer",
                "Fresher Developer",
                "Manager - Engineering",
                "Entry Level Python",
            ],
            "description": [
                "5 years experience required",
                "Freshers welcome",
                "Lead a team of 10",
                "New grad opportunity",
            ],
        }
        df = pd.DataFrame(data)
        result = filter_fresher_jobs(df)

        # Should drop Senior and Manager, keep Fresher and Entry Level
        assert len(result) == 2
        assert "Fresher Developer" in result["title"].values
        assert "Entry Level Python" in result["title"].values

    def test_adds_fresher_columns(self):
        """Should add fresher_signals and fresher_score columns."""
        data = {
            "title": ["Fresher Developer"],
            "description": ["Freshers welcome! 0-1 years experience."],
        }
        df = pd.DataFrame(data)
        result = filter_fresher_jobs(df)

        assert "fresher_signals" in result.columns
        assert "fresher_score" in result.columns
        assert result["fresher_score"].iloc[0] == 2

    def test_preserves_original_columns(self):
        """Should preserve all original DataFrame columns."""
        data = {
            "title": ["Developer"],
            "description": ["Entry-level position"],
            "company": ["Tech Corp"],
            "location": ["Bangalore"],
        }
        df = pd.DataFrame(data)
        result = filter_fresher_jobs(df)

        assert "title" in result.columns
        assert "description" in result.columns
        assert "company" in result.columns
        assert "location" in result.columns

    def test_verbose_logging(self, capsys):
        """Should log dropped jobs when verbose=True."""
        data = {
            "title": ["Senior Developer"],
            "description": ["5 years experience"],
        }
        df = pd.DataFrame(data)
        filter_fresher_jobs(df, verbose=True)

        captured = capsys.readouterr()
        assert "Fetched 1 jobs" in captured.out
        assert "0 passed fresher filter" in captured.out
        assert "DROPPED" in captured.out or "--- Dropped Jobs ---" in captured.out

    def test_combined_text_checking(self):
        """Should check both title and description together."""
        # Title looks senior but description says entry-level
        data = {
            "title": ["Developer"],  # Not "Senior"
            "description": ["Entry-level position for fresh graduates"],
        }
        df = pd.DataFrame(data)
        result = filter_fresher_jobs(df)

        # Should be kept because title doesn't have negative patterns
        assert len(result) == 1

        # Now test with negative in description
        data2 = {
            "title": ["Developer"],
            "description": ["Minimum 5 years experience required"],
        }
        df2 = pd.DataFrame(data2)
        result2 = filter_fresher_jobs(df2)

        # Should be dropped because description has negative pattern
        assert len(result2) == 0


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_none_text(self):
        """Should handle None input gracefully."""
        assert not is_negative_match(None)
        signals, score = score_positive_signals(None)
        assert score == 0
        assert signals == []

    def test_special_characters(self):
        """Should handle special characters in text."""
        text = "Freshers welcome! @#$%^&*() 0-1 years experience"
        signals, score = score_positive_signals(text)
        assert score == 2

    def test_very_long_text(self):
        """Should handle very long job descriptions."""
        long_description = "Freshers welcome! " * 100 + "Entry-level position."
        signals, score = score_positive_signals(long_description)
        assert score >= 1

    def test_partial_matches(self):
        """Should not match partial words incorrectly."""
        # "seniority" contains "senior" but shouldn't match
        assert not is_negative_match("This role has seniority progression")

    def test_numbers_in_context(self):
        """Should correctly interpret year requirements."""
        # 0-1 years should NOT trigger negative (pattern is 2-9)
        assert not is_negative_match("0-1 years experience")
        assert not is_negative_match("0-2 years okay")
        # But 2+ years should trigger negative
        assert is_negative_match("2 years experience")
        assert is_negative_match("5+ years of experience")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
