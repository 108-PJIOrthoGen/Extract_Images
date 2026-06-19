"""Central definitions of the template's structural keys.

These names mirror the layout of ``templates/template.json``. Keeping them in one
place means a change to the template's top-level shape is made here once, instead
of being hard-coded across the prompt builder, sparse merge and completeness code.
"""

# Top-level record sections.
TEST_RESULTS = "test_results"
ABNORMAL_FLAGS_SUMMARY = "abnormal_flags_summary"
EXTRACTION_META = "extraction_meta"

# Sections inside ``test_results``.
SECTION_LAB = "section_1_xet_nghiem"
SECTION_IMAGING = "section_2_chan_doan_hinh_anh"
SECTION_FUNCTIONAL = "section_3_tham_do_chuc_nang"

# Exam (imaging / functional) sections grouped for convenient iteration.
EXAM_SECTIONS = (SECTION_IMAGING, SECTION_FUNCTIONAL)

# Keys used by the sparse VLM payload (before merge into the full template).
SPARSE_DOCUMENT = "document"
SPARSE_PATIENT = "patient"
SPARSE_GROUPS = "groups"
SPARSE_IMAGING_FUNCTIONAL = "imaging_and_functional"
SPARSE_UNRECOGNIZED = "_unrecognized_sources"

# Top-level keys that a well-formed sparse response may contain. Used to reject
# garbage / wrong-shaped output and trigger a retry.
SPARSE_TOP_LEVEL_KEYS = (
    SPARSE_DOCUMENT,
    SPARSE_PATIENT,
    SPARSE_GROUPS,
    TEST_RESULTS,
    SPARSE_IMAGING_FUNCTIONAL,
)
