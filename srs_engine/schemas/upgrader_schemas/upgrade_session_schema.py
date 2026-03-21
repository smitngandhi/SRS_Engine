from __future__ import annotations

"""
upgrade_session_schema.py
─────────────────────────
Pydantic v2 models for the SRS Upgrader pipeline.

UpgradeSession is stored as JSON at:
    upgrade_sessions/{user_id}/{file_id}.json

It is the single source of truth for the state of an upgrade job.
The original ParsedSection tree is NEVER mutated — all upgrades
are stored here and merged at export time only.
"""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Models that use @computed_field must use this instead —
# computed fields are excluded from extra-input validation
class ComputedModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Per-section analysis result (from Section Analyser Agent) ────────────────

class SectionScore(ComputedModel):
    completeness: float = Field(..., ge=0, le=10, description="Is content thorough enough?")
    clarity: float      = Field(..., ge=0, le=10, description="Is language precise and unambiguous?")
    ieee_compliance: float = Field(..., ge=0, le=10, description="Follows IEEE 830 conventions?")
    testability: float  = Field(..., ge=0, le=10, description="Can requirements be verified/tested?")
    consistency: float  = Field(..., ge=0, le=10, description="No contradictions with rest of doc?")

    @computed_field
    @property
    def overall(self) -> float:
        return round(
            (self.completeness + self.clarity + self.ieee_compliance +
             self.testability + self.consistency) / 5,
            2
        )


# ── Per-question model ───────────────────────────────────────────────────────

class UpgradeQuestion(StrictBaseModel):
    question_id: str           # e.g. "q1", "q2"
    question: str              # human-readable question text
    dimension: str             # which score dimension this addresses
    answer: str = ""           # filled in by the user
    answered: bool = False


# ── Per-section upgrade record ───────────────────────────────────────────────

class SectionUpgradeRecord(ComputedModel):
    # Identity — always from original tree, immutable
    section_id: str
    heading: str
    level: int

    # Content snapshots
    original_content: str      # locked at session creation — never overwritten
    upgraded_content: str = "" # written by Upgrade Writer Agent
    user_edited_content: str = ""  # written by user if they edit the suggestion

    # Analysis
    score: SectionScore | None = None
    flags: list[str] = Field(default_factory=list)   # human-readable issue descriptions
    needs_upgrade: bool = False

    # Q&A
    questions: list[UpgradeQuestion] = Field(default_factory=list)

    # Lifecycle
    status: Literal[
        "pending",      # not yet analysed
        "kept",         # score above threshold — no upgrade needed
        "questioned",   # questions generated, waiting for user answers
        "answered",     # user answered all questions, ready for upgrade writer
        "upgraded",     # upgrade writer produced content, waiting for user review
        "accepted",     # user accepted upgraded_content
        "edited",       # user edited the suggestion → user_edited_content is used
        "rejected",     # user rejected — original_content will be used
    ] = "pending"

    @computed_field
    @property
    def final_content(self) -> str:
        """
        Single authoritative content for export.
        No if-else scattered around the codebase — always call this.
        """
        if self.status == "edited" and self.user_edited_content:
            return self.user_edited_content
        if self.status in ("accepted", "upgraded") and self.upgraded_content:
            return self.upgraded_content
        return self.original_content   # kept / rejected / pending → always original

    @computed_field
    @property
    def all_questions_answered(self) -> bool:
        return bool(self.questions) and all(q.answered for q in self.questions)

    @computed_field
    @property
    def score_overall(self) -> float | None:
        return self.score.overall if self.score else None


# ── Top-level session ────────────────────────────────────────────────────────

class UpgradeSession(ComputedModel):
    file_id: str
    user_id: str
    original_filename: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # The SCORE_THRESHOLD below which a section is flagged for upgrade
    score_threshold: float = 6.5

    sections: list[SectionUpgradeRecord] = Field(default_factory=list)

    # Overall pipeline status
    pipeline_status: Literal[
        "created",       # session created, analysis not yet run
        "analysing",     # analysis in progress
        "analysed",      # all sections scored
        "questioning",   # questions generated for flagged sections
        "ready",         # all flagged sections answered
        "upgrading",     # upgrade writer running
        "review",        # all upgrades ready for user review
        "complete",      # user finished accepting/rejecting
    ] = "created"

    @computed_field
    @property
    def sections_needing_upgrade(self) -> list[SectionUpgradeRecord]:
        return [s for s in self.sections if s.needs_upgrade]

    @computed_field
    @property
    def sections_pending_questions(self) -> list[SectionUpgradeRecord]:
        return [
            s for s in self.sections
            if s.needs_upgrade and s.status == "questioned" and not s.all_questions_answered
        ]

    @computed_field
    @property
    def sections_pending_review(self) -> list[SectionUpgradeRecord]:
        return [s for s in self.sections if s.status == "upgraded"]

    @computed_field
    @property
    def upgrade_summary(self) -> dict:
        total = len(self.sections)
        return {
            "total": total,
            "kept": sum(1 for s in self.sections if s.status == "kept"),
            "needs_upgrade": sum(1 for s in self.sections if s.needs_upgrade),
            "answered": sum(1 for s in self.sections if s.status == "answered"),
            "upgraded": sum(1 for s in self.sections if s.status == "upgraded"),
            "accepted": sum(1 for s in self.sections if s.status == "accepted"),
            "edited": sum(1 for s in self.sections if s.status == "edited"),
            "rejected": sum(1 for s in self.sections if s.status == "rejected"),
        }


# ── API response models ──────────────────────────────────────────────────────

class AnalyseResponse(StrictBaseModel):
    success: bool
    file_id: str
    sections_analysed: int
    sections_needing_upgrade: int
    session: UpgradeSession


class QuestionResponse(StrictBaseModel):
    success: bool
    file_id: str
    sections_with_questions: int
    session: UpgradeSession


class AnswerSubmission(StrictBaseModel):
    section_id: str
    answers: dict[str, str]   # question_id → answer text


class SessionStatusResponse(StrictBaseModel):
    file_id: str
    pipeline_status: str
    upgrade_summary: dict
    sections: list[SectionUpgradeRecord]