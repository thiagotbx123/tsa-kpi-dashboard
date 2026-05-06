"""Tests for KPI pipeline calculations.

Covers functions from:
  - kpi/merge_opossum_data.py: date_to_week, week_range, extract_customer,
                               extract_history_fields
  - kpi/normalize_data.py: calc_perf (single authority), calc_perf_with_history

Strategy: merge_opossum_data.py and normalize_data.py both execute module-level I/O
on import. We patch builtins.open and related calls so the modules can be imported
without needing real data files on disk.
"""

import sys
import os
import json
import types
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# ── Path setup ────────────────────────────────────────────────────────────────
KPI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if KPI_DIR not in sys.path:
    sys.path.insert(0, KPI_DIR)

# ── Import helpers (isolate module-level side-effects) ────────────────────────
# Both source files open JSON files and call sys.stdout.reconfigure at import
# time. We mock those so we can extract pure functions without real data.

_EMPTY_JSON = json.dumps([])


def _load_merge_module():
    """Import merge_opossum_data with all file I/O mocked out."""
    import importlib
    # Remove cached version so we get a fresh import each time if needed
    sys.modules.pop('merge_opossum_data', None)

    with patch('builtins.open', MagicMock()), \
         patch('json.load', return_value=[]), \
         patch('json.dump', return_value=None), \
         patch('os.path.exists', return_value=False), \
         patch('os.replace', return_value=None), \
         patch('sys.stdout.reconfigure', return_value=None):
        mod = importlib.import_module('merge_opossum_data')
    return mod


def _load_normalize_module():
    """Import normalize_data with all file I/O mocked out."""
    import importlib
    sys.modules.pop('normalize_data', None)

    with patch('builtins.open', MagicMock()), \
         patch('json.load', return_value=[]), \
         patch('json.dump', return_value=None), \
         patch('os.path.exists', return_value=False), \
         patch('os.replace', return_value=None), \
         patch('sys.stdout.reconfigure', return_value=None), \
         patch('sys.exit', return_value=None):
        mod = importlib.import_module('normalize_data')
    return mod


# Load modules once at module level
_merge = _load_merge_module()
_norm = _load_normalize_module()

# Pull functions out of the loaded modules
# A30-003: calc_perf is now ONLY in normalize (single authority)
calc_perf = _norm.calc_perf
date_to_week = _merge.date_to_week
week_range = _merge.week_range
extract_customer = _merge.extract_customer
extract_history_fields = _merge.extract_history_fields
calc_perf_with_history = _norm.calc_perf_with_history

# State ID constants from source (Raccoons team)
STATE_IN_REVIEW = '89e4c72d-57aa-4774-8cf0-b00ee103d17c'
STATE_DONE = '6e10418c-81fe-467d-aed3-d4c75577d16e'
STATE_IN_PROGRESS = '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b'


