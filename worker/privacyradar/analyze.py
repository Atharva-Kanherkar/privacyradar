from __future__ import annotations

from openai import OpenAI

from privacyradar.schema import MaterialityJudgement, PracticeDocument
from privacyradar.settings import settings

EXTRACT_INSTRUCTIONS = """
You extract structured data practices from a privacy policy.
Only use facts present in the text. Every practice needs a verbatim quote.
If a field is not stated, use unspecified / empty lists. Do not invent vendors.
""".strip()

MATERIALITY_INSTRUCTIONS = """
You compare two versions of a privacy policy (or the changed sections).
Cosmetic = date stamps, typo fixes, nav/footer, formatting, equivalent rephrasing.
Material = new/removed data types, new sharing, longer retention, weaker user control.
Headline must be one sentence a non-lawyer understands. Empty headline if cosmetic.
Quotes must be verbatim from the NEW text.
""".strip()


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key)


def extract_practices(company: str, markdown: str) -> tuple[PracticeDocument, str]:
    client = _client()
    model = settings.openai_extract_model
    parsed = client.responses.parse(
        model=model,
        instructions=EXTRACT_INSTRUCTIONS,
        input=f"Company: {company}\n\nPolicy:\n{markdown[:120_000]}",
        text_format=PracticeDocument,
    )
    if parsed.output_parsed is None:
        raise RuntimeError("OpenAI returned no parsed PracticeDocument")
    return parsed.output_parsed, model


def judge_materiality(
    company: str,
    old_markdown: str,
    new_markdown: str,
    changed: list[str],
) -> tuple[MaterialityJudgement, str]:
    client = _client()
    model = settings.openai_extract_model
    parsed = client.responses.parse(
        model=model,
        instructions=MATERIALITY_INSTRUCTIONS,
        input=(
            f"Company: {company}\n"
            f"Changed sections: {', '.join(changed) or '(whole document)'}\n\n"
            f"--- OLD ---\n{old_markdown[:40_000]}\n\n"
            f"--- NEW ---\n{new_markdown[:40_000]}"
        ),
        text_format=MaterialityJudgement,
    )
    if parsed.output_parsed is None:
        raise RuntimeError("OpenAI returned no parsed MaterialityJudgement")
    return parsed.output_parsed, model
