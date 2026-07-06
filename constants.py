import re

MENU_NAME = "Sort New Cards Semantically"

CLOZE_RE = re.compile(r'{{c\d+::|}}') # Remove Cloze Syntax
HTML_RE = re.compile(r"<img[^>]*>|<[^>]+>|&nbsp;") # Remove HTML tags and entities
DELIMITER_RE = re.compile(r'::|[_/#!&,;:\'\"?\*~=\\()\[\]{}<>]') # Replace certain delimiters with spaces
PUNCT_RE = re.compile(r'[^\w\s.]') # Remove punctuation except periods (to retain decimal numbers)
SPACES_RE = re.compile(r'\s+') # Normalize whitespace in string

MEDICAL_STOP_WORDS = {
    'presents', 'associated', 'causes', 'diagnosed', 'inhibits',
    'activates', 'leads', 'results', 'increase', 'decrease',
    'increased', 'decreased', 'occurs', 'found', 'seen',
    'related', 'called', 'known', 'uses', 'produces', 'involves',
    'manifests', 'characterized', 'treat', 'treated', 'given',
    'administered', 'shows', 'indicates', 'suggests', 'develops',
    'lacks', 'requires', 'contains', 'describes', 'comprises',
    'follows', 'precedes', 'remains', 'demonstrated', 'observed',
    'reported', 'compare', 'compared', 'defined', 'excluded',
    'included', 'listed', 'recommended', 'considered', 'arises',

    # Adverbs (these are very noisy)
    'typically', 'commonly', 'rarely', 'often', 'usually',
    'primarily', 'secondarily', 'acutely', 'chronically',
    'subsequently', 'generally', 'specifically',

    # Conjunctions & Prepositions (not in default list)
    'via', 'per', 'versus', 'vs', 'within', 'without', 'upon'
}