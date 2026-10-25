from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from app.schemas.analysis import AnalysisResponse, IntelligenceReport, VisualEvidence


def build_intelligence_report(data: dict[str, object], *, timestamp: datetime | None = None) -> IntelligenceReport:
    """Create a transparent, rule-based report wrapper around actual CV/model output."""
    semantic = data.get("semantic_analysis")
    semantic_data = semantic if isinstance(semantic, dict) else None
    analysis_id = str(data.get("analysis_id", ""))
    regions = data.get("regions") if isinstance(data.get("regions"), list) else []
    changed_percent = float(data.get("changed_percent", 0) or 0)
    largest_region_percent = max(
        (float(region.get("percent_of_valid_area", 0) or 0) for region in regions if isinstance(region, dict)),
        default=0.0,
    )

    if semantic_data:
        category = semantic_data["category"]
        source = "AI_VISION_MODEL"
        classification_explanation = (
            "Category is a cautious interpretation of the supplied imagery and CV candidate regions; "
            "it is not verified ground truth."
        )
        alternatives = [str(item) for item in semantic_data.get("alternative_explanations", [])]
        limitations = [str(item) for item in semantic_data.get("limitations", [])]
        limitations.extend(str(item) for item in semantic_data.get("unknowns", []))
        confidence_explanation = "No calibrated confidence score is provided by the model."
    else:
        category = "UNCERTAIN"
        source = "COMPUTER_VISION_HEURISTIC"
        classification_explanation = (
            "Semantic interpretation was unavailable; this report describes detected visual differences only. "
            "No event category is inferred from pixel changes."
        )
        alternatives = [
            "Seasonal or normal environmental variation",
            "Cloud, haze, shadow, or acquisition-condition differences",
            "Sensor, resolution, or residual image-alignment differences",
        ]
        limitations = [
            str(data.get("semantic_error") or "No AI provider was configured or semantic interpretation was not requested."),
            "Image differences alone do not establish a real-world event, cause, intent, legality, or responsibility.",
        ]
        confidence_explanation = "No confidence score is available for the computer-vision heuristic."

    if changed_percent < 0.1 and largest_region_percent < 0.1:
        severity = "LOW_VISUAL_EXTENT"
        severity_explanation = (
            f"Heuristic visual-extent rule: {changed_percent:.3f}% changed area and a largest region of "
            f"{largest_region_percent:.3f}% are both below 0.1%. "
            "This measures detected image extent only, not hazard or disaster severity."
        )
    elif changed_percent < 1.0 and largest_region_percent < 0.5:
        severity = "MODERATE_VISUAL_EXTENT"
        severity_explanation = (
            f"Heuristic visual-extent rule: changed area is {changed_percent:.3f}% and largest region is "
            f"{largest_region_percent:.3f}%; moderate applies when area is below 1% and the largest region is below 0.5%, "
            "or either measure exceeds the low threshold. "
            "This measures detected image extent only, not hazard or disaster severity."
        )
    else:
        severity = "HIGH_VISUAL_EXTENT"
        severity_explanation = (
            f"Heuristic visual-extent rule: changed area is {changed_percent:.3f}% (high at 1% or more) or largest "
            f"region is {largest_region_percent:.3f}% (high at 0.5% or more). "
            "A large visual difference does not establish a severe disaster or harmful event."
        )

    evidence = [
        VisualEvidence(kind="annotated_preview", label="Annotated comparison preview", reference="annotated_preview"),
        VisualEvidence(kind="difference_preview", label="Difference-map preview", reference="difference_preview"),
    ]
    for region in regions:
        if isinstance(region, dict) and region.get("region_id"):
            evidence.append(
                VisualEvidence(
                    kind="detected_region",
                    label=f"Detected region {region['region_id']}",
                    reference=f"regions[region_id={region['region_id']}]",
                )
            )

    return IntelligenceReport(
        analysis_timestamp=timestamp or datetime.now(timezone.utc),
        change_category=category,
        classification_source=source,
        classification_explanation=classification_explanation,
        confidence=None,
        confidence_explanation=confidence_explanation,
        severity=severity,
        severity_explanation=severity_explanation,
        supporting_visual_evidence=evidence,
        alternative_explanations=alternatives,
        limitations=limitations,
        recommended_verification_steps=[
            "Review the before and after images and the annotated candidate regions.",
            "Check source imagery, acquisition dates, sensor and processing metadata, and geometric alignment.",
            "Compare with additional dates or independent imagery and authoritative local records before acting.",
        ],
    )


