"""
Clinical assessment instruments with ICF mappings.

Standardized questionnaires used in Remote Patient Monitoring (RPM) for
functional assessment, mapped to ICF codes and qualifier scales.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ResponseOption:
    value: int
    label: str


@dataclass
class InstrumentItem:
    number: int
    text: str
    options: list[ResponseOption]


@dataclass
class ScoreRange:
    min_score: float
    max_score: float
    severity: str
    description: str
    icf_qualifier: int | None = None


@dataclass
class ICFMapping:
    code: str
    name: str
    relationship: str  # "primary", "secondary", "related"


@dataclass
class Instrument:
    id: str
    name: str
    abbreviation: str
    description: str
    domain: str
    conditions: list[str]
    items: list[InstrumentItem]
    scoring_method: str  # "sum", "mean", "weighted", "custom"
    score_ranges: list[ScoreRange]
    icf_mappings: list[ICFMapping]
    min_score: float
    max_score: float
    recall_period: str
    administration: str  # "self-report", "clinician", "mixed"
    completion_time: str
    references: list[str]
    rpm_frequency: str  # recommended RPM reassessment frequency
    notes: str = ""
    # Instruments with non-trivial scoring set this to a dedicated scorer
    # function; when None, the generic sum/mean path in score() applies.
    scorer: Callable[[list[int]], dict[str, Any]] | None = None

    def score(self, responses: list[int | float]) -> dict[str, Any]:
        if len(responses) != len(self.items):
            return {
                "error": f"Expected {len(self.items)} responses, got {len(responses)}."
            }

        if self.scoring_method == "mean":
            total = sum(responses) / len(responses)
        else:
            total = sum(responses)

        return _build_result(self, round(total, 2), response_count=len(responses))


def _build_result(instrument: "Instrument", total: float, **extras: Any) -> dict[str, Any]:
    """Assemble a scored result dict from an instrument's score ranges."""
    result: dict[str, Any] = {
        "instrument": instrument.abbreviation,
        "total_score": total,
        "min_possible": instrument.min_score,
        "max_possible": instrument.max_score,
        "severity": "Unknown",
        "description": "",
        "icf_qualifier": None,
        "response_count": len(instrument.items),
    }
    result.update(extras)
    for sr in instrument.score_ranges:
        if sr.min_score <= total <= sr.max_score:
            result["severity"] = sr.severity
            result["description"] = sr.description
            result["icf_qualifier"] = sr.icf_qualifier
            break
    return result


# ── Standard response scales ────────────────────────────────────────────────

LIKERT_0_3 = [
    ResponseOption(0, "Not at all"),
    ResponseOption(1, "Several days"),
    ResponseOption(2, "More than half the days"),
    ResponseOption(3, "Nearly every day"),
]

LIKERT_0_4 = [
    ResponseOption(0, "None"),
    ResponseOption(1, "Mild"),
    ResponseOption(2, "Moderate"),
    ResponseOption(3, "Severe"),
    ResponseOption(4, "Extreme / Cannot do"),
]

VAS_0_10 = [ResponseOption(i, str(i)) for i in range(11)]


# ── GAD-7 ────────────────────────────────────────────────────────────────────

GAD7 = Instrument(
    id="gad7",
    name="Generalized Anxiety Disorder 7-Item Scale",
    abbreviation="GAD-7",
    description=(
        "A brief self-report measure to identify probable cases of generalized "
        "anxiety disorder and assess symptom severity. Widely used in primary "
        "care and RPM programs."
    ),
    domain="Mental Health",
    conditions=["Generalized anxiety disorder", "Panic disorder", "Social anxiety disorder", "PTSD"],
    items=[
        InstrumentItem(1, "Feeling nervous, anxious, or on edge", LIKERT_0_3),
        InstrumentItem(2, "Not being able to stop or control worrying", LIKERT_0_3),
        InstrumentItem(3, "Worrying too much about different things", LIKERT_0_3),
        InstrumentItem(4, "Trouble relaxing", LIKERT_0_3),
        InstrumentItem(5, "Being so restless that it's hard to sit still", LIKERT_0_3),
        InstrumentItem(6, "Becoming easily annoyed or irritable", LIKERT_0_3),
        InstrumentItem(7, "Feeling afraid, as if something awful might happen", LIKERT_0_3),
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(0, 4, "Minimal", "Minimal anxiety; monitor only", 0),
        ScoreRange(5, 9, "Mild", "Mild anxiety; watchful waiting", 1),
        ScoreRange(10, 14, "Moderate", "Moderate anxiety; consider treatment", 2),
        ScoreRange(15, 21, "Severe", "Severe anxiety; active treatment indicated", 3),
    ],
    icf_mappings=[
        ICFMapping("b152", "Emotional functions", "primary"),
        ICFMapping("b1522", "Range of emotion", "primary"),
        ICFMapping("b1528", "Emotional functions, other specified", "secondary"),
        ICFMapping("b130", "Energy and drive functions", "secondary"),
        ICFMapping("b134", "Sleep functions", "related"),
        ICFMapping("d240", "Handling stress and other psychological demands", "primary"),
        ICFMapping("d720", "Complex interpersonal interactions", "related"),
    ],
    min_score=0,
    max_score=21,
    recall_period="2 weeks",
    administration="self-report",
    completion_time="2-3 minutes",
    references=["Spitzer RL, Kroenke K, Williams JBW, Löwe B. A brief measure for assessing generalized anxiety disorder. Arch Intern Med. 2006;166(10):1092-1097."],
    rpm_frequency="Weekly to biweekly",
)

# ── PHQ-9 ────────────────────────────────────────────────────────────────────