# ══════════════════════════════════════════════════════════════════════════════
# 1. calc_perf(status, eta, delivery)
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcPerf(unittest.TestCase):

    # ── Done + delivery comparisons ───────────────────────────────────────────

    def test_done_delivery_before_eta_is_on_time(self):
        result = calc_perf('Done', '2026-03-20', '2026-03-18')
        self.assertEqual(result, 'On Time')

    def test_done_delivery_same_day_as_eta_is_on_time(self):
        # diff == 0 → on time (boundary)
        result = calc_perf('Done', '2026-03-20', '2026-03-20')
        self.assertEqual(result, 'On Time')

    def test_done_delivery_after_eta_is_late(self):
        # D.LIE27: 5 days past ETA (beyond 1 BDay tolerance) → Late
        result = calc_perf('Done', '2026-03-20', '2026-03-25')
        self.assertEqual(result, 'Late')

    # ── D.LIE27: 1 business-day tolerance ────────────────────────────────────

    def test_done_delivery_one_bday_after_eta_is_on_time(self):
        # ETA Wed 2026-03-18, delivered Thu 2026-03-19 → 1 BDay → On Time
        result = calc_perf('Done', '2026-03-18', '2026-03-19')
        self.assertEqual(result, 'On Time')

    def test_done_delivery_two_bdays_after_eta_is_late(self):
        # ETA Wed 2026-03-18, delivered Fri 2026-03-20 → 2 BDays → Late
        result = calc_perf('Done', '2026-03-18', '2026-03-20')
        self.assertEqual(result, 'Late')

    def test_done_delivery_weekend_after_friday_eta_is_on_time(self):
        # ETA Fri 2026-03-20, delivered Mon 2026-03-23 → 1 BDay (weekend skipped) → On Time
        result = calc_perf('Done', '2026-03-20', '2026-03-23')
        self.assertEqual(result, 'On Time')

    def test_done_delivery_tuesday_after_friday_eta_is_late(self):
        # ETA Fri 2026-03-20, delivered Tue 2026-03-24 → 2 BDays → Late
        result = calc_perf('Done', '2026-03-20', '2026-03-24')
        self.assertEqual(result, 'Late')

    # ── No delivery ──────────────────────────────────────────────────────────

    def test_done_no_delivery_date(self):
        result = calc_perf('Done', '2026-03-20', '')
        self.assertEqual(result, 'No Delivery Date')

    def test_done_none_delivery_date(self):
        result = calc_perf('Done', '2026-03-20', None)
        self.assertEqual(result, 'No Delivery Date')

    # ── D.LIE26: No ETA requires External(Customer) ─────────────────────────

    def test_done_no_eta_external_is_no_eta(self):
        result = calc_perf('Done', '', '2026-03-18', category='External')
        self.assertEqual(result, 'No ETA')

    def test_done_no_eta_internal_is_na(self):
        # D.LIE26: Internal with no ETA → N/A (No ETA only counts for External)
        result = calc_perf('Done', '', '2026-03-18', category='Internal')
        self.assertEqual(result, 'N/A')

    def test_done_no_eta_no_category_is_na(self):
        # Default category empty → treated as non-External → N/A
        result = calc_perf('Done', '', '2026-03-18')
        self.assertEqual(result, 'N/A')

    def test_done_none_eta_external_is_no_eta(self):
        result = calc_perf('Done', None, '2026-03-18', category='External')
        self.assertEqual(result, 'No ETA')

    # ── Not Started (Backlog/Todo/Triage without ETA) ────────────────────────

    def test_backlog_no_eta_is_not_started(self):
        result = calc_perf('Backlog', '', '')
        self.assertEqual(result, 'Not Started')

    def test_triage_no_eta_is_not_started(self):
        result = calc_perf('Triage', '', '')
        self.assertEqual(result, 'Not Started')

    # ── Canceled ──────────────────────────────────────────────────────────────

    def test_canceled_returns_na(self):
        result = calc_perf('Canceled', '2026-03-20', '2026-03-18')
        self.assertEqual(result, 'N/A')

    def test_canceled_no_eta_still_na(self):
        result = calc_perf('Canceled', '', '')
        self.assertEqual(result, 'N/A')

    # ── Active tickets (On Track / Overdue) ───────────────────────────────────

    def test_in_progress_eta_future_is_on_track(self):
        future_eta = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        result = calc_perf('In Progress', future_eta, '')
        self.assertEqual(result, 'On Track')

    def test_in_progress_eta_past_is_late(self):
        past_eta = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        result = calc_perf('In Progress', past_eta, '')
        self.assertEqual(result, 'Late')

    def test_todo_eta_future_is_on_track(self):
        future_eta = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        result = calc_perf('Todo', future_eta, '')
        self.assertEqual(result, 'On Track')

    def test_todo_eta_past_is_late(self):
        past_eta = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        result = calc_perf('Todo', past_eta, '')
        self.assertEqual(result, 'Late')

    # ── Paused / On Hold ────────────────────────────────────────────────────

    def test_paused_returns_on_hold(self):
        result = calc_perf('Paused', '2026-03-20', '')
        self.assertEqual(result, 'On Hold')

    def test_on_hold_returns_on_hold(self):
        result = calc_perf('On Hold', '2026-03-20', '')
        self.assertEqual(result, 'On Hold')

    def test_paused_no_eta_returns_on_hold(self):
        result = calc_perf('Paused', '', '')
        self.assertEqual(result, 'On Hold')

    # ── Blocked ──────────────────────────────────────────────────────────────

    def test_bbc_returns_blocked(self):
        result = calc_perf('B.B.C', '2026-03-20', '')
        self.assertEqual(result, 'Blocked')

    def test_blocked_returns_blocked(self):
        result = calc_perf('Blocked', '2026-01-01', '')
        self.assertEqual(result, 'Blocked')

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_empty_status_no_eta_external_returns_no_eta(self):
        # D.LIE26: needs category=External to be flagged as No ETA
        result = calc_perf('', '', '', category='External')
        self.assertEqual(result, 'No ETA')

    def test_empty_status_no_eta_internal_returns_na(self):
        result = calc_perf('', '', '', category='Internal')
        self.assertEqual(result, 'N/A')

    def test_none_status_no_eta_external_returns_no_eta(self):
        result = calc_perf(None, '', '', category='External')
        self.assertEqual(result, 'No ETA')

    def test_done_invalid_eta_format_returns_na(self):
        result = calc_perf('Done', 'not-a-date', '2026-03-18')
        self.assertEqual(result, 'N/A')

    def test_in_progress_invalid_eta_format_returns_na(self):
        result = calc_perf('In Progress', 'not-a-date', '')
        self.assertEqual(result, 'N/A')

    def test_done_delivery_with_datetime_suffix(self):
        # delivery may carry a time component — only first 10 chars are used
        result = calc_perf('Done', '2026-03-20', '2026-03-19T18:00:00.000Z')
        self.assertEqual(result, 'On Time')


