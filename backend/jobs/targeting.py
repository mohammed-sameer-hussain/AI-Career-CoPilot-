import re

'''Targeting rules: IT roles in major tech/MNC hub cities,
fresher + senior levels, and MNC companies.'''

# ONLY cities with real tech parks / MNC offices / GCCs.
# Bengaluru (ORR/Whitefield/Electronic City), Hyderabad (HITEC/Gachibowli),
# Chennai (OMR/Sholinganallur), Pune (Hinjewadi/Magarpatta), Mumbai (BKC/Powai/Thane),
# Gurugram (Cyber City), Noida (Sector 62/135), Delhi, Kolkata (Sector V),
# Ahmedabad (GIFT), Kochi (Infopark), Coimbatore (CHIL/SEZ).
TECH_MNC_CITIES = [
    'Bengaluru', 'Hyderabad', 'Chennai', 'Pune', 'Mumbai',
    'Gurugram', 'Noida', 'Delhi', 'Kolkata', 'Ahmedabad',
    'Kochi', 'Coimbatore',
]
TECH_MNC_CITY_ALIASES = {
    'bengaluru': ['bengaluru', 'bangalore'],
    'hyderabad': ['hyderabad', 'secunderabad'],
    'chennai': ['chennai'],
    'pune': ['pune'],
    'mumbai': ['mumbai', 'thane'],
    'gurugram': ['gurugram', 'gurgaon'],
    'noida': ['noida'],
    'delhi': ['delhi'],
    'kolkata': ['kolkata'],
    'ahmedabad': ['ahmedabad'],
    'kochi': ['kochi', 'cochin'],
    'coimbatore': ['coimbatore'],
}

# Backwards-compat alias used by older imports.
SOUTH_INDIA_HUBS = TECH_MNC_CITIES

# --- IT / tech roles -------------------------------------------------------------
# Matched against a normalised blob: title + skills/tags/categories with
# hyphens and underscores turned into spaces (e.g. "Software-Engineer").
IT_PATTERN = re.compile(
    r'engineer|developer|programmer|software|full[\s]?stack|front[\s]?end|back[\s]?end|'
    r'devops|\bsre\b|site reliability|cloud|kubernetes|terraform|'
    r'\bqa\b|quality assurance|\bsdet\b|test automation|automation tester|software test|'
    r'data scientist|data engineer|data analyst|data analyst|data analytics|data science|data warehouse|data pipeline|\betl\b|'
    r'machine learning|\bml\b|artificial intelligence|\bai\b|deep learning|nlp|large language model|\bllm\b|genai|'
    r'python|java\b|javascript|typescript|react\b|angular|node ?js|\bnode\b|php|ruby|rails|golang|'
    r'\bc\+\+|\bnet\b|dotnet|sap\b|salesforce|android|ios\b|swift|kotlin|flutter|'
    r'security|cyber|information technology|\bit support\b|\bit specialist\b|\bit analyst\b|'
    r'technical support|help ?desk|network (engineer|administrator|admin)|'
    r'system administrator|systems administrator|sysadmin|'
    r'business analyst|systems analyst|database|\bdba\b|sql developer|'
    r'web developer|mobile developer|application developer|embedded|firmware|'
    r'power bi|tableau|informatica|mainframe|oracle developer|sap consultant',
    re.IGNORECASE)

# Roles that only look technical at a glance (or are clearly not IT).
NON_IT_PATTERN = re.compile(
    r'marketing|advertis|mortgage|loan|accounting|accountant|payroll|recruit|'
    r'nurse|doctor|teacher|teaching|legal|paralegal|cook|chef|driver|retail|'
    r'content writer|copywriter|social media|'
    r'participat|study|translator|linguist|locali[sz]ation|voice|curriculum|'
    r'business development|classroom|customer research|research agent|'
    r'digital ad|ad quality|\bpos\b|assistant|'
    r'sales representative|sales associate|sales executive|sales manager|'
    r'inside sales|outside sales|undecided|talent hub|talent network|'
    r'coding tasks|customer support|'
    r'annotat|usability|survey|humanities|data entry|transcription|'
    r'content moderator|moderation|office assistant|administrative|back office|'
    r'customer service|customer success|tutor',
    re.IGNORECASE)