PHQ9 = Instrument(
    id="phq9",
    name="Patient Health Questionnaire-9",
    abbreviation="PHQ-9",
    description=(
        "A 9-item self-report measure for screening, diagnosing, monitoring, "
        "and measuring the severity of depression. Based on DSM criteria."
    ),
    domain="Mental Health",
    conditions=["Major depressive disorder", "Persistent depressive disorder", "Adjustment disorder"],
    items=[
        InstrumentItem(1, "Little interest or pleasure in doing things", LIKERT_0_3),
        InstrumentItem(2, "Feeling down, depressed, or hopeless", LIKERT_0_3),
        InstrumentItem(3, "Trouble falling or staying asleep, or sleeping too much", LIKERT_0_3),
        InstrumentItem(4, "Feeling tired or having little energy", LIKERT_0_3),
        InstrumentItem(5, "Poor appetite or overeating", LIKERT_0_3),
        InstrumentItem(6, "Feeling bad about yourself — or that you are a failure or have let yourself or your family down", LIKERT_0_3),
        InstrumentItem(7, "Trouble concentrating on things, such as reading the newspaper or watching television", LIKERT_0_3),
        InstrumentItem(8, "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual", LIKERT_0_3),
        InstrumentItem(9, "Thoughts that you would be better off dead, or of hurting yourself in some way", LIKERT_0_3),
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(0, 4, "Minimal", "Minimal depression; may not require treatment", 0),
        ScoreRange(5, 9, "Mild", "Mild depression; watchful waiting, repeat at follow-up", 1),
        ScoreRange(10, 14, "Moderate", "Moderate depression; treatment plan indicated", 2),
        ScoreRange(15, 19, "Moderately Severe", "Moderately severe depression; active treatment with pharmacotherapy and/or psychotherapy", 3),
        ScoreRange(20, 27, "Severe", "Severe depression; immediate treatment, consider referral to specialist", 4),
    ],
    icf_mappings=[
        ICFMapping("b152", "Emotional functions", "primary"),
        ICFMapping("b130", "Energy and drive functions", "primary"),
        ICFMapping("b134", "Sleep functions", "primary"),
        ICFMapping("b140", "Attention functions", "secondary"),
        ICFMapping("b1300", "Energy level", "primary"),
        ICFMapping("b5105", "Swallowing (appetite changes)", "secondary"),
        ICFMapping("d230", "Carrying out daily routine", "primary"),
        ICFMapping("d240", "Handling stress and other psychological demands", "secondary"),
        ICFMapping("d177", "Making decisions", "related"),
        ICFMapping("d920", "Recreation and leisure", "related"),
    ],
    min_score=0,
    max_score=27,
    recall_period="2 weeks",
    administration="self-report",
    completion_time="2-5 minutes",
    references=["Kroenke K, Spitzer RL, Williams JBW. The PHQ-9: validity of a brief depression severity measure. J Gen Intern Med. 2001;16(9):606-613."],
    rpm_frequency="Weekly to biweekly",
    notes="Item 9 screens for suicidal ideation and requires immediate clinical follow-up if endorsed.",
)

# ── RADAI-5 ──────────────────────────────────────────────────────────────────

RADAI5 = Instrument(
    id="radai5",
    name="Rheumatoid Arthritis Disease Activity Index-5",
    abbreviation="RADAI-5",
    description=(
        "A 5-item patient self-report measure of rheumatoid arthritis disease "
        "activity. Uses 0-10 visual analog scales. Score is the mean of all items."
    ),
    domain="Rheumatology",
    conditions=["Rheumatoid arthritis"],
    items=[
        InstrumentItem(1, "How active was your rheumatoid arthritis on average during the last 6 months?", VAS_0_10),
        InstrumentItem(2, "How active is your rheumatoid arthritis today in terms of joint tenderness and swelling?", VAS_0_10),
        InstrumentItem(3, "How would you describe your arthritis pain today?", VAS_0_10),
        InstrumentItem(4, "How would you describe your current level of morning stiffness?", VAS_0_10),
        InstrumentItem(5, "How would you rate your current overall functional capacity (ability to carry out daily activities)?", VAS_0_10),
    ],
    scoring_method="mean",
    score_ranges=[
        ScoreRange(0.0, 1.4, "Near remission", "Disease activity near remission", 0),
        ScoreRange(1.5, 3.0, "Low", "Low disease activity", 1),
        ScoreRange(3.1, 5.0, "Moderate", "Moderate disease activity", 2),
        ScoreRange(5.1, 7.5, "High", "High disease activity", 3),
        ScoreRange(7.6, 10.0, "Very high", "Very high disease activity", 4),
    ],
    icf_mappings=[
        ICFMapping("b280", "Sensation of pain", "primary"),
        ICFMapping("b710", "Mobility of joint functions", "primary"),
        ICFMapping("b770", "Gait pattern functions", "secondary"),
        ICFMapping("b7101", "Mobility of several joints", "primary"),
        ICFMapping("s710", "Structure of head and neck region", "related"),
        ICFMapping("s720", "Structure of shoulder region", "related"),
        ICFMapping("s730", "Structure of upper extremity", "primary"),
        ICFMapping("s750", "Structure of lower extremity", "primary"),
        ICFMapping("d230", "Carrying out daily routine", "primary"),
        ICFMapping("d440", "Fine hand use", "secondary"),
        ICFMapping("d445", "Hand and arm use", "secondary"),
        ICFMapping("d450", "Walking", "secondary"),
    ],
    min_score=0.0,
    max_score=10.0,
    recall_period="Today / 6 months (item 1)",
    administration="self-report",
    completion_time="2-3 minutes",
    references=["Leeb BF, et al. The patient's perspective and rheumatoid arthritis disease activity indexes. Rheumatology. 2004;43(9):1122-1125."],
    rpm_frequency="Weekly to monthly",
)

# ── SLEDAI-2K ────────────────────────────────────────────────────────────────

_SLEDAI_PRESENT_ABSENT = [ResponseOption(0, "Absent"), ResponseOption(1, "Present")]