# ══════════════════════════════════════════════════════════════════════════════
# 2. date_to_week(date_str)
# ══════════════════════════════════════════════════════════════════════════════

class TestDateToWeek(unittest.TestCase):

    def test_normal_date_returns_correct_format(self):
        # 2026-03-10 → year=26, month=03, day=10 → wn = (10-1)//7+1 = 2
        result = date_to_week('2026-03-10')
        self.assertEqual(result, '26-03 W.2')

    def test_first_day_of_month_is_w1(self):
        result = date_to_week('2026-03-01')
        self.assertEqual(result, '26-03 W.1')

    def test_day_8_is_w2(self):
        result = date_to_week('2026-03-08')
        self.assertEqual(result, '26-03 W.2')

    def test_day_15_is_w3(self):
        result = date_to_week('2026-03-15')
        self.assertEqual(result, '26-03 W.3')

    def test_day_22_is_w4(self):
        result = date_to_week('2026-03-22')
        self.assertEqual(result, '26-03 W.4')

    def test_day_29_is_w5(self):
        result = date_to_week('2026-03-29')
        self.assertEqual(result, '26-03 W.5')

    def test_empty_string_returns_none(self):
        result = date_to_week('')
        self.assertIsNone(result)

    def test_none_returns_none(self):
        result = date_to_week(None)
        self.assertIsNone(result)

    def test_january_first_2026(self):
        result = date_to_week('2026-01-01')
        self.assertEqual(result, '26-01 W.1')

    def test_december_date(self):
        # 2025-12-25 → year=25, month=12, day=25 → wn=(25-1)//7+1=4
        result = date_to_week('2025-12-25')
        self.assertEqual(result, '25-12 W.4')

    def test_date_with_datetime_suffix_uses_first_10_chars(self):
        result = date_to_week('2026-03-15T12:00:00Z')
        self.assertEqual(result, '26-03 W.3')

    def test_invalid_format_returns_none(self):
        result = date_to_week('not-a-date')
        self.assertIsNone(result)

    def test_year_suffix_is_zero_padded(self):
        # Year 2009 → suffix 09
        result = date_to_week('2009-06-01')
        self.assertEqual(result, '09-06 W.1')

    def test_month_is_zero_padded(self):
        result = date_to_week('2026-02-01')
        self.assertIn('26-02', result)


# ══════════════════════════════════════════════════════════════════════════════
# 3. extract_customer(title)
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractCustomer(unittest.TestCase):

    def test_gong_bracket(self):
        result = extract_customer('[Gong] Some task')
        self.assertEqual(result, 'Gong')

    def test_quickbooks_bracket(self):
        result = extract_customer('[QuickBooks] Another task')
        self.assertEqual(result, 'QuickBooks')

    def test_qbo_bracket_maps_to_quickbooks(self):
        result = extract_customer('[QBO] Data generation')
        self.assertEqual(result, 'QuickBooks')

    def test_no_brackets_returns_empty(self):
        result = extract_customer('No brackets here')
        self.assertIn(result, ('', None))

    def test_spike_maps_to_internal(self):
        result = extract_customer('[Spike] Internal thing')
        self.assertEqual(result, 'Internal')

    def test_archer_bracket(self):
        result = extract_customer('[Archer] Implementation')
        self.assertEqual(result, 'Archer')

    def test_gem_bracket(self):
        result = extract_customer('[Gem] Setup')
        self.assertEqual(result, 'Gem')

    def test_gainsight_maps_to_staircase(self):
        result = extract_customer('[Gainsight] Integration')
        self.assertEqual(result, 'Staircase')

    def test_staircase_bracket(self):
        result = extract_customer('[Staircase] Integration')
        self.assertEqual(result, 'Staircase')

    def test_people_ai_bracket(self):
        result = extract_customer('[People.ai] Setup')
        self.assertEqual(result, 'People.ai')

    def test_unknown_customer_returns_as_is(self):
        # Unknown keys are returned verbatim
        result = extract_customer('[Tropic] Implementation')
        self.assertEqual(result, 'Tropic')

    def test_de_team_maps_to_internal(self):
        result = extract_customer('[DE Team] Standardization')
        self.assertEqual(result, 'Internal')

    def test_case_insensitive_lookup(self):
        # cust_map uses lowercase lookup
        result = extract_customer('[GONG] Task')
        self.assertEqual(result, 'Gong')

    def test_empty_string_returns_empty(self):
        result = extract_customer('')
        self.assertEqual(result, '')

    def test_mailchimp_bracket(self):
        result = extract_customer('[Mailchimp] Integration')
        self.assertEqual(result, 'Mailchimp')