# --- Locations: ONLY major tech/MNC hub cities + Remote ------------------------
INDIA_PATTERN = re.compile(
    r'bengaluru|bangalore|hyderabad|secunderabad|pune|mumbai|thane|chennai|'
    r'delhi|noida|gurugram|gurgaon|kolkata|ahmedabad|kochi|cochin|coimbatore|'
    r'\bremote\b',
    re.IGNORECASE)

SOUTH_INDIA_PATTERN = re.compile(
    r'bengaluru|bangalore|chennai|hyderabad|secunderabad|kochi|cochin|coimbatore',
    re.IGNORECASE)

# kept for backwards compat; canonical list is TECH_MNC_CITIES above.
SOUTH_INDIA_HUBS = TECH_MNC_CITIES

# --- Fresher AND senior levels -------------------------------------------------
FRESHER_PATTERN = re.compile(
    r'junior|\bjr\b|entry[\s-]?level|intern(ship)?|trainee|graduate|fresher|'
    r'associate|apprentice|new grad|0[\s-]?(?:to|[-])[\s-]?2 years|'
    r'0[\s-]?1 years|1[\s-]?2 years|no experience|freshers? hiring|off[\s-]?campus|'
    r'nqt|system engineer|project engineer', re.IGNORECASE)

MID_PATTERN = re.compile(
    r'\bmid[\s-]?level\b|2[\s-]?(?:to|[-])[\s-]?5 years|3[\s-]?(?:to|[-])[\s-]?5 years|'
    r'2\+ years|3\+ years', re.IGNORECASE)

# Seniority markers are KEPT (not rejected) so seniors see roles too.
SENIOR_PATTERN = re.compile(
    r'senior|\bsr\.?\b|\blead\b|principal|\bstaff\b|head of|\bhead\b|director|'
    r'chief|\bcto\b|\bvp\b|vice president|manager|\barchitect\b|'
    r'delivery manager|program manager|5\+ years|[5-9]\s*[-+]?\s*\d*\s*years|10\+ years',
    re.IGNORECASE)

# --- MNC companies: flagship Indian IT + global tech + GCC ---------------------
MNC_COMPANIES = [
    'wipro', 'hcl', 'hcltech', 'hcl technologies', 'infosys', 'tech mahindra',
    'cognizant', 'cogizant', 'accenture', 'tcs', 'tata consultancy services',
    'tata consultancy', 'tata', 'ltimindtree', 'lti mindtree', 'mindtree',
    'mphasis', 'hexaware', 'ntt data', 'ntt', 'persistent systems', 'persistent',
    'coforge', 'zensar', 'birlasoft', 'sonata software', 'tata elxsi',
    'kpit', 'cyient', 'quest global', 'ust global', 'ust', 'virtusa',
    'nagarro', 'globant', 'epam', 'softserve', 'publicis sapient', 'sapient',
    'thoughtworks', 'zoho', 'freshworks', 'genpact', 'exl', 'wns',
    'google', 'microsoft', 'amazon', 'aws', 'apple', 'meta', 'ibm',
    'oracle', 'sap', 'salesforce', 'adobe', 'cisco', 'intel', 'nvidia', 'dell',
    'hewlett packard', 'hpe', 'lenovo', 'vmware', 'broadcom', 'servicenow',
    'workday', 'intuit', 'paypal', 'uber', 'netflix', 'linkedin',
    'snowflake', 'atlassian', 'samsung', 'red hat', 'nutanix',
    'qualcomm', 'texas instruments', 'micron', 'synopsys', 'cadence',
    'dxc technology', 'dxc', 'cgi', 'atos', 'syntel', 'fujitsu', 'hitachi',
    'siemens', 'bosch', 'continental', 'mercedes benz', 'volvo',
    'ericsson', 'nokia', 'airbus', 'boeing', 'honeywell',
    'deloitte', 'kpmg', 'pwc', 'ernst and young', 'capgemini',
    'jpmorgan', 'jp morgan', 'goldman sachs', 'morgan stanley', 'barclays',
    'hsbc', 'standard chartered', 'deutsche bank', 'citibank', 'citi',
    'bank of america', 'wells fargo', 'visa', 'mastercard', 'american express',
    'mdaas',
]