SLEDAI2K = Instrument(
    id="sledai2k",
    name="Systemic Lupus Erythematosus Disease Activity Index 2000",
    abbreviation="SLEDAI-2K",
    description=(
        "A weighted index measuring SLE disease activity across 24 descriptors "
        "in 9 organ systems. Each descriptor is present/absent and carries a "
        "predefined weight (1-8). Total is the sum of weights for present items."
    ),
    domain="Rheumatology",
    conditions=["Systemic lupus erythematosus"],
    items=[
        InstrumentItem(1, "Seizure: recent onset, exclude metabolic, infectious, or drug causes", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(2, "Psychosis: altered ability to function due to severe disturbance in perception of reality", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(3, "Organic brain syndrome: altered mental function with impaired orientation, memory, or other cognitive function", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(4, "Visual disturbance: retinal changes of SLE (cytoid bodies, retinal hemorrhages, choroid/optic neuritis)", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(5, "Cranial nerve disorder: new onset sensory or motor neuropathy involving cranial nerves", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(6, "Lupus headache: severe, persistent headache; may be migrainous, unresponsive to narcotics", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(7, "CVA: new onset cerebrovascular accident(s), exclude arteriosclerosis", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(8, "Vasculitis: ulceration, gangrene, tender finger nodules, periungual infarction, splinter hemorrhages, or biopsy/angiogram proof of vasculitis", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(9, "Arthritis: ≥2 joints with pain and signs of inflammation", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(10, "Myositis: proximal muscle aching/weakness associated with elevated CPK/aldolase, EMG changes, or biopsy showing myositis", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(11, "Urinary casts: heme-granular or red blood cell casts", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(12, "Hematuria: >5 red blood cells/high power field, exclude stone, infection, or other cause", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(13, "Proteinuria: >0.5 g/24 hours, new onset or recent increase", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(14, "Pyuria: >5 white blood cells/high power field, exclude infection", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(15, "New rash: new onset or recurrence of inflammatory type rash", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(16, "Alopecia: new onset or recurrence of abnormal, patchy or diffuse hair loss", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(17, "Mucosal ulcers: new onset or recurrence of oral or nasal ulcerations", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(18, "Pleurisy: pleuritic chest pain with pleural rub or effusion, or pleural thickening", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(19, "Pericarditis: pericardial pain with at least 1 of: rub, effusion, or ECG/echo confirmation", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(20, "Low complement: decrease in CH50, C3, or C4 below lower limit of normal", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(21, "Increased DNA binding: >25% binding by Farr assay or above normal range", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(22, "Fever: >38°C (100.4°F), exclude infectious cause", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(23, "Thrombocytopenia: <100,000 platelets/mm³", _SLEDAI_PRESENT_ABSENT),
        InstrumentItem(24, "Leukopenia: <3,000 white blood cells/mm³, exclude drug causes", _SLEDAI_PRESENT_ABSENT),
    ],
    scoring_method="weighted",
    score_ranges=[
        ScoreRange(0, 0, "No activity", "No measurable disease activity", 0),
        ScoreRange(1, 5, "Mild", "Mild disease activity", 1),
        ScoreRange(6, 10, "Moderate", "Moderate disease activity", 2),
        ScoreRange(11, 19, "High", "High disease activity; active treatment adjustment indicated", 3),
        ScoreRange(20, 105, "Very high", "Very high disease activity; aggressive treatment indicated", 4),
    ],
    icf_mappings=[
        ICFMapping("b280", "Sensation of pain", "primary"),
        ICFMapping("b430", "Haematological system functions", "primary"),
        ICFMapping("b435", "Immunological system functions", "primary"),
        ICFMapping("b440", "Respiration functions", "secondary"),
        ICFMapping("b610", "Urinary excretory functions", "secondary"),
        ICFMapping("b710", "Mobility of joint functions", "primary"),
        ICFMapping("b730", "Muscle power functions", "secondary"),
        ICFMapping("b810", "Protective functions of the skin", "secondary"),
        ICFMapping("s410", "Structure of cardiovascular system", "related"),
        ICFMapping("s610", "Structure of urinary system", "related"),
        ICFMapping("s810", "Structure of areas of skin", "related"),
        ICFMapping("d230", "Carrying out daily routine", "primary"),
        ICFMapping("d450", "Walking", "related"),
        ICFMapping("d5", "Self-care", "related"),
    ],
    min_score=0,
    max_score=105,
    recall_period="10 days",
    administration="clinician",
    completion_time="5-10 minutes",
    references=["Gladman DD, Ibañez D, Urowitz MB. Systemic Lupus Erythematosus Disease Activity Index 2000. J Rheumatol. 2002;29(2):288-291."],
    rpm_frequency="Monthly to quarterly",
    notes="Weighted scoring: items 1-8 = 8 points each, 9-10 = 4 points each, 11-14 = 4 points each, 15-19 = 2 points each, 20-21 = 2 points each, 22-24 = 1 point each.",
)

# SLEDAI-2K item weights
SLEDAI_WEIGHTS = {
    1: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 8, 7: 8, 8: 8,  # Neurological + Vascular
    9: 4, 10: 4,                                          # Musculoskeletal
    11: 4, 12: 4, 13: 4, 14: 4,                          # Renal
    15: 2, 16: 2, 17: 2, 18: 2, 19: 2,                   # Dermal + Serositis
    20: 2, 21: 2,                                          # Immunological
    22: 1, 23: 1, 24: 1,                                   # Constitutional + Haematological
}


def score_sledai(responses: list[int]) -> dict[str, Any]:
    if len(responses) != 24:
        return {"error": f"SLEDAI-2K requires 24 responses, got {len(responses)}."}
    total = sum(resp * SLEDAI_WEIGHTS[i + 1] for i, resp in enumerate(responses))
    return _build_result(
        SLEDAI2K, total,
        active_descriptors=sum(responses),
        organ_systems=_sledai_organ_summary(responses),
    )


def _sledai_organ_summary(responses: list[int]) -> dict[str, bool]:
    return {
        "neurological": any(responses[i] for i in range(0, 7)),
        "vascular": bool(responses[7]),
        "musculoskeletal": any(responses[i] for i in range(8, 10)),
        "renal": any(responses[i] for i in range(10, 14)),
        "dermal": any(responses[i] for i in range(14, 17)),
        "serositis": any(responses[i] for i in range(17, 19)),
        "immunological": any(responses[i] for i in range(19, 21)),
        "constitutional": bool(responses[21]),
        "haematological": any(responses[i] for i in range(22, 24)),
    }


# ── WHODAS 2.0 (12-item) ────────────────────────────────────────────────────

WHODAS2_12 = Instrument(
    id="whodas2_12",
    name="WHO Disability Assessment Schedule 2.0 (12-Item)",
    abbreviation="WHODAS 2.0",
    description=(
        "A 12-item version of the WHO Disability Assessment Schedule, directly "
        "based on the ICF conceptual framework. Measures health and disability "
        "across 6 life domains. The gold standard for ICF-linked assessment."
    ),
    domain="General Function",
    conditions=["Any health condition", "Disability assessment", "Rehabilitation outcomes"],
    items=[
        InstrumentItem(1, "Standing for long periods such as 30 minutes?", LIKERT_0_4),
        InstrumentItem(2, "Taking care of your household responsibilities?", LIKERT_0_4),
        InstrumentItem(3, "Learning a new task, for example, learning how to get to a new place?", LIKERT_0_4),
        InstrumentItem(4, "How much of a problem did you have joining in community activities (for example, festivities, religious or other activities) in the same way as anyone else can?", LIKERT_0_4),
        InstrumentItem(5, "How much have you been emotionally affected by your health problems?", LIKERT_0_4),
        InstrumentItem(6, "Concentrating on doing something for ten minutes?", LIKERT_0_4),
        InstrumentItem(7, "Walking a long distance such as a kilometre [or equivalent]?", LIKERT_0_4),
        InstrumentItem(8, "Washing your whole body?", LIKERT_0_4),
        InstrumentItem(9, "Getting dressed?", LIKERT_0_4),
        InstrumentItem(10, "Dealing with people you do not know?", LIKERT_0_4),
        InstrumentItem(11, "Maintaining a friendship?", LIKERT_0_4),
        InstrumentItem(12, "Your day-to-day work/school?", LIKERT_0_4),
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(0, 4, "None", "No disability", 0),
        ScoreRange(5, 12, "Mild", "Mild disability", 1),
        ScoreRange(13, 24, "Moderate", "Moderate disability", 2),
        ScoreRange(25, 36, "Severe", "Severe disability", 3),
        ScoreRange(37, 48, "Extreme", "Extreme / complete disability", 4),
    ],
    icf_mappings=[
        ICFMapping("d410", "Changing basic body position", "primary"),
        ICFMapping("d450", "Walking", "primary"),
        ICFMapping("d510", "Washing oneself", "primary"),
        ICFMapping("d540", "Dressing", "primary"),
        ICFMapping("d640", "Doing housework", "primary"),
        ICFMapping("d155", "Acquiring skills", "primary"),
        ICFMapping("d160", "Focusing attention", "primary"),
        ICFMapping("d710", "Basic interpersonal interactions", "primary"),
        ICFMapping("d720", "Complex interpersonal interactions", "primary"),
        ICFMapping("d910", "Community life", "primary"),
        ICFMapping("d920", "Recreation and leisure", "secondary"),
        ICFMapping("d850", "Remunerative employment", "primary"),
        ICFMapping("b152", "Emotional functions", "secondary"),
    ],
    min_score=0,
    max_score=48,
    recall_period="30 days",
    administration="self-report",
    completion_time="5 minutes",
    references=["Üstün TB, et al. Measuring Health and Disability: Manual for WHO Disability Assessment Schedule (WHODAS 2.0). WHO, 2010."],
    rpm_frequency="Monthly",
    notes="Directly derived from ICF. The WHO's recommended measure of health and disability.",
)

# ── HAQ-DI ───────────────────────────────────────────────────────────────────

_HAQ_OPTIONS = [
    ResponseOption(0, "Without any difficulty"),
    ResponseOption(1, "With some difficulty"),
    ResponseOption(2, "With much difficulty"),
    ResponseOption(3, "Unable to do"),
]

HAQ_DI = Instrument(
    id="haq_di",
    name="Health Assessment Questionnaire - Disability Index",
    abbreviation="HAQ-DI",
    description=(
        "A 20-item self-report measure of functional ability across 8 categories "
        "of daily living. Widely used in rheumatology for RA, PsA, SLE, and other "
        "conditions. Score is the mean of 8 category scores (0-3)."
    ),
    domain="Rheumatology",
    conditions=["Rheumatoid arthritis", "Psoriatic arthritis", "Systemic lupus erythematosus", "Osteoarthritis", "Scleroderma"],
    items=[
        # Dressing & Grooming
        InstrumentItem(1, "Dress yourself, including tying shoelaces and doing buttons?", _HAQ_OPTIONS),
        InstrumentItem(2, "Shampoo your hair?", _HAQ_OPTIONS),
        # Arising
        InstrumentItem(3, "Stand up from a straight chair?", _HAQ_OPTIONS),
        InstrumentItem(4, "Get in and out of bed?", _HAQ_OPTIONS),
        # Eating
        InstrumentItem(5, "Cut your meat?", _HAQ_OPTIONS),
        InstrumentItem(6, "Lift a full cup or glass to your mouth?", _HAQ_OPTIONS),
        InstrumentItem(7, "Open a new milk carton?", _HAQ_OPTIONS),
        # Walking
        InstrumentItem(8, "Walk outdoors on flat ground?", _HAQ_OPTIONS),
        InstrumentItem(9, "Climb up five steps?", _HAQ_OPTIONS),
        # Hygiene
        InstrumentItem(10, "Wash and dry your entire body?", _HAQ_OPTIONS),
        InstrumentItem(11, "Take a tub bath?", _HAQ_OPTIONS),
        InstrumentItem(12, "Get on and off the toilet?", _HAQ_OPTIONS),
        # Reach
        InstrumentItem(13, "Reach and get down a 5-pound object from above your head?", _HAQ_OPTIONS),
        InstrumentItem(14, "Bend down to pick up clothing from the floor?", _HAQ_OPTIONS),
        # Grip
        InstrumentItem(15, "Open car doors?", _HAQ_OPTIONS),
        InstrumentItem(16, "Open jars which have been previously opened?", _HAQ_OPTIONS),
        InstrumentItem(17, "Turn faucets on and off?", _HAQ_OPTIONS),
        # Activities
        InstrumentItem(18, "Run errands and shop?", _HAQ_OPTIONS),
        InstrumentItem(19, "Get in and out of a car?", _HAQ_OPTIONS),
        InstrumentItem(20, "Do chores such as vacuuming or yard work?", _HAQ_OPTIONS),
    ],
    scoring_method="custom",
    score_ranges=[
        ScoreRange(0.0, 0.5, "Mild difficulty", "Mild to no functional difficulty", 0),
        ScoreRange(0.51, 1.0, "Moderate difficulty", "Moderate functional difficulty", 1),
        ScoreRange(1.01, 2.0, "Severe difficulty", "Severe functional difficulty", 2),
        ScoreRange(2.01, 3.0, "Very severe", "Very severe disability; unable to perform most activities", 3),
    ],
    icf_mappings=[
        ICFMapping("d540", "Dressing", "primary"),
        ICFMapping("d520", "Caring for body parts", "primary"),
        ICFMapping("d410", "Changing basic body position", "primary"),
        ICFMapping("d550", "Eating", "primary"),
        ICFMapping("d560", "Drinking", "primary"),
        ICFMapping("d450", "Walking", "primary"),
        ICFMapping("d455", "Moving around", "primary"),
        ICFMapping("d510", "Washing oneself", "primary"),
        ICFMapping("d530", "Toileting", "primary"),
        ICFMapping("d445", "Hand and arm use", "primary"),
        ICFMapping("d440", "Fine hand use", "primary"),
        ICFMapping("d430", "Lifting and carrying objects", "primary"),
        ICFMapping("d640", "Doing housework", "primary"),
        ICFMapping("d620", "Acquisition of goods and services", "secondary"),
        ICFMapping("d470", "Using transportation", "secondary"),
    ],
    min_score=0.0,
    max_score=3.0,
    recall_period="Past week",
    administration="self-report",
    completion_time="5-8 minutes",
    references=["Fries JF, et al. The Health Assessment Questionnaire: A clinical measure of arthritis. Arthritis Rheum. 1980;23(2):137-145."],
    rpm_frequency="Monthly",
    notes="Score = mean of 8 category scores. Each category score = highest item score in that category. Categories: dressing (1-2), arising (3-4), eating (5-7), walking (8-9), hygiene (10-12), reach (13-14), grip (15-17), activities (18-20).",
)

HAQ_CATEGORIES = {
    "Dressing & Grooming": [1, 2],
    "Arising": [3, 4],
    "Eating": [5, 6, 7],
    "Walking": [8, 9],
    "Hygiene": [10, 11, 12],
    "Reach": [13, 14],
    "Grip": [15, 16, 17],
    "Activities": [18, 19, 20],
}


def score_haq(responses: list[int]) -> dict[str, Any]:
    if len(responses) != 20:
        return {"error": f"HAQ-DI requires 20 responses, got {len(responses)}."}
    category_scores = {
        cat_name: max(responses[n - 1] for n in item_numbers)
        for cat_name, item_numbers in HAQ_CATEGORIES.items()
    }
    total = round(sum(category_scores.values()) / 8, 2)
    return _build_result(HAQ_DI, total, category_scores=category_scores)


# ── PROMIS Global-10 ─────────────────────────────────────────────────────────

_PROMIS_EXCELLENT_POOR = [
    ResponseOption(5, "Excellent"),
    ResponseOption(4, "Very good"),
    ResponseOption(3, "Good"),
    ResponseOption(2, "Fair"),
    ResponseOption(1, "Poor"),
]

_PROMIS_NOT_AT_ALL_COMPLETELY = [
    ResponseOption(5, "Not at all"),
    ResponseOption(4, "A little"),
    ResponseOption(3, "Somewhat"),
    ResponseOption(2, "Quite a bit"),
    ResponseOption(1, "Very much"),
]

_PROMIS_NEVER_ALWAYS = [
    ResponseOption(5, "Never"),
    ResponseOption(4, "Rarely"),
    ResponseOption(3, "Sometimes"),
    ResponseOption(2, "Often"),
    ResponseOption(1, "Always"),
]


PROMIS_10 = Instrument(
    id="promis10",
    name="PROMIS Global Health-10",
    abbreviation="PROMIS-10",
    description=(
        "A 10-item measure of global physical and mental health from the "
        "Patient-Reported Outcomes Measurement Information System (PROMIS). "
        "Yields two summary scores: Global Physical Health (GPH) and "
        "Global Mental Health (GMH)."
    ),
    domain="General Health",
    conditions=["Any health condition", "Chronic disease monitoring", "General wellness"],
    items=[
        InstrumentItem(1, "In general, would you say your health is...", _PROMIS_EXCELLENT_POOR),
        InstrumentItem(2, "In general, would you say your quality of life is...", _PROMIS_EXCELLENT_POOR),
        InstrumentItem(3, "In general, how would you rate your physical health?", _PROMIS_EXCELLENT_POOR),
        InstrumentItem(4, "In general, how would you rate your mental health, including your mood and your ability to think?", _PROMIS_EXCELLENT_POOR),
        InstrumentItem(5, "In general, how would you rate your satisfaction with your social activities and relationships?", _PROMIS_EXCELLENT_POOR),
        InstrumentItem(6, "To what extent are you able to carry out your everyday physical activities such as walking, climbing stairs, carrying groceries, or moving a chair?", _PROMIS_NOT_AT_ALL_COMPLETELY),
        InstrumentItem(7, "How often have you been bothered by emotional problems such as feeling anxious, depressed, or irritable?", _PROMIS_NEVER_ALWAYS),
        InstrumentItem(8, "How would you rate your fatigue on average?", [
            ResponseOption(5, "None"),
            ResponseOption(4, "Mild"),
            ResponseOption(3, "Moderate"),
            ResponseOption(2, "Severe"),
            ResponseOption(1, "Very severe"),
        ]),
        InstrumentItem(9, "How would you rate your pain on average? (0=no pain, 10=worst pain imaginable)", VAS_0_10),
        InstrumentItem(10, "In general, please rate how well you carry out your usual social activities and roles (activities at work, at home, with friends, in community).", _PROMIS_EXCELLENT_POOR),
    ],
    scoring_method="custom",
    score_ranges=[
        ScoreRange(10, 20, "Poor", "Poor global health", 3),
        ScoreRange(21, 30, "Fair", "Fair global health", 2),
        ScoreRange(31, 40, "Good", "Good global health", 1),
        ScoreRange(41, 50, "Very good to excellent", "Very good to excellent global health", 0),
    ],
    icf_mappings=[
        ICFMapping("b130", "Energy and drive functions", "primary"),
        ICFMapping("b152", "Emotional functions", "primary"),
        ICFMapping("b280", "Sensation of pain", "primary"),
        ICFMapping("d230", "Carrying out daily routine", "primary"),
        ICFMapping("d450", "Walking", "secondary"),
        ICFMapping("d455", "Moving around", "secondary"),
        ICFMapping("d710", "Basic interpersonal interactions", "secondary"),
        ICFMapping("d920", "Recreation and leisure", "secondary"),
    ],
    min_score=10,
    max_score=50,
    recall_period="7 days",
    administration="self-report",
    completion_time="2-4 minutes",
    references=["Hays RD, et al. Development of physical and mental health summary scores from the PROMIS Global items. Qual Life Res. 2009;18(7):873-880."],
    rpm_frequency="Weekly to monthly",
    notes=(
        "Items 7 and 8 are reverse-coded via their option values. Item 9 (0-10 pain) "
        "is recoded to 1-5 before summing. GPH items: 3, 6, 8, 9. GMH items: 2, 4, 5, 7. "
        "T-score conversion tables available from PROMIS."
    ),
)

# PROMIS subscale item assignments
PROMIS_GPH_ITEMS = [3, 6, 8, 9]  # Global Physical Health (item 9 recoded)
PROMIS_GMH_ITEMS = [2, 4, 5, 7]  # Global Mental Health


def score_promis(responses: list[int]) -> dict[str, Any]:
    if len(responses) != 10:
        return {"error": f"PROMIS-10 requires 10 responses, got {len(responses)}."}
    # Recode item 9 pain (0-10) to the 1-5 scale: 0→5, 1-3→4, 4-6→3, 7-9→2, 10→1
    pain = responses[8]
    recoded = list(responses)
    recoded[8] = 5 if pain == 0 else 4 if pain <= 3 else 3 if pain <= 6 else 2 if pain <= 9 else 1
    total = sum(recoded)
    return _build_result(
        PROMIS_10, total,
        gph_raw=sum(recoded[n - 1] for n in PROMIS_GPH_ITEMS),
        gmh_raw=sum(recoded[n - 1] for n in PROMIS_GMH_ITEMS),
    )


# ── CAT (COPD Assessment Test) ──────────────────────────────────────────────

_CAT_ITEMS_DATA = [
    ("I never cough", "I cough all the time"),
    ("I have no phlegm (mucus) in my chest at all", "My chest is completely full of phlegm (mucus)"),
    ("My chest does not feel tight at all", "My chest feels very tight"),
    ("When I walk up a hill or one flight of stairs I am not breathless", "When I walk up a hill or one flight of stairs I am very breathless"),
    ("I am not limited doing any activities at home", "I am very limited doing activities at home"),
    ("I am confident leaving my home despite my lung condition", "I am not at all confident leaving my home because of my lung condition"),
    ("I sleep soundly", "I don't sleep soundly because of my lung condition"),
    ("I have lots of energy", "I have no energy at all"),
]

_CAT_OPTIONS = [ResponseOption(i, str(i)) for i in range(6)]

CAT = Instrument(
    id="cat",
    name="COPD Assessment Test",
    abbreviation="CAT",
    description=(
        "An 8-item patient-completed questionnaire for assessing and monitoring "
        "COPD. Each item is scored 0-5 on a semantic differential scale."
    ),
    domain="Respiratory",
    conditions=["Chronic obstructive pulmonary disease", "Chronic bronchitis", "Emphysema"],
    items=[
        InstrumentItem(i + 1, f"{left} (0) ←→ (5) {right}", _CAT_OPTIONS)
        for i, (left, right) in enumerate(_CAT_ITEMS_DATA)
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(0, 10, "Low impact", "Low impact of COPD on daily life", 1),
        ScoreRange(11, 20, "Medium impact", "Medium impact; some limitations", 2),
        ScoreRange(21, 30, "High impact", "High impact; significant limitations", 3),
        ScoreRange(31, 40, "Very high impact", "Very high impact; severely limited", 4),
    ],
    icf_mappings=[
        ICFMapping("b440", "Respiration functions", "primary"),
        ICFMapping("b450", "Additional respiratory functions (cough)", "primary"),
        ICFMapping("b455", "Exercise tolerance functions", "primary"),
        ICFMapping("b134", "Sleep functions", "secondary"),
        ICFMapping("b130", "Energy and drive functions", "primary"),
        ICFMapping("d450", "Walking", "secondary"),
        ICFMapping("d640", "Doing housework", "secondary"),
        ICFMapping("d910", "Community life", "related"),
    ],
    min_score=0,
    max_score=40,
    recall_period="Current",
    administration="self-report",
    completion_time="2-3 minutes",
    references=["Jones PW, et al. Development and first validation of the COPD Assessment Test. Eur Respir J. 2009;34(3):648-654."],
    rpm_frequency="Weekly to monthly",
)

# ── ODI (Oswestry Disability Index) ─────────────────────────────────────────

_ODI_PAIN_OPTS = [
    ResponseOption(0, "I have no pain at the moment"),
    ResponseOption(1, "The pain is very mild at the moment"),
    ResponseOption(2, "The pain is moderate at the moment"),
    ResponseOption(3, "The pain is fairly severe at the moment"),
    ResponseOption(4, "The pain is very severe at the moment"),
    ResponseOption(5, "The pain is the worst imaginable at the moment"),
]

_ODI_GENERIC_OPTS = [
    ResponseOption(0, "No difficulty / normal"),
    ResponseOption(1, "Slight limitation"),
    ResponseOption(2, "Moderate limitation"),
    ResponseOption(3, "Fairly significant limitation"),
    ResponseOption(4, "Severely limited"),
    ResponseOption(5, "Completely unable / worst"),
]

ODI = Instrument(
    id="odi",
    name="Oswestry Disability Index",
    abbreviation="ODI",
    description=(
        "A 10-item questionnaire measuring the impact of low back pain on daily "
        "functioning. Each section scored 0-5; total as percentage of maximum. "
        "The gold standard for low back pain functional assessment."
    ),
    domain="Pain / Musculoskeletal",
    conditions=["Low back pain", "Lumbar disc disease", "Spinal stenosis", "Post-spinal surgery"],
    items=[
        InstrumentItem(1, "Pain intensity", _ODI_PAIN_OPTS),
        InstrumentItem(2, "Personal care (washing, dressing)", _ODI_GENERIC_OPTS),
        InstrumentItem(3, "Lifting", _ODI_GENERIC_OPTS),
        InstrumentItem(4, "Walking", _ODI_GENERIC_OPTS),
        InstrumentItem(5, "Sitting", _ODI_GENERIC_OPTS),
        InstrumentItem(6, "Standing", _ODI_GENERIC_OPTS),
        InstrumentItem(7, "Sleeping", _ODI_GENERIC_OPTS),
        InstrumentItem(8, "Social life / sex life", _ODI_GENERIC_OPTS),
        InstrumentItem(9, "Travelling", _ODI_GENERIC_OPTS),
        InstrumentItem(10, "Employment / homemaking", _ODI_GENERIC_OPTS),
    ],
    scoring_method="custom",
    score_ranges=[
        ScoreRange(0, 20, "Minimal disability", "Can cope with most living activities; usually no treatment needed beyond advice", 0),
        ScoreRange(21, 40, "Moderate disability", "More difficulty with daily activities; conservative treatment", 1),
        ScoreRange(41, 60, "Severe disability", "Pain is a major problem; detailed investigation required", 2),
        ScoreRange(61, 80, "Crippled", "Back pain impinges on all aspects of daily living", 3),
        ScoreRange(81, 100, "Bed-bound / exaggerating", "Bed-bound or symptoms are exaggerated", 4),
    ],
    icf_mappings=[
        ICFMapping("b280", "Sensation of pain", "primary"),
        ICFMapping("b28013", "Pain in back", "primary"),
        ICFMapping("b710", "Mobility of joint functions", "primary"),
        ICFMapping("b134", "Sleep functions", "secondary"),
        ICFMapping("d410", "Changing basic body position", "primary"),
        ICFMapping("d430", "Lifting and carrying objects", "primary"),
        ICFMapping("d450", "Walking", "primary"),
        ICFMapping("d475", "Driving", "secondary"),
        ICFMapping("d510", "Washing oneself", "secondary"),
        ICFMapping("d540", "Dressing", "secondary"),
        ICFMapping("d850", "Remunerative employment", "secondary"),
        ICFMapping("d920", "Recreation and leisure", "related"),
    ],
    min_score=0,
    max_score=100,
    recall_period="Current / today",
    administration="self-report",
    completion_time="3-5 minutes",
    references=["Fairbank JC, Pynsent PB. The Oswestry Disability Index. Spine. 2000;25(22):2940-2953."],
    rpm_frequency="Biweekly to monthly",
    notes="Score = (sum of item scores / (5 × number of answered sections)) × 100. If a section is not answered, it is excluded.",
)


def score_odi(responses: list[int]) -> dict[str, Any]:
    if len(responses) != 10:
        return {"error": f"ODI requires 10 responses, got {len(responses)}."}
    total = round((sum(responses) / 50) * 100, 1)
    return _build_result(ODI, total, unit="%")


# ── NRS Pain ─────────────────────────────────────────────────────────────────

NRS_PAIN = Instrument(
    id="nrs_pain",
    name="Numeric Rating Scale for Pain",
    abbreviation="NRS Pain",
    description=(
        "A single-item 0-10 numeric scale for rapid pain intensity assessment. "
        "The most commonly used pain measure in RPM and clinical practice."
    ),
    domain="Pain",
    conditions=["Any pain condition", "Chronic pain", "Post-surgical pain", "Cancer pain"],
    items=[
        InstrumentItem(1, "Rate your pain on a scale of 0 to 10, where 0 is no pain and 10 is the worst pain imaginable.", VAS_0_10),
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(0, 0, "No pain", "No pain", 0),
        ScoreRange(1, 3, "Mild", "Mild pain", 1),
        ScoreRange(4, 6, "Moderate", "Moderate pain", 2),
        ScoreRange(7, 9, "Severe", "Severe pain", 3),
        ScoreRange(10, 10, "Worst possible", "Worst possible pain", 4),
    ],
    icf_mappings=[
        ICFMapping("b280", "Sensation of pain", "primary"),
        ICFMapping("b28010", "Pain in head and neck", "related"),
        ICFMapping("b28011", "Pain in chest", "related"),
        ICFMapping("b28012", "Pain in stomach or abdomen", "related"),
        ICFMapping("b28013", "Pain in back", "related"),
        ICFMapping("b28014", "Pain in upper limb", "related"),
        ICFMapping("b28015", "Pain in lower limb", "related"),
        ICFMapping("b28016", "Pain in joints", "related"),
    ],
    min_score=0,
    max_score=10,
    recall_period="Current / past 24 hours",
    administration="self-report",
    completion_time="< 1 minute",
    references=["Hawker GA, et al. Measures of adult pain. Arthritis Care Res. 2011;63(S11):S240-S252."],
    rpm_frequency="Daily to weekly",
)

# ── Falls Efficacy Scale - International (Short) ────────────────────────────

_FES_OPTIONS = [
    ResponseOption(1, "Not at all concerned"),
    ResponseOption(2, "Somewhat concerned"),
    ResponseOption(3, "Fairly concerned"),
    ResponseOption(4, "Very concerned"),
]

FES_I_SHORT = Instrument(
    id="fes_i_short",
    name="Falls Efficacy Scale - International (Short Form)",
    abbreviation="Short FES-I",
    description=(
        "A 7-item measure of fear of falling / concern about falls during "
        "daily activities. Used in geriatric and rehabilitation RPM programs."
    ),
    domain="Geriatrics / Falls",
    conditions=["Fall risk", "Balance disorders", "Geriatric assessment", "Post-hip fracture"],
    items=[
        InstrumentItem(1, "Getting dressed or undressed", _FES_OPTIONS),
        InstrumentItem(2, "Taking a bath or shower", _FES_OPTIONS),
        InstrumentItem(3, "Getting in or out of a chair", _FES_OPTIONS),
        InstrumentItem(4, "Going up or down stairs", _FES_OPTIONS),
        InstrumentItem(5, "Reaching for something above your head or on the ground", _FES_OPTIONS),
        InstrumentItem(6, "Walking up or down a slope", _FES_OPTIONS),
        InstrumentItem(7, "Going out to a social event", _FES_OPTIONS),
    ],
    scoring_method="sum",
    score_ranges=[
        ScoreRange(7, 8, "Low concern", "Low concern about falling", 0),
        ScoreRange(9, 13, "Moderate concern", "Moderate concern about falling", 1),
        ScoreRange(14, 21, "High concern", "High concern about falling; fall risk assessment indicated", 2),
        ScoreRange(22, 28, "Severe concern", "Severe concern; activity avoidance likely", 3),
    ],
    icf_mappings=[
        ICFMapping("b235", "Vestibular functions", "secondary"),
        ICFMapping("b755", "Involuntary movement reaction functions", "primary"),
        ICFMapping("d410", "Changing basic body position", "primary"),
        ICFMapping("d450", "Walking", "primary"),
        ICFMapping("d455", "Moving around", "primary"),
        ICFMapping("d510", "Washing oneself", "secondary"),
        ICFMapping("d540", "Dressing", "secondary"),
        ICFMapping("d920", "Recreation and leisure", "related"),
        ICFMapping("e120", "Products and technology for personal indoor and outdoor mobility and transportation", "related"),
    ],
    min_score=7,
    max_score=28,
    recall_period="Current",
    administration="self-report",
    completion_time="2-3 minutes",
    references=["Kempen GIJM, et al. The Short FES-I: a shortened version of the Falls Efficacy Scale-International. Age Ageing. 2008;37(1):45-50."],
    rpm_frequency="Monthly",
)

# ═════════════════════════════════════════════════════════════════════════════
# Instrument Registry
# ═════════════════════════════════════════════════════════════════════════════

# Attach dedicated scorers to instruments whose scoring is not a plain sum/mean
SLEDAI2K.scorer = score_sledai
HAQ_DI.scorer = score_haq
ODI.scorer = score_odi
PROMIS_10.scorer = score_promis

INSTRUMENTS: dict[str, Instrument] = {
    inst.id: inst for inst in [
        GAD7, PHQ9, RADAI5, SLEDAI2K, WHODAS2_12,
        HAQ_DI, PROMIS_10, CAT, ODI, NRS_PAIN, FES_I_SHORT,
    ]
}

# Lookup by abbreviation or name (case-insensitive)
_ALIAS_MAP: dict[str, str] = {}
for _inst in INSTRUMENTS.values():
    _ALIAS_MAP[_inst.id] = _inst.id
    _ALIAS_MAP[_inst.abbreviation.lower()] = _inst.id
    _ALIAS_MAP[_inst.abbreviation.lower().replace("-", "")] = _inst.id
    _ALIAS_MAP[_inst.abbreviation.lower().replace("-", " ")] = _inst.id
    _ALIAS_MAP[_inst.name.lower()] = _inst.id
# Common shorthand aliases
_ALIAS_MAP.update({
    "gad": "gad7", "gad 7": "gad7",
    "phq": "phq9", "phq 9": "phq9",
    "radai": "radai5", "radai 5": "radai5",
    "sledai": "sledai2k", "sledai 2k": "sledai2k",
    "whodas": "whodas2_12", "whodas 2.0": "whodas2_12", "whodas2": "whodas2_12", "whodas 12": "whodas2_12",
    "haq": "haq_di", "haq di": "haq_di",
    "promis": "promis10", "promis 10": "promis10", "promis global": "promis10",
    "copd assessment test": "cat",
    "oswestry": "odi",
    "nrs": "nrs_pain", "pain nrs": "nrs_pain", "pain scale": "nrs_pain",
    "fes": "fes_i_short", "fes-i": "fes_i_short", "falls": "fes_i_short", "falls efficacy": "fes_i_short",
})


def resolve_instrument(name: str) -> Instrument | None:
    key = name.strip().lower()
    inst_id = _ALIAS_MAP.get(key)
    if inst_id:
        return INSTRUMENTS.get(inst_id)
    # Fuzzy: check if any alias starts with the input
    for alias, iid in _ALIAS_MAP.items():
        if alias.startswith(key):
            return INSTRUMENTS.get(iid)
    return None


def score_instrument(name: str, responses: list[int | float]) -> dict[str, Any]:
    inst = resolve_instrument(name)
    if not inst:
        return {"error": f"Unknown instrument '{name}'. Use icf_list_instruments to see available instruments."}

    if inst.scorer:
        return inst.scorer([int(r) for r in responses])

    return inst.score(responses)


DOMAINS = sorted(set(inst.domain for inst in INSTRUMENTS.values()))