# ══════════════════════════════════════════════════════════════════════════════
# 4. D.LIE24 — extract_history_fields with reassignedInReview
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractHistoryFieldsReassignedInReview(unittest.TestCase):
    """
    D.LIE24 scenario:
      - Person A moves ticket to In Review on 2026-03-10
      - Person A reassigns to Person B on the same day
      - Person B marks Done on 2026-03-15

    Expected:
      - reassignedInReview = True
      - inReviewDate = '2026-03-10'
      - deliveryDate = '2026-03-10'  (first In Review / Done transition)
      - reviewAssignee = person_b_id
    """

    PERSON_A_ID = 'person-a-001'
    PERSON_B_ID = 'person-b-002'

    # State IDs from merge_opossum_data.py (Raccoons team)
    STATE_IN_REVIEW = '89e4c72d-57aa-4774-8cf0-b00ee103d17c'
    STATE_DONE = '6e10418c-81fe-467d-aed3-d4c75577d16e'

    def _make_issue(self):
        return {
            'dueDate': '2026-03-20',
            'history': [
                # Person A moves to In Review
                {
                    'createdAt': '2026-03-10T10:00:00.000Z',
                    'toStateId': self.STATE_IN_REVIEW,
                    'fromStateId': '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b',  # In Progress
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
                # Person A reassigns to Person B (same day, after moving to In Review)
                {
                    'createdAt': '2026-03-10T11:00:00.000Z',
                    'toStateId': None,
                    'fromStateId': None,
                    'toAssigneeId': self.PERSON_B_ID,
                    'fromAssigneeId': self.PERSON_A_ID,
                    'toAssigneeName': 'Person B',
                    'fromAssigneeName': 'Person A',
                },
                # Person B marks Done
                {
                    'createdAt': '2026-03-15T09:00:00.000Z',
                    'toStateId': self.STATE_DONE,
                    'fromStateId': self.STATE_IN_REVIEW,
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
            ],
        }

    def test_reassigned_in_review_flag_is_true(self):
        result = extract_history_fields(self._make_issue())
        self.assertTrue(result['reassignedInReview'])

    def test_in_review_date_is_set(self):
        result = extract_history_fields(self._make_issue())
        self.assertEqual(result['inReviewDate'], '2026-03-10')

    def test_delivery_date_is_first_transition_to_in_review(self):
        result = extract_history_fields(self._make_issue())
        self.assertEqual(result['deliveryDate'], '2026-03-10')

    def test_review_assignee_is_person_b(self):
        result = extract_history_fields(self._make_issue())
        self.assertEqual(result['reviewAssignee'], self.PERSON_B_ID)

    def test_reviewer_delay_calculated(self):
        # In Review: 2026-03-10, Done: 2026-03-15 → 5 days
        result = extract_history_fields(self._make_issue())
        self.assertEqual(result['reviewerDelay'], 5)

    def test_final_eta_from_due_date(self):
        result = extract_history_fields(self._make_issue())
        self.assertEqual(result['finalEta'], '2026-03-20')

    def test_no_history_returns_all_none(self):
        issue = {'dueDate': '2026-03-20', 'history': []}
        result = extract_history_fields(issue)
        self.assertIsNone(result['deliveryDate'])
        self.assertIsNone(result['inReviewDate'])
        self.assertFalse(result['reassignedInReview'])
        self.assertIsNone(result['reviewAssignee'])

    def test_no_reassignment_flag_false(self):
        """Ticket that goes In Review → Done without assignee change."""
        issue = {
            'dueDate': '2026-03-20',
            'history': [
                {
                    'createdAt': '2026-03-10T10:00:00.000Z',
                    'toStateId': self.STATE_IN_REVIEW,
                    'fromStateId': '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b',
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
                {
                    'createdAt': '2026-03-12T10:00:00.000Z',
                    'toStateId': self.STATE_DONE,
                    'fromStateId': self.STATE_IN_REVIEW,
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
            ],
        }
        result = extract_history_fields(issue)
        self.assertFalse(result['reassignedInReview'])
        self.assertIsNone(result['reviewAssignee'])

    def test_rework_detected_when_done_to_in_progress(self):
        """Tickets moved from Done back to In Progress should set reworkDetected."""
        issue = {
            'dueDate': '2026-03-20',
            'history': [
                {
                    'createdAt': '2026-03-08T10:00:00.000Z',
                    'toStateId': self.STATE_DONE,
                    'fromStateId': '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b',
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
                # Reopened
                {
                    'createdAt': '2026-03-09T10:00:00.000Z',
                    'toStateId': '8fd63b1a-1ec5-460f-b0c9-605ac0d6e04b',  # In Progress
                    'fromStateId': self.STATE_DONE,
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                },
            ],
        }
        result = extract_history_fields(issue)
        self.assertTrue(result['reworkDetected'])

    def test_eta_changes_counted(self):
        issue = {
            'dueDate': '2026-03-25',
            'history': [
                {
                    'createdAt': '2026-03-01T10:00:00.000Z',
                    'toStateId': None,
                    'fromStateId': None,
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                    'fromDueDate': '2026-03-15',
                    'toDueDate': '2026-03-20',
                },
                {
                    'createdAt': '2026-03-05T10:00:00.000Z',
                    'toStateId': None,
                    'fromStateId': None,
                    'toAssigneeId': None,
                    'fromAssigneeId': None,
                    'toDueDate': '2026-03-25',
                },
            ],
        }
        result = extract_history_fields(issue)
        self.assertEqual(result['etaChanges'], 2)
        # originalEta = fromDueDate of first change
        self.assertEqual(result['originalEta'], '2026-03-15')


# ══════════════════════════════════════════════════════════════════════════════
# 5. week_range(date_str)
# ══════════════════════════════════════════════════════════════════════════════

class TestWeekRange(unittest.TestCase):

    def test_monday_returns_mon_to_fri(self):
        # 2026-03-23 is a Monday
        result = week_range('2026-03-23')
        self.assertEqual(result, '03/23 - 03/27/2026')

    def test_wednesday_returns_surrounding_week(self):
        # 2026-03-25 is a Wednesday → week is Mon 03/23 – Fri 03/27
        result = week_range('2026-03-25')
        self.assertEqual(result, '03/23 - 03/27/2026')

    def test_friday_returns_same_week(self):
        # 2026-03-27 is a Friday → week is Mon 03/23 – Fri 03/27
        result = week_range('2026-03-27')
        self.assertEqual(result, '03/23 - 03/27/2026')

    def test_sunday_returns_next_week_start(self):
        # 2026-03-22 is a Sunday → weekday()=6 → monday = 03/22 - 6 days = 03/16
        # (Sunday belongs to the PREVIOUS week in Python's weekday)
        result = week_range('2026-03-22')
        # Monday 03/16, Friday 03/20
        self.assertEqual(result, '03/16 - 03/20/2026')

    def test_returns_correct_format(self):
        # Format must be MM/DD - MM/DD/YYYY
        result = week_range('2026-01-05')
        import re
        self.assertRegex(result, r'^\d{2}/\d{2} - \d{2}/\d{2}/\d{4}$')

    def test_empty_string_returns_empty(self):
        result = week_range('')
        self.assertEqual(result, '')

    def test_none_returns_empty(self):
        result = week_range(None)
        self.assertEqual(result, '')

    def test_cross_month_week(self):
        # 2026-03-30 is a Monday → week runs 03/30 – 04/03
        result = week_range('2026-03-30')
        self.assertEqual(result, '03/30 - 04/03/2026')

    def test_invalid_date_returns_empty(self):
        result = week_range('not-a-date')
        self.assertEqual(result, '')

    def test_date_with_datetime_suffix(self):
        # Should use first 10 chars
        result = week_range('2026-03-23T00:00:00.000Z')
        self.assertEqual(result, '03/23 - 03/27/2026')


# ══════════════════════════════════════════════════════════════════════════════
# 6. calc_perf_with_history (normalize_data.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcPerfWithHistory(unittest.TestCase):
    """Tests for the activity-based performance calculator."""

    def _rec(self, **kwargs):
        """Build a minimal record dict with sensible defaults."""
        base = {
            'status': 'Done',
            'originalEta': '',
            'finalEta': '',
            'eta': '',
            'deliveryDate': '',
            'inReviewDate': '',
            'delivery': '',
        }
        base.update(kwargs)
        return base

    def test_canceled_returns_na(self):
        r = self._rec(status='Canceled', originalEta='2026-03-20')
        self.assertEqual(calc_perf_with_history(r), 'N/A')

    def test_bbc_returns_blocked(self):
        r = self._rec(status='B.B.C', originalEta='2026-03-20')
        self.assertEqual(calc_perf_with_history(r), 'Blocked')

    def test_backlog_no_eta_returns_not_started(self):
        r = self._rec(status='Backlog', originalEta='', finalEta='', eta='')
        self.assertEqual(calc_perf_with_history(r), 'Not Started')

    def test_todo_no_eta_returns_not_started(self):
        r = self._rec(status='Todo', originalEta='', finalEta='', eta='')
        self.assertEqual(calc_perf_with_history(r), 'Not Started')

    def test_in_progress_no_eta_external_returns_no_eta(self):
        # D.LIE26: External(Customer) + no ETA → No ETA
        r = self._rec(status='In Progress', originalEta='', finalEta='', eta='', category='External')
        self.assertEqual(calc_perf_with_history(r), 'No ETA')

    def test_in_progress_no_eta_internal_returns_na(self):
        # D.LIE26: Internal + no ETA → N/A
        r = self._rec(status='In Progress', originalEta='', finalEta='', eta='', category='Internal')
        self.assertEqual(calc_perf_with_history(r), 'N/A')

    def test_delivery_on_time_via_delivery_date(self):
        r = self._rec(
            status='Done',
            originalEta='2026-03-20',
            deliveryDate='2026-03-18',
        )
        self.assertEqual(calc_perf_with_history(r), 'On Time')

    def test_delivery_same_day_as_eta_is_on_time(self):
        r = self._rec(
            status='Done',
            originalEta='2026-03-20',
            deliveryDate='2026-03-20',
        )
        self.assertEqual(calc_perf_with_history(r), 'On Time')

    def test_delivery_after_eta_is_late(self):
        r = self._rec(
            status='Done',
            originalEta='2026-03-15',
            deliveryDate='2026-03-20',
        )
        self.assertEqual(calc_perf_with_history(r), 'Late')

    def test_no_delivery_open_ticket_future_eta_on_track(self):
        future = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        r = self._rec(
            status='In Progress',
            originalEta=future,
            deliveryDate='',
            inReviewDate='',
        )
        self.assertEqual(calc_perf_with_history(r), 'On Track')

    def test_no_delivery_open_ticket_past_eta_is_late(self):
        past = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        r = self._rec(
            status='In Progress',
            originalEta=past,
            deliveryDate='',
            inReviewDate='',
        )
        self.assertEqual(calc_perf_with_history(r), 'Late')

    def test_in_review_on_time_when_review_move_before_eta(self):
        past_eta = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        in_review = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        r = self._rec(
            status='In Progress',
            originalEta=past_eta,
            deliveryDate='',
            inReviewDate=in_review,
        )
        self.assertEqual(calc_perf_with_history(r), 'On Time')

    def test_in_review_late_when_review_move_after_eta(self):
        past_eta = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        in_review = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        r = self._rec(
            status='In Progress',
            originalEta=past_eta,
            deliveryDate='',
            inReviewDate=in_review,
        )
        self.assertEqual(calc_perf_with_history(r), 'Late')

    def test_falls_back_to_eta_when_original_eta_missing(self):
        """originalEta missing → falls back to finalEta then eta."""
        r = self._rec(
            status='Done',
            originalEta='',
            finalEta='2026-03-20',
            deliveryDate='2026-03-19',
        )
        self.assertEqual(calc_perf_with_history(r), 'On Time')

    def test_invalid_eta_returns_na(self):
        r = self._rec(
            status='Done',
            originalEta='not-a-date',
            deliveryDate='2026-03-19',
        )
        self.assertEqual(calc_perf_with_history(r), 'N/A')


if __name__ == '__main__':
    unittest.main()
