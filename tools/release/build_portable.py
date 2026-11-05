#!/usr/bin/env python3
"""Package the SAME City on Paper site locally, without GitHub Actions or Node.

Usage (from repo root):
    python3 tools/release/build_portable.py --out dist/city-on-paper --zip
The builder uses the same source curators and data as the GitHub release pipeline.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATIC_DIRS = (
    "poc/compare", "docs/ux/mockups", "world", "salon", "photography",
    "closeup", "exhibitions/city-as-evidence", "discover", "journeys",
    "detective", "fieldwork", "printlab", "ideas", "studio", "ornaments",
    "atelier/bargue", "atelier/ornament",
)
STATIC_FILES = (
    "index.html",
    "data/ideas/radar-20261103.json",
    "data/curation/world-cities-v1.json",
    "data/curation/close-reading-20261103.json",
    "data/curation/close-reading-benoist-20261103.json",
    "data/curation/era-journeys-20261102.json",
    "data/research/benoist-production-network-v1.json",
    "data/stories/madeleine-dossier-20261103.json",
    "data/catalog/ornament-workshop-2026-11-02.json",
    "data/catalog/bargue-academy-2026-11-02.json",
    "data/catalog/ledger-2026-11-01.csv",
    "data/candidates/candidates-2026-11-01b.json",
)
CONSILIUM = (
    "docs/consilium/MASTER_DIRECTION_20261103.md",
    "docs/consilium/BEFORE_RELEASE.md",
    "docs/consilium/AFTER_RELEASE.md",
    "docs/consilium/WORLD_EXPANSION_CONSILIUM_20261104.md",
)


def copy_sources(out: Path) -> None:
    if out.resolve() == ROOT:
        raise ValueError("Output directory may not be the repository root")
    out.mkdir(parents=True, exist_ok=True)
    for rel in STATIC_DIRS:
        source = ROOT / rel
        if not source.is_dir():
            raise FileNotFoundError(source)
        shutil.copytree(source, out / rel, dirs_exist_ok=True)
    for rel in (*STATIC_FILES, *CONSILIUM):
        source = ROOT / rel
        if not source.is_file():
            raise FileNotFoundError(source)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(ROOT / "tools/release/serve_local.py", out / "serve_local.py")
    shutil.copy2(ROOT / "docs/PORTABLE_SITE_HANDOFF.md", out / "PROJECT_HANDOFF.md")
    (out / "README_RUN.txt").write_text(
        "CITY ON PAPER | ГОРОД НА БУМАГЕ\n\n"
        "Откройте в распакованной папке терминал и выполните:\n"
        "Mac/Linux: python3 serve_local.py\n"
        "Windows: py -3 serve_local.py\n"
        "В браузере откроется http://127.0.0.1:8765/\n"
        "Для iPad/iPhone в доверенном домашнем Wi-Fi: python3 serve_local.py --lan\n"
        "Используйте адрес для iPad, который появится в терминале.\n"
        "Режим --lan без пароля: не использовать на общественном Wi-Fi.\n"
        "Для полной международной коллекции требуется интернет.\n"
        "Историческая Site v7 не импортирована автоматически.\n",
        encoding="utf-8",
    )
    (out / "VERSION.json").write_text(
        json.dumps({
            "product": "City on Paper", "packaged": str(date.today()),
            "source": "zukevich-blip/-city-on-paper",
            "branch": "release/city-on-paper-private-preview-20261104",
            "notes": "Local portable build, no independently confirmed exact THEN/NOW matching",
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_catalogues(out: Path, world_budget: int) -> dict:
    # The tools' source catalogues are not rewritten in the repo.
    from tools.curation.build_modern_city_photos import build as photos
    from tools.curation.build_open_art_cache import build as base_cache
    from tools.curation.build_world_graphics import build as world
    from tools.curation.expand_open_archives import build as expanded

    base = base_cache(out, workers=8)
    print("Проверенный базовый фонд:", base["cached"], "копий CC0", flush=True)
    archive = expanded(out, cma=220, aic=110, met=60, cache_limit=180)
    print("Музейный архив:", archive["total"], "записей", flush=True)
    modern = photos(out)
    print("Современные фотографии:", modern["visible_images"], "записей", flush=True)
    geographic = world(
        ROOT / "data/curation/world-cities-v1.json", out,
        per_city=9, budget=world_budget, max_seconds=480,
    )
    print("Города мира:", geographic["item_count"], "листов", flush=True)
    return {"base": base, "archive": archive, "modern": modern, "world": geographic}


def make_zip(out: Path) -> Path:
    archive_path = out.parent / "City-on-Paper-Portable.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as zf:
        for file in sorted(out.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(out))
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist/city-on-paper")
    parser.add_argument("--city-budget", type=int, default=150)
    parser.add_argument("--zip", action="store_true", help="Also create one downloadable ZIP")
    parser.add_argument("--skip-network", action="store_true", help="Only copy source files (incomplete preview)")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out == ROOT:
        parser.error("Output directory must be a separate subfolder of this source repository")
    copy_sources(out)
    if args.skip_network:
        print("ATTENTION: only source shell copied; worldwide manifests are NOT built")
        return
    try:
        summary = build_catalogues(out, args.city_budget)
    except Exception as exc:
        print("Ошибка источника:", exc, file=sys.stderr)
        raise SystemExit(2) from exc

    if summary["world"]["item_count"] < 20:
        raise SystemExit("Мировой архив слишком мал. Проверьте интернет и лимиты API.")

    command = [sys.executable, str(ROOT / "tools/release/validate_bundle.py"), "--root", str(out)]
    result = subprocess.run(command, check=False, cwd=ROOT)
    if result.returncode:
        raise SystemExit("Архив собран, но не прошёл верификацию. Данные сохранены для анализа.")
    if args.zip:
        path = make_zip(out)
        print("Готовый ZIP:", path, "байт:", path.stat().st_size)
    print("Готово. Откройте папку и запустите: python3 serve_local.py")


if __name__ == "__main__":
    main()
