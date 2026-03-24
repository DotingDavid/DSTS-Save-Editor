"""Unit tests for EXP and growth stat calculations.

Verifies against actual save data to ensure the formulas match
what the game produces.
"""

import os
import sys
import struct
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import save_crypto
from save_data import (SaveFile, _get_db, get_growth_type, get_exp_for_level,
                        get_growth_stats, get_base_stats, detect_exp_curve)


SAVE_DIR = os.path.join(
    os.environ.get('ProgramFiles(x86)', ''),
    'Steam', 'steamapps', 'common',
    'Digimon Story Time Stranger', 'gamedata', 'savedata'
)


def _find_save():
    """Find the most recent save file for testing."""
    if not os.path.isdir(SAVE_DIR):
        return None
    for d in os.listdir(SAVE_DIR):
        slot = os.path.join(SAVE_DIR, d, '0000.bin')
        if os.path.isfile(slot):
            return slot
    return None


class TestExpCurve(unittest.TestCase):
    """Test that get_exp_for_level returns correct thresholds."""

    def test_level_1_is_zero(self):
        self.assertEqual(get_exp_for_level(1), 0)

    def test_level_99_is_max(self):
        exp = get_exp_for_level(99)
        self.assertEqual(exp, 7500000)  # curve 4 (highest)

    def test_exp_increases_with_level(self):
        prev = 0
        for lv in range(1, 100):
            exp = get_exp_for_level(lv)
            self.assertGreaterEqual(exp, prev,
                f"EXP should increase: Lv{lv}={exp} < Lv{lv-1}={prev}")
            prev = exp

    def test_all_levels_have_values(self):
        for lv in range(1, 100):
            exp = get_exp_for_level(lv)
            self.assertIsNotNone(exp, f"No EXP value for level {lv}")
            self.assertGreaterEqual(exp, 0)


class TestExpAgainstSaveData(unittest.TestCase):
    """Verify EXP formula against actual save data.

    Every Digimon in the save should have EXP >= the curve 1 threshold
    for its level. If any fail, the formula is wrong.
    """

    @classmethod
    def setUpClass(cls):
        cls.save_path = _find_save()
        if cls.save_path is None:
            raise unittest.SkipTest("No save file found")
        cls.sf = SaveFile(cls.save_path)
        cls.roster = cls.sf.read_roster()

    def test_all_digimon_exp_fits_curve_1(self):
        """Every Digimon's EXP should be >= curve 1 (minimum) threshold."""
        db = _get_db()
        failures = []
        for e in self.roster:
            row = db.execute(
                "SELECT total_exp FROM experience_curves WHERE curve_id = 1 AND level = ?",
                (e['level'],)).fetchone()
            threshold = row['total_exp'] if row else 0
            if e['exp'] < threshold:
                name = e.get('nickname') or e['species']
                failures.append(
                    f"{name} Lv{e['level']}: EXP={e['exp']} < threshold={threshold}")
        self.assertEqual(failures, [],
            f"{len(failures)} Digimon have EXP below curve 1 threshold:\n" +
            "\n".join(failures))

    def test_get_exp_defaults_to_curve_4(self):
        """get_exp_for_level with no curve should return curve 4 (highest)."""
        db = _get_db()
        for lv in [10, 50, 99]:
            row = db.execute(
                "SELECT total_exp FROM experience_curves WHERE curve_id = 4 AND level = ?",
                (lv,)).fetchone()
            self.assertEqual(get_exp_for_level(lv), row['total_exp'],
                f"get_exp_for_level({lv}) should default to curve 4")

    def test_get_exp_with_specific_curve(self):
        """get_exp_for_level with explicit curve_id should use that curve."""
        db = _get_db()
        for c in [1, 2, 3, 4]:
            row = db.execute(
                "SELECT total_exp FROM experience_curves WHERE curve_id = ? AND level = 50",
                (c,)).fetchone()
            self.assertEqual(get_exp_for_level(50, curve_id=c), row['total_exp'])

    def test_detect_curve_returns_valid(self):
        """detect_exp_curve should return 1-4."""
        for e in self.roster[:10]:
            curve = detect_exp_curve(e['level'], e['exp'])
            self.assertIn(curve, [1, 2, 3, 4])

    def test_detected_curve_exp_fits(self):
        """EXP from detected curve at current level should be <= actual EXP."""
        db = _get_db()
        for e in self.roster:
            curve = detect_exp_curve(e['level'], e['exp'])
            row = db.execute(
                "SELECT total_exp FROM experience_curves WHERE curve_id = ? AND level = ?",
                (curve, e['level'])).fetchone()
            self.assertLessEqual(row['total_exp'], e['exp'],
                f"{e['species']} Lv{e['level']}: curve {curve} threshold {row['total_exp']} > EXP {e['exp']}")

    def test_roster_not_empty(self):
        self.assertGreater(len(self.roster), 0, "Roster should not be empty")


