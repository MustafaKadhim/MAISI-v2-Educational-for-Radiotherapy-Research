#!/usr/bin/env python
"""generate.py — One-command synthetic medical image generation with NVIDIA MAISI.

Run without arguments for an interactive menu, or pass --preset to skip it.

Examples
--------
  python generate.py                            # interactive menu
  python generate.py --list                     # show all available presets
  python generate.py --preset ct_lungs_tumor    # CT chest with lung tumor mask
  python generate.py --preset brain_t1          # T1-weighted brain MRI
  python generate.py --preset brain_t1 --seed 9999 --gpu 0
  python generate.py --preset ct_abdomen_organs --dry-run   # write YAML only, skip GPU
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).parent.resolve()
CONFIGS_DIR = REPO_ROOT / "configs" / "maisi2"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

@dataclass
class Preset:
    label: str                          # shown in the menu
    category: str                       # group heading
    kind: str                           # "ct_paired" | "mr_brain" | "mr_body"
    # CT-specific
    body_region: list[str] = field(default_factory=list)
    anatomy_list: list[str] = field(default_factory=list)
    # MRI-specific
    modality: Optional[str] = None
    modalities: Optional[list[str]] = None
    # Geometry (shared)
    output_size: list[int] = field(default_factory=lambda: [256, 256, 128])
    spacing: list[float] = field(default_factory=lambda: [1.5, 1.5, 2.0])
    # Model
    model_variant: str = "rflow-ct"
    num_inference_steps: int = 30
    cfg_guidance_scale: float = 0.0


# Ordered so the menu is grouped and sequenced nicely.
_PRESET_ORDER: list[tuple[str, Preset]] = [

    # ── CT with segmentation masks ──────────────────────────────────────────
    ("ct_lungs_tumor", Preset(
        label="Chest  — all lung lobes + lung tumor + heart + trachea",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["chest"],
        anatomy_list=[
            "lung tumor",
            "left lung upper lobe", "left lung lower lobe",
            "right lung upper lobe", "right lung middle lobe", "right lung lower lobe",
            "trachea", "heart",
        ],
        output_size=[256, 256, 128],
        spacing=[1.5, 1.5, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_abdomen_organs", Preset(
        label="Abdomen — liver, spleen, pancreas, kidneys, aorta, gallbladder, stomach",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["abdomen"],
        anatomy_list=[
            "liver", "spleen", "pancreas",
            "right kidney", "left kidney",
            "aorta", "inferior vena cava",
            "gallbladder", "stomach", "esophagus", "duodenum",
        ],
        output_size=[256, 256, 128],
        spacing=[1.5, 1.5, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_abdomen_tumor", Preset(
        label="Abdomen — organs (above) + hepatic tumor + pancreatic tumor",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["abdomen"],
        anatomy_list=[
            "liver", "spleen", "pancreas",
            "right kidney", "left kidney",
            "aorta", "gallbladder", "stomach",
            "hepatic tumor", "pancreatic tumor",
        ],
        output_size=[256, 256, 128],
        spacing=[1.5, 1.5, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_head_neck", Preset(
        label="Head & Neck — brain, skull, spinal cord, carotid arteries, thyroid, trachea",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["head"],
        anatomy_list=[
            "brain", "skull", "spinal cord",
            "left common carotid artery", "right common carotid artery",
            "thyroid gland", "trachea", "esophagus",
        ],
        output_size=[256, 256, 128],
        spacing=[1.0, 1.0, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_pelvis_rt", Preset(
        label="Pelvis RT — bladder, prostate, femur, hip bones, sacrum",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["pelvis"],
        anatomy_list=[
            "bladder", "prostate",
            "left femur", "right femur",
            "left hip", "right hip",
            "sacrum", "colon",
        ],
        output_size=[256, 256, 128],
        spacing=[1.5, 1.5, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_chest_cardio", Preset(
        label="Chest cardiovascular — heart, aorta, great vessels, lungs, airway",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["chest"],
        anatomy_list=[
            "heart", "aorta", "pulmonary vein", "superior vena cava",
            "left lung upper lobe", "left lung lower lobe",
            "right lung upper lobe", "right lung middle lobe", "right lung lower lobe",
            "trachea", "airway",
        ],
        output_size=[256, 256, 128],
        spacing=[1.5, 1.5, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),
    ("ct_spine", Preset(
        label="Spine — spinal cord + full vertebral column C1–L5 + sacrum",
        category="CT with segmentation masks",
        kind="ct_paired",
        body_region=["head", "chest", "abdomen"],
        anatomy_list=[
            "spinal cord",
            "vertebrae C1", "vertebrae C2", "vertebrae C3", "vertebrae C4",
            "vertebrae C5", "vertebrae C6", "vertebrae C7",
            "vertebrae T1", "vertebrae T2", "vertebrae T3", "vertebrae T4",
            "vertebrae T5", "vertebrae T6", "vertebrae T7", "vertebrae T8",
            "vertebrae T9", "vertebrae T10", "vertebrae T11", "vertebrae T12",
            "vertebrae L1", "vertebrae L2", "vertebrae L3", "vertebrae L4",
            "vertebrae L5", "vertebrae S1",
        ],
        output_size=[256, 256, 384],
        spacing=[1.0, 1.0, 2.0],
        model_variant="rflow-ct",
        cfg_guidance_scale=0,
    )),

    # ── Brain MRI ────────────────────────────────────────────────────────────
    ("brain_t1", Preset(
        label="Brain MRI — T1-weighted whole brain",
        category="Brain MRI",
        kind="mr_brain",
        modality="mri_t1",
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),
    ("brain_t2", Preset(
        label="Brain MRI — T2-weighted whole brain",
        category="Brain MRI",
        kind="mr_brain",
        modality="mri_t2",
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),
    ("brain_flair", Preset(
        label="Brain MRI — FLAIR whole brain  (fluid suppression, lesion detection)",
        category="Brain MRI",
        kind="mr_brain",
        modality="mri_flair",
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),
    ("brain_swi", Preset(
        label="Brain MRI — SWI whole brain  (susceptibility weighted imaging)",
        category="Brain MRI",
        kind="mr_brain",
        modality="mri_swi",
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),
    ("brain_t1_stripped", Preset(
        label="Brain MRI — T1 skull-stripped  (brain tissue only, no skull)",
        category="Brain MRI",
        kind="mr_brain",
        modality="mri_t1_skull_stripped",
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),
    ("brain_all", Preset(
        label="Brain MRI — All contrasts  (T1, T2, FLAIR, SWI + skull-stripped = 8 volumes)",
        category="Brain MRI",
        kind="mr_brain",
        modalities=[
            "mri_t1", "mri_t2", "mri_flair", "mri_swi",
            "mri_t1_skull_stripped", "mri_t2_skull_stripped",
            "mri_flair_skull_stripped", "mri_swi_skull_stripped",
        ],
        output_size=[256, 256, 256],
        spacing=[1.0, 1.0, 1.0],
        model_variant="rflow-mr-brain",
        cfg_guidance_scale=10,
    )),

    # ── Body MRI ─────────────────────────────────────────────────────────────
    ("mr_prostate_t2", Preset(
        label="Body MRI — Prostate T2  (high-resolution pelvic MRI)",
        category="Body MRI",
        kind="mr_body",
        modality="mri_t2",
        output_size=[256, 256, 128],
        spacing=[0.66, 0.66, 0.70],
        model_variant="rflow-mr",
        cfg_guidance_scale=15,
    )),
    ("mr_breast_t1", Preset(
        label="Body MRI — Breast T1  (bilateral breast MRI)",
        category="Body MRI",
        kind="mr_body",
        modality="mri_t1",
        output_size=[256, 256, 128],
        spacing=[0.68, 0.78, 1.56],
        model_variant="rflow-mr",
        cfg_guidance_scale=15,
    )),
    ("mr_abdomen_t1", Preset(
        label="Body MRI — Abdomen T1  (upper abdominal MRI)",
        category="Body MRI",
        kind="mr_body",
        modality="mri_t1",
        output_size=[256, 256, 128],
        spacing=[1.48, 1.21, 2.25],
        model_variant="rflow-mr",
        cfg_guidance_scale=15,
    )),
]

PRESETS: dict[str, Preset] = dict(_PRESET_ORDER)


# ---------------------------------------------------------------------------
# YAML config builders
# ---------------------------------------------------------------------------

def _build_ct_yaml(key: str, preset: Preset, seed: int, gpu: int) -> dict:
    return {
        "ct_structures": {
            "repo_path": "external/NV-Generate-CTMR",
            "model_variant": preset.model_variant,
            "network": "rflow",
            "output_dir": f"outputs/quickgen_{key}",
            "gpu_index": gpu,
            "seeds": [seed],
            "num_output_samples": 1,
            "output_size": preset.output_size,
            "spacing": preset.spacing,
            "body_region": preset.body_region,
            "anatomy_list": preset.anatomy_list,
            "controllable_anatomy_size": [],
            "modality": 1,
            "num_inference_steps": preset.num_inference_steps,
            "mask_generation_num_inference_steps": 1000,
            "cfg_guidance_scale": int(preset.cfg_guidance_scale),
            "autoencoder_sliding_window_infer_size": [48, 48, 48],
            "autoencoder_sliding_window_infer_overlap": 0.6666,
            "download_models": False,
        },
        "ct_visuals": {
            "output_subdir": "visuals",
            "planes": ["axial", "coronal", "sagittal"],
            "random_grid": True,
            "random_slices": 16,
            "orthogonal_panel": True,
            "plane_sweeps": True,
            "overlay_structures": True,
            "overview_contact_sheet": True,
        },
    }


def _build_mr_yaml(key: str, preset: Preset, seed: int, gpu: int) -> dict:
    nvidia: dict = {
        "repo_path": "external/NV-Generate-CTMR",
        "model_variant": preset.model_variant,
        "network": "rflow",
        "output_dir": f"outputs/quickgen_{key}",
        "output_size": preset.output_size,
        "spacing": preset.spacing,
        "seeds": [seed],
        "gpu_index": gpu,
        "num_inference_steps": preset.num_inference_steps,
        "cfg_guidance_scale": preset.cfg_guidance_scale,
        "intensity_mode": "mr",
        "download_models": False,
    }
    if preset.modalities:
        nvidia["modalities"] = preset.modalities
        nvidia["output_prefix"] = f"{preset.model_variant}_{{modality}}"
    else:
        nvidia["modality"] = preset.modality
        nvidia["output_prefix"] = f"{preset.model_variant}_{preset.modality}"
    return {
        "nvidia": nvidia,
        "sample_visuals": {
            "output_subdir": "visuals",
            "planes": ["axial", "coronal", "sagittal"],
            "random_grid": True,
            "random_slices": 16,
            "orthogonal_panel": True,
            "plane_sweeps": True,
            "overview_contact_sheet": True,
        },
    }


def write_config(key: str, preset: Preset, seed: int, gpu: int) -> tuple[Path, Path]:
    """Write the YAML config for this preset and return (yaml_path, script_path)."""
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    yaml_path = CONFIGS_DIR / f"quickgen_{key}.yaml"

    if preset.kind == "ct_paired":
        data = _build_ct_yaml(key, preset, seed, gpu)
        script = SCRIPTS_DIR / "run_nvidia_ct_structures_from_config.py"
    else:
        data = _build_mr_yaml(key, preset, seed, gpu)
        script = SCRIPTS_DIR / "run_nvidia_case_from_config.py"

    with open(yaml_path, "w") as f:
        f.write(f"# Auto-generated by generate.py  —  preset: {key}\n")
        f.write(f"# {preset.label}\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return yaml_path, script


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _hr(char: str = "─", width: int = 62) -> str:
    return char * width


def print_banner() -> None:
    print()
    print(_hr("═"))
    print("  MAISI-RT Sandbox  —  Quick Generate")
    print("  Synthetic CT / MRI with NVIDIA MAISI v2")
    print(_hr("═"))
    print()


def print_menu() -> list[str]:
    """Print the grouped interactive menu. Returns ordered list of preset keys."""
    keys: list[str] = []
    current_cat = ""
    n = 0
    for key, preset in _PRESET_ORDER:
        if preset.category != current_cat:
            if current_cat:
                print()
            current_cat = preset.category
            print(f"  {current_cat}")
            print(f"  {_hr('-', 56)}")
        n += 1
        keys.append(key)
        print(f"  [{n:2d}]  {preset.label}")
    print()
    return keys


def print_preset_list() -> None:
    """Print all presets with their --preset keys (for --list mode)."""
    print_banner()
    current_cat = ""
    for key, preset in _PRESET_ORDER:
        if preset.category != current_cat:
            current_cat = preset.category
            print(f"\n  {current_cat}")
            print(f"  {_hr()}")
        print(f"  {key:<24}  {preset.label}")
    print()


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def generate(key: str, preset: Preset, seed: int, gpu: int, dry_run: bool) -> None:
    yaml_path, script = write_config(key, preset, seed, gpu)
    out_dir = REPO_ROOT / "outputs" / f"quickgen_{key}"

    print()
    print(_hr())
    print(f"  Preset    : {key}")
    print(f"  Generates : {preset.label}")
    print(f"  Seed      : {seed}")
    print(f"  GPU index : {gpu}")
    print(f"  Config    : {yaml_path.relative_to(REPO_ROOT)}")
    print(f"  Output    : outputs/quickgen_{key}/")
    print(_hr())

    if dry_run:
        print()
        print("  [dry-run]  Config written. GPU generation skipped.")
        print()
        print("  To run manually after reviewing the config:")
        print(f"    python {script.relative_to(REPO_ROOT)} \\")
        print(f"           --config {yaml_path.relative_to(REPO_ROOT)}")
        print()
        return

    print()
    print("  Starting generation — this takes a few minutes on GPU.")
    print("  You will see NVIDIA's progress output below.")
    print()

    result = subprocess.run(
        [sys.executable, str(script), "--config", str(yaml_path)],
        cwd=REPO_ROOT,
    )

    if result.returncode != 0:
        print()
        print("  ERROR: Generation failed. See the output above for details.")
        print(f"  Logs are also saved in: outputs/quickgen_{key}/visuals/")
        sys.exit(1)

    vis_dir = out_dir / "visuals" / f"sample_001_seed{seed}"
    print()
    print(_hr("═"))
    print("  Generation complete!")
    print()
    if preset.kind == "ct_paired":
        print("  Your files:")
        print(f"    {vis_dir.relative_to(REPO_ROOT)}/")
        print(f"      ct_seed{seed}_image.nii.gz          ← CT volume (HU values)")
        print(f"      ct_seed{seed}_label.nii.gz          ← structure masks (integer labels)")
        print(f"      ct_orthogonal_panel.png              ← 3-plane PNG")
        print(f"      ct_structure_overlay_axial_4x4.png  ← mask overlay grid")
    else:
        print("  Your files:")
        print(f"    outputs/quickgen_{key}/*.nii.gz   ← generated MRI volume(s)")
        print(f"    outputs/quickgen_{key}/visuals/   ← PNG galleries")
    print()
    print("  Open in 3D Slicer:  File → Add Data → select the .nii.gz")
    print(_hr("═"))
    print()


# ---------------------------------------------------------------------------
# Interactive prompt helpers
# ---------------------------------------------------------------------------

def _ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    return value if value else (default or "")


def interactive_mode() -> tuple[str, Preset, int, int]:
    print_banner()

    print("  What would you like to generate?\n")
    keys = print_menu()

    n = len(keys)
    while True:
        raw = _ask(f"Enter a number (1–{n}), or q to quit")
        if raw.lower() in ("q", "quit", "exit"):
            sys.exit(0)
        try:
            idx = int(raw) - 1
            if 0 <= idx < n:
                break
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {n}.")

    key = keys[idx]
    preset = PRESETS[key]
    print(f"\n  You chose: {preset.label}\n")

    # Seed
    seed_raw = _ask("Random seed (press Enter for a random seed)", default="random")
    if seed_raw in ("random", ""):
        seed = random.randint(10_000, 99_999)
        print(f"  Using seed: {seed}")
    else:
        try:
            seed = int(seed_raw)
        except ValueError:
            seed = random.randint(10_000, 99_999)
            print(f"  Invalid — using random seed: {seed}")

    # GPU
    gpu_raw = _ask("GPU index", default="1")
    try:
        gpu = int(gpu_raw)
    except ValueError:
        gpu = 1

    return key, preset, seed, gpu


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--preset", metavar="NAME",
        help="Preset name to generate (use --list to see all options)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all available presets with their --preset key and exit",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility (default: random)",
    )
    parser.add_argument(
        "--gpu", type=int, default=1,
        help="GPU device index to use (default: 1)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Write the YAML config and print the command, but do not run generation",
    )
    args = parser.parse_args()

    if args.list:
        print_preset_list()
        return

    if args.preset:
        if args.preset not in PRESETS:
            print(f"\n  Unknown preset: {args.preset!r}")
            print(f"  Run  python generate.py --list  to see all options.\n")
            sys.exit(1)
        key = args.preset
        preset = PRESETS[key]
        seed = args.seed if args.seed is not None else random.randint(10_000, 99_999)
        gpu = args.gpu
        print_banner()
    else:
        key, preset, seed, gpu = interactive_mode()

    generate(key, preset, seed, gpu, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
