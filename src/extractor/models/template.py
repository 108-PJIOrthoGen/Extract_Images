"""Pydantic models for template schema validation."""

from typing import Any

from pydantic import BaseModel, Field


class TestItem(BaseModel):
    stt: int | None = None
    name: str = ""
    value: Any | None = None
    flag: str | None = None
    reference_range: str | None = None
    unit: str | None = None
    category: str | None = None
    sub_tests: list[dict[str, Any]] | None = None


class TestGroup(BaseModel):
    department: str | None = ""
    time_collected: str | None = ""
    time_resulted: str | None = ""
    category: str | None = None
    tests: list[TestItem] | None = Field(default_factory=list)


class DocumentInfo(BaseModel):
    title: str = ""
    hospital: str = ""
    record_number: str = ""
    exam_date: str = ""
    report_generated_at: str = ""


class PatientInfo(BaseModel):
    full_name: str = ""
    age: Any | None = None
    gender: str = ""
    address: str = ""
    card_number: str = ""
    clinical_diagnosis: str = ""


class TestResults(BaseModel):
    section_1_xet_nghiem: dict[str, Any] = Field(default_factory=dict)
    section_2_chan_doan_hinh_anh: dict[str, Any] = Field(default_factory=dict)
    section_3_tham_do_chuc_nang: dict[str, Any] = Field(default_factory=dict)


class AbnormalFlag(BaseModel):
    test: str = ""
    value: Any | None = None
    unit: str | None = None
    reference: str | None = None
    organism: str | None = None


class AbnormalFlagsSummary(BaseModel):
    HIGH: list[AbnormalFlag] = Field(default_factory=list)
    LOW: list[AbnormalFlag] = Field(default_factory=list)
    POSITIVE_CULTURE: list[AbnormalFlag] = Field(default_factory=list)


class TemplateSchema(BaseModel):
    document: DocumentInfo = Field(default_factory=DocumentInfo)
    patient: PatientInfo = Field(default_factory=PatientInfo)
    test_results: TestResults = Field(default_factory=TestResults)
    abnormal_flags_summary: AbnormalFlagsSummary = Field(default_factory=AbnormalFlagsSummary)

    class Config:
        extra = "allow"


def validate_template(data: dict[str, Any]) -> TemplateSchema:
    """Validate template data against Pydantic schema."""
    return TemplateSchema(**data)