MNC_ALIASES = {
    'hcltech': 'hcl', 'hcl tech': 'hcl', 'hcl technologies': 'hcl',
    'techm': 'tech mahindra', 'cogizant': 'cognizant',
    'tata consultancy services limited': 'tata consultancy services',
    'wipro limited': 'wipro', 'infosys limited': 'infosys',
    'infosys bpm': 'infosys', 'infy': 'infosys',
}

FEATURED_MNCS = [
    'TCS', 'Infosys', 'Wipro', 'HCLTech', 'Tech Mahindra',
    'Cognizant', 'Accenture', 'LTIMindtree', 'Capgemini', 'IBM',
    'Oracle', 'Dell', 'Cisco', 'Zoho', 'Freshworks',
]

_WORD_RE = {key: re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE) for key in MNC_COMPANIES}


def _blob(*parts):
    text = ' '.join(str(p) for p in parts if p)
    return re.sub(r'[-_]+', ' ', text).lower()


def _normalise_company(company):
    text = str(company or '').strip()
    if not text:
        return ''
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'[.,;|/\\()\[\]:]+', ' ', text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    return MNC_ALIASES.get(text, text)


def is_it_role(title, *extra):
    # Non-IT words only disqualify the *title*; an IT job description may
    # legitimately mention marketing, accounts, legal etc.
    if NON_IT_PATTERN.search(_blob(title)): return False
    return bool(IT_PATTERN.search(_blob(title, *extra)))


def is_india_location(location):
    return bool(INDIA_PATTERN.search(location or ''))


def is_south_india_location(location):
    return bool(SOUTH_INDIA_PATTERN.search(location or ''))


def is_fresher_role(title, experience=''):
    if FRESHER_PATTERN.search(title or ''):
        return True
    if FRESHER_PATTERN.search(experience or ''):
        return True
    blob = f'{title or ""} {experience or ""}'
    return not SENIOR_PATTERN.search(blob)


def is_senior_role(title, experience=''):
    return bool(SENIOR_PATTERN.search(f'{title or ""} {experience or ""}'))


def experience_level(title='', experience=''):
    blob = f'{title or ""} {experience or ""}'
    if SENIOR_PATTERN.search(blob):
        return 'senior'
    if MID_PATTERN.search(blob):
        return 'mid'
    if FRESHER_PATTERN.search(blob):
        return 'fresher'
    if not re.search(r'\d+\s*(?:\+|yrs?|years)', blob, re.IGNORECASE):
        return 'fresher'
    return 'unspecified'


def is_mnc_company(company):
    text = str(company or '').strip()
    if not text:
        return False
    normalised = _normalise_company(text)
    if any(p.search(normalised) for p in _WORD_RE.values()):
        return True
    squashed = re.sub(r'[^a-z0-9]', '', normalised)
    for key in MNC_COMPANIES:
        ks = re.sub(r'[^a-z0-9]', '', key)
        if ks and ks in squashed and (len(ks) > 2 or _WORD_RE[key].search(text)):
            return True
    return False


def passes_target_policy(raw):
    title = raw.get('title', '')
    skills = ' '.join(raw.get('required_skills') or [])
    return is_it_role(title, skills) and is_india_location(raw.get('location', ''))