class TestGrowthType(unittest.TestCase):
    """Test growth_type lookups."""

    def test_known_species(self):
        db = _get_db()
        # Agumon should have growth_type 1
        row = db.execute(
            "SELECT growth_type FROM digimon WHERE name = 'Agumon'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['growth_type'], 1)

    def test_all_species_have_growth_type(self):
        db = _get_db()
        rows = db.execute(
            "SELECT id, name, growth_type FROM digimon WHERE growth_type IS NULL"
        ).fetchall()
        self.assertEqual(len(rows), 0, "All species should have a growth_type")

    def test_growth_type_has_curve(self):
        """Every growth_type used by a Digimon should have a growth_curves entry."""
        db = _get_db()
        growth_types = db.execute(
            "SELECT DISTINCT growth_type FROM digimon").fetchall()
        for row in growth_types:
            gt = row['growth_type']
            count = db.execute(
                "SELECT COUNT(*) FROM growth_curves WHERE curve_id = ?",
                (gt,)).fetchone()[0]
            self.assertEqual(count, 99,
                f"growth_type {gt} should have 99 growth_curve entries, got {count}")


class TestGrowthStats(unittest.TestCase):
    """Test growth stat lookups."""

    def test_level_1_is_zero(self):
        # All growth types should have zero growth at level 1
        for gt in [1, 4, 7, 10, 13, 16]:
            stats = get_growth_stats(gt, 1)
            self.assertEqual(stats, [0] * 7,
                f"Growth at Lv1 should be all zeros for gt={gt}")

    def test_growth_increases_with_level(self):
        """Stats should generally increase with level (sum of all stats)."""
        for gt in [1, 4, 7, 10]:
            prev_total = 0
            for lv in range(1, 100):
                stats = get_growth_stats(gt, lv)
                total = sum(stats)
                self.assertGreaterEqual(total, prev_total,
                    f"Growth should increase: gt={gt} Lv{lv} total={total} < prev={prev_total}")
                prev_total = total

    def test_returns_7_stats(self):
        stats = get_growth_stats(1, 50)
        self.assertEqual(len(stats), 7)
        for s in stats:
            self.assertGreaterEqual(s, 0)


class TestLevelChangeIntegration(unittest.TestCase):
    """Test that level changes produce consistent EXP and stat values."""

    def test_leveling_up_increases_exp(self):
        exp_10 = get_exp_for_level(10)
        exp_50 = get_exp_for_level(50)
        self.assertGreater(exp_50, exp_10)

    def test_leveling_up_increases_growth(self):
        growth_10 = get_growth_stats(1, 10)
        growth_50 = get_growth_stats(1, 50)
        for i in range(7):
            self.assertGreaterEqual(growth_50[i], growth_10[i],
                f"Stat {i} should grow: Lv50={growth_50[i]} < Lv10={growth_10[i]}")

    def test_growth_delta_is_positive_when_leveling_up(self):
        """When leveling from 10 to 50, the delta should be positive."""
        old = get_growth_stats(1, 10)
        new = get_growth_stats(1, 50)
        for i in range(7):
            delta = new[i] - old[i]
            self.assertGreaterEqual(delta, 0,
                f"Stat {i} delta should be >= 0, got {delta}")

    def test_growth_delta_is_negative_when_leveling_down(self):
        """When leveling from 50 to 10, the delta should be negative."""
        old = get_growth_stats(1, 50)
        new = get_growth_stats(1, 10)
        for i in range(7):
            delta = new[i] - old[i]
            self.assertLessEqual(delta, 0,
                f"Stat {i} delta should be <= 0 when leveling down, got {delta}")


class TestRosterCounts(unittest.TestCase):
    """Test that roster parsing produces correct counts."""

    @classmethod
    def setUpClass(cls):
        cls.save_path = _find_save()
        if cls.save_path is None:
            raise unittest.SkipTest("No save file found")
        cls.sf = SaveFile(cls.save_path)
        cls.roster = cls.sf.read_roster()

    def test_party_max_6(self):
        party = [e for e in self.roster if e['location'] == 'party']
        self.assertLessEqual(len(party), 6, "Party should have at most 6 members")

    def test_no_duplicate_offsets(self):
        offsets = [e['_offset'] for e in self.roster]
        self.assertEqual(len(offsets), len(set(offsets)),
            "No two roster entries should share the same offset")

    def test_all_levels_valid(self):
        for e in self.roster:
            self.assertGreaterEqual(e['level'], 1)
            self.assertLessEqual(e['level'], 99)

    def test_all_personalities_valid(self):
        for e in self.roster:
            self.assertGreaterEqual(e['personality_id'], 1)
            self.assertLessEqual(e['personality_id'], 16)

    def test_locations_are_valid(self):
        valid = {'party', 'box', 'farm'}
        for e in self.roster:
            self.assertIn(e['location'], valid,
                f"{e['species']} has invalid location: {e['location']}")


if __name__ == '__main__':
    unittest.main()