def report_json(report: AnalysisResponse) -> str:
    return report.model_dump_json(indent=2)


def _markdown_escape(value: object) -> str:
    text = str(value)
    text = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|>])", r"\\\1", text)


def report_markdown(report: AnalysisResponse) -> str:
    data = report.model_dump(mode="json")
    summary = _markdown_escape(data.get("summary", ""))
    lines = [
        f"# OrbitalPulse Intelligence Report — {_markdown_escape(report.analysis_id)}",
        "",
        f"- **Analysis timestamp (UTC):** {_markdown_escape(report.report.analysis_timestamp.isoformat())}",
        f"- **Location:** {_markdown_escape(report.location or 'Not provided')}",
        f"- **Before date:** {_markdown_escape(report.before_acquisition_date or 'Not provided')}",
        f"- **After date:** {_markdown_escape(report.after_acquisition_date or 'Not provided')}",
        f"- **Changed area:** {report.changed_percent:.3f}% ({report.changed_pixels:,} / {report.total_pixels:,} valid pixels)",
        f"- **Comparison:** {_markdown_escape(report.comparison_mode)}; registration {_markdown_escape(report.registration_status)} ({_markdown_escape(report.registration_method)})",
        f"- **Detection method:** {_markdown_escape(report.detection_method)}",
        f"- **Category:** {_markdown_escape(report.report.change_category)}",
        f"- **Classification source:** {_markdown_escape(report.report.classification_source)}",
        f"- **Confidence:** Not available. {_markdown_escape(report.report.confidence_explanation)}",
        f"- **Heuristic severity:** {_markdown_escape(report.report.severity)} — {_markdown_escape(report.report.severity_explanation)}",
        "",
        "## Summary",
        "",
        summary,
        "",
        "## Detected regions",
        "",
        "| Region | Bounding box (x, y, width, height) | Pixel area | Valid area | Size |",
        "|---|---:|---:|---:|---|",
    ]
    for region in report.regions:
        lines.append(
            f"| {_markdown_escape(region.region_id)} | ({region.x}, {region.y}, {region.width}, {region.height}) | "
            f"{region.area:,} | {region.percent_of_valid_area:.4f}% | {_markdown_escape(region.size_category)} |"
        )
    if not report.regions:
        lines.append("| None detected | — | 0 | 0% | — |")
    lines.extend(["", f"Processing duration: {report.processing_duration_ms:.1f} ms. Warnings: {_markdown_escape('; '.join(report.warnings) or 'None')}"])

    lines.extend(["", "## Evidence references", ""])
    for item in report.report.supporting_visual_evidence:
        lines.append(f"- {_markdown_escape(item.label)} (`{_markdown_escape(item.reference)}`)")
    if report.annotated_preview.startswith("data:image/"):
        lines.extend(["", "### Annotated comparison", "", f"![Annotated comparison]({report.annotated_preview})"])
    if report.difference_preview.startswith("data:image/"):
        lines.extend(["", "### Difference map", "", f"![Difference map]({report.difference_preview})"])

    _append_list(lines, "Alternative explanations", report.report.alternative_explanations)
    _append_list(lines, "Limitations and uncertainty", report.report.limitations)
    _append_list(lines, "Recommended verification steps", report.report.recommended_verification_steps)
    return "\n".join(lines) + "\n"


