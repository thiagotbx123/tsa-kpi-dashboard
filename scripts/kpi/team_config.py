"""Shared KPI configuration — single source of truth.

All person maps, customer maps, perf labels, and output paths live here.
Import from this module in merge, normalize, refresh, build, upload.
"""
import os

# ── Output directory ──
OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'Downloads')

# ── Person maps ──

PERSON_MAP = {
    'Thiago Rodrigues': 'THIAGO',
    'Carlos Guilherme Matos de Almeida da Silva': 'CARLOS',
    'Alexandra Lacerda': 'ALEXANDRA',
    'Diego Cavalli': 'DIEGO',
    'Gabrielle Cupello': 'GABI',
}

PERSON_MAP_BY_ID = {
    'a6063009-d822-49f1-a638-6cebfe59e89e': 'THIAGO',
    'b13ca864-e0f4-4ff6-b020-ec3f4491643e': 'CARLOS',
    '19b6975e-3026-450b-bc01-f468ad543028': 'ALEXANDRA',
    '717e7b13-d840-41c0-baeb-444354c8ff91': 'DIEGO',
    'd9745bdb-7138-4345-9303-516aa6e4ec39': 'GABI',
}

KPI_MEMBERS = PERSON_MAP_BY_ID

# ── Performance label constants (A03-004) ──

PERF_ON_TIME = 'On Time'
PERF_LATE = 'Late'
PERF_ON_TRACK = 'On Track'
PERF_NO_ETA = 'No ETA'
PERF_NA = 'N/A'
PERF_BLOCKED = 'Blocked'
PERF_ON_HOLD = 'On Hold'
PERF_NOT_STARTED = 'Not Started'
PERF_NO_DELIVERY = 'No Delivery Date'

# ── Customer mapping (A01-002: consolidated from merge + normalize) ──

CUSTOMER_MAP = {
    'qbo': 'QuickBooks', 'quickbooks': 'QuickBooks',
    'intuit quickbooks': 'QuickBooks', 'intuit': 'QuickBooks',
    'intuit ies tco/keystone construction': 'QuickBooks',
    'qbo-wfs': 'WFS',
    'gong': 'Gong',
    'gem': 'Gem',
    'mailchimp': 'Mailchimp',
    'people.ai': 'People.ai', 'people ai': 'People.ai',
    'siteimprove': 'Siteimprove',
    'brevo': 'Brevo',
    'archer': 'Archer',
    'tropic': 'Tropic',
    'apollo': 'Apollo',
    'callrail': 'CallRail',
    'hockeystack': 'HockeyStack',
    'wfs': 'WFS',
    'staircase': 'Staircase',
    'gainsight': 'Staircase',
    'coda': 'Coda',
    'general': 'General',
    'outreach': 'Outreach',
    'tbx': 'TBX',
    'tabs': 'Tabs',
    'curbwaste': 'CurbWaste',
    'zuper': 'Zuper', '[zuper] integration': 'Zuper',
    'bill': 'Bill',
    'dixa': 'Dixa',
    'assignar': 'Assignar',
    'syncari': 'Syncari',
    'onyx': 'Onyx',
    'mparticle': 'mParticle',
    'monarch': 'Monarch',
    'de team': 'Internal',
    'spike': 'Internal',
}

PROJECT_TO_CUSTOMER = {
    'qbo': 'QuickBooks', '[quickbook] data gen': 'QuickBooks',
    'intuit quickbooks': 'QuickBooks', '[intuit quickbooks]': 'QuickBooks',
    'archer': 'Archer', 'gong implementation': 'Gong', '[gong]': 'Gong',
    '[gem]': 'Gem', '[tabs] integration': 'Tabs',
    '[tropic] implementation': 'Tropic', '[brevo] integration': 'Brevo',
    '[mailchimp] integration': 'Mailchimp', 'mailchimp': 'Mailchimp',
    '[people.ai] integration': 'People.ai',
    '[wfs] workforce solutions': 'WFS',
    '[gainsight] staircase ai integration': 'Staircase',
    'gainsight staircase': 'Staircase',
    '[siteimprove] integration': 'Siteimprove', 'siteimprove': 'Siteimprove',
    '[apollo] integration': 'Apollo', 'apollo': 'Apollo',
    'de team': 'Internal',
}

LABEL_TO_CUSTOMER = {
    'QBO': 'QuickBooks', 'WFS': 'WFS', 'Gong': 'Gong', 'Archer': 'Archer',
    'Gem': 'Gem', 'Mailchimp': 'Mailchimp', 'Tropic': 'Tropic', 'Brevo': 'Brevo',
    'Tabs': 'Tabs', 'Siteimprove': 'Siteimprove', 'Apollo': 'Apollo',
}

REAL_CUSTOMERS = {
    'QuickBooks', 'Gong', 'Archer', 'Siteimprove', 'Mailchimp', 'Gem', 'Apollo',
    'Tropic', 'Brevo', 'Tabs', 'People.ai', 'CallRail', 'Gainsight', 'Staircase',
    'WFS', 'Dixa', 'Assignar', 'Syncari', 'Onyx', 'CurbWaste', 'Bill',
    'Zuper', 'HockeyStack', 'Outreach', 'mParticle', 'Monarch',
}

NOT_REAL_CLIENTS = {
    'Waki', 'TBX', 'Routine', 'General', 'Coda', 'All',
    'Internal', "Internal \u2013 Sam's Board Meeting",
    '[Internal] TSA Operations', '[Internal] TSA Shared Repo', '[TSA] Diego Internal',
    'DE Team', 'Worklog', 'TSA', 'Bug',
    'Demo Scripts', 'Surface Editor', 'Sandbox UX', 'Sandbox Improvements',
    'Sandbox Preview', 'Legacy Sandbox Preview', 'Tracking Events',
    'Bulk Invite', 'Email Notifications', 'Basic Admin Permissions',
    'Deals UX Modernization', 'Self-Serve Demo Environments Provisioning',
    'UX for Partner Account Provisioning', 'Presenter Mode', 'Shortcut URL',
    'Project noFrame', 'HISTORY',
    '[ChurnZero] Integration',
}

FORCE_EXTERNAL = {'Tabs'}
