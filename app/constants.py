ACTION_VALUES = [
    'New Lead',
    'Call Scheduled',
    'Contacted',
    'Quote Requested',
    'Proposal Sent',
    'Follow-Up',
    'Negotiation',
    'Contract',
    'Contract Sent',
    'Closed Won',
    'Closed Lost',
    'On Hold',
]

PROGRESS_VALUES = [
    'Prospect',
    'Qualified',
    'In Progress',
    'Proposal',
    'Decision Pending',
    'Won',
    'Lost',
]

# Bootstrap badge colour per ACTION value
ACTION_BADGE_CLASS = {
    'New Lead':        'secondary',
    'Call Scheduled':  'info',
    'Contacted':       'primary',
    'Quote Requested': 'warning',
    'Proposal Sent':   'warning',
    'Follow-Up':       'primary',
    'Negotiation':     'warning',
    'Contract':        'dark',
    'Contract Sent':   'success',
    'Closed Won':      'success',
    'Closed Lost':     'danger',
    'On Hold':         'secondary',
}

LEADS_PER_PAGE = 25