def _append_list(lines: list[str], title: str, values: list[str]) -> None:
    lines.extend(["", f"## {title}", ""])
    lines.extend(f"- {_markdown_escape(value)}" for value in values)
    if not values:
        lines.append("- None provided.")


def report_html(report: AnalysisResponse) -> str:
    """Render a standalone HTML document; every model/user-provided value is escaped."""
    esc = lambda value: html.escape(str(value), quote=True)
    evidence = "".join(f"<li>{esc(item.label)} <code>{esc(item.reference)}</code></li>" for item in report.report.supporting_visual_evidence)
    regions = "".join(
        f"<tr><td>{esc(region.region_id)}</td><td>({region.x}, {region.y}, {region.width}, {region.height})</td>"
        f"<td>{region.area:,}</td><td>{region.percent_of_valid_area:.4f}%</td><td>{esc(region.size_category)}</td></tr>"
        for region in report.regions
    ) or "<tr><td colspan='5'>No regions detected</td></tr>"

    def list_html(values: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"

    images = ""
    if report.annotated_preview.startswith("data:image/"):
        images += f"<h2>Annotated comparison</h2><img alt='Annotated comparison' src='{esc(report.annotated_preview)}'>"
    if report.difference_preview.startswith("data:image/"):
        images += f"<h2>Difference map</h2><img alt='Difference map' src='{esc(report.difference_preview)}'>"
    confidence = report.report.confidence
    confidence_text = "Not available" if confidence is None else f"{confidence:.3f}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OrbitalPulse report {esc(report.analysis_id)}</title><style>
body{{font:16px/1.55 system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#172033}}h1,h2{{color:#123}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd2dd;padding:.5rem;text-align:left}}img{{max-width:100%;height:auto;border:1px solid #ccd2dd;border-radius:8px}}.severity{{padding:1rem;background:#f1f4f9}}
</style></head><body><h1>OrbitalPulse Intelligence Report</h1>
<dl><dt>Analysis ID</dt><dd>{esc(report.analysis_id)}</dd><dt>Timestamp (UTC)</dt><dd>{esc(report.report.analysis_timestamp.isoformat())}</dd>
<dt>Location</dt><dd>{esc(report.location or 'Not provided')}</dd><dt>Before / after acquisition</dt><dd>{esc(report.before_acquisition_date or 'Not provided')} / {esc(report.after_acquisition_date or 'Not provided')}</dd>
<dt>Category</dt><dd>{esc(report.report.change_category)}</dd><dt>Classification source</dt><dd>{esc(report.report.classification_source)}</dd><dt>Confidence</dt><dd>{confidence_text}. {esc(report.report.confidence_explanation)}</dd>
<dt>Changed area</dt><dd>{report.changed_percent:.3f}% ({report.changed_pixels:,} of {report.total_pixels:,} valid pixels)</dd><dt>Comparison / registration</dt><dd>{esc(report.comparison_mode)} / {esc(report.registration_status)} ({esc(report.registration_method)})</dd><dt>Detection method</dt><dd>{esc(report.detection_method)}</dd></dl>
<p class="severity"><strong>Heuristic severity: {esc(report.report.severity)}</strong><br>{esc(report.report.severity_explanation)}</p>
<h2>Summary</h2><p>{esc(report.summary)}</p><p>Processing: {report.processing_duration_ms:.1f} ms. Warnings: {esc('; '.join(report.warnings) or 'None')}</p><h2>Detected regions</h2><table><thead><tr><th>Region</th><th>Bounding box</th><th>Pixel area</th><th>Valid area</th><th>Size</th></tr></thead><tbody>{regions}</tbody></table>
<h2>Supporting visual evidence</h2><ul>{evidence}</ul>{images}<h2>Alternative explanations</h2>{list_html(report.report.alternative_explanations)}
<h2>Limitations and uncertainty</h2>{list_html(report.report.limitations)}<h2>Recommended verification steps</h2>{list_html(report.report.recommended_verification_steps)}
</body></html>"""
