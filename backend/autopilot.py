import json
import uuid
from pathlib import Path
from typing import Any

from backend import db, engine
from backend.enrichment import coverage_for_text, enrich_missing_words
from backend.qwen_cloud import plan_autopilot_workflow
from backend.speech_service import generate_composite_speech

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "data" / "autopilot" / "runs"
ALLOWED_STEPS = {
    "import_sources",
    "check_coverage",
    "enrich_vocabulary",
    "generate_audio",
}


def _run_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def _audio_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.wav"


def _save(run: dict[str, Any]) -> dict[str, Any]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _run_path(run["id"]).write_text(json.dumps(run, indent=2), encoding="utf-8")
    return run


def get_run(run_id: str) -> dict[str, Any]:
    path = _run_path(run_id)
    if not path.exists():
        raise ValueError("Autopilot run not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_plan(raw: dict[str, Any], target_variants: int) -> dict[str, Any]:
    requested_steps = raw.get("steps", [])
    steps = [step for step in requested_steps if step in ALLOWED_STEPS]
    if "check_coverage" not in steps:
        steps.insert(0, "check_coverage")
    if "generate_audio" not in steps:
        steps.append("generate_audio")
    return {
        "summary": str(raw.get("summary") or "Prepare the shared corpus and generate composite speech."),
        "rationale": str(raw.get("rationale") or "Coverage is checked before external actions are approved."),
        "steps": list(dict.fromkeys(steps)),
        "target_variants": max(1, min(20, int(raw.get("target_variants", target_variants)))),
        "estimated_external_actions": max(0, int(raw.get("estimated_external_actions", 0))),
    }


def create_run(
    goal: str,
    target_text: str,
    source_urls: list[str],
    target_variants: int = 3,
) -> dict[str, Any]:
    clean_sources = list(dict.fromkeys(url.strip() for url in source_urls if url.strip()))
    coverage = coverage_for_text(target_text, target_variants)
    missing_variants = sum(row["needed"] for row in coverage["words"])
    raw_plan = plan_autopilot_workflow(
        goal=goal,
        target_text=target_text,
        source_urls=clean_sources,
        coverage=coverage,
        target_variants=target_variants,
    )
    plan = _normalize_plan(raw_plan, target_variants)
    plan["estimated_external_actions"] = max(
        plan["estimated_external_actions"], len(clean_sources) + missing_variants
    )

    run = {
        "id": uuid.uuid4().hex,
        "status": "awaiting_approval",
        "goal": goal,
        "target_text": target_text,
        "source_urls": clean_sources,
        "coverage_before": coverage,
        "plan": plan,
        "approval": None,
        "events": [
            {"type": "qwen_plan_created", "message": plan["summary"]},
            {
                "type": "human_checkpoint",
                "message": "Source imports and Qwen enrichment require approval before execution.",
            },
        ],
        "result": None,
        "error": None,
    }
    return _save(run)


def approve_run(
    run_id: str,
    allow_source_imports: bool,
    allow_cloud_enrichment: bool,
) -> dict[str, Any]:
    run = get_run(run_id)
    if run["status"] != "awaiting_approval":
        raise ValueError("Autopilot run is not awaiting approval")
    run["approval"] = {
        "allow_source_imports": allow_source_imports,
        "allow_cloud_enrichment": allow_cloud_enrichment,
    }
    run["status"] = "approved"
    run["events"].append(
        {
            "type": "human_approved",
            "message": (
                f"source_imports={allow_source_imports}, "
                f"cloud_enrichment={allow_cloud_enrichment}"
            ),
        }
    )
    return _save(run)


def execute_run(run_id: str) -> None:
    run = get_run(run_id)
    if run["status"] not in {"approved", "executing"}:
        raise ValueError("Autopilot run must be approved before execution")
    run["status"] = "executing"
    _save(run)

    imported_sources: list[dict[str, Any]] = []
    enrichment_result: dict[str, Any] | None = None
    try:
        approval = run["approval"] or {}
        if "import_sources" in run["plan"]["steps"] and approval.get("allow_source_imports"):
            for url in run["source_urls"]:
                path = engine.ingest_youtube(url)
                if not path:
                    imported_sources.append({"url": url, "status": "failed"})
                    continue
                source_id = db.create_source(url, "youtube", path, "processing")
                engine.process_audio_file(path, source_id)
                imported_sources.append(
                    {"url": url, "source_id": source_id, "status": "complete"}
                )
            run["events"].append(
                {
                    "type": "tool_completed",
                    "tool": "import_sources",
                    "message": f"Processed {len(imported_sources)} source request(s).",
                }
            )
            _save(run)

        coverage_after_import = coverage_for_text(
            run["target_text"], run["plan"]["target_variants"]
        )
        run["events"].append(
            {
                "type": "tool_completed",
                "tool": "check_coverage",
                "message": "Recalculated shared-corpus vocabulary coverage.",
            }
        )
        _save(run)

        if (
            "enrich_vocabulary" in run["plan"]["steps"]
            and approval.get("allow_cloud_enrichment")
            and not coverage_after_import["complete"]
        ):
            enrichment_result = enrich_missing_words(
                words=[row["word"] for row in coverage_after_import["words"]],
                target_variants=run["plan"]["target_variants"],
            )
            run["events"].append(
                {
                    "type": "tool_completed",
                    "tool": "qwen_enrichment",
                    "message": f"Created {len(enrichment_result['created'])} derived clips.",
                }
            )
            _save(run)

        coverage_final = coverage_for_text(
            run["target_text"], run["plan"]["target_variants"]
        )
        speech = generate_composite_speech(run["target_text"])
        audio_path = _audio_path(run_id)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(speech.audio_buffer.read())

        run["status"] = "complete"
        run["result"] = {
            "imported_sources": imported_sources,
            "enrichment": enrichment_result,
            "coverage_final": coverage_final,
            "audio_ready": True,
            "report": (
                f"Autopilot completed {len(run['plan']['steps'])} planned step(s), "
                f"processed {len(imported_sources)} source request(s), and produced composite audio."
            ),
        }
        run["events"].append(
            {
                "type": "workflow_complete",
                "message": run["result"]["report"],
            }
        )
        _save(run)
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
        run["events"].append({"type": "workflow_failed", "message": str(exc)})
        _save(run)


def audio_path_for_run(run_id: str) -> Path:
    run = get_run(run_id)
    path = _audio_path(run_id)
    if run["status"] != "complete" or not path.exists():
        raise ValueError("Autopilot audio is not ready")
    return path
