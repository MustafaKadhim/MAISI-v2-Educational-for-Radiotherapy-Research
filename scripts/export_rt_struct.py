#!/usr/bin/env python3
"""
Export a MAISI NIfTI CT + label pair → DICOM CT series + DICOM RT-STRUCT.

The RT-STRUCT file (.dcm) can be imported directly into:
  - 3D Slicer (free, immediate — recommended for verification)
  - Eclipse, RayStation, Monaco (standard DICOM import)

Usage
-----
  # Auto-discover CT + label from a sample directory
  python scripts/export_rt_struct.py --pair outputs/maisi2_showcase_ct_pelvis_rt/visuals/sample_001_seed73001/

  # Explicit paths
  python scripts/export_rt_struct.py \\
      --ct  outputs/.../ct_seed73001_image.nii.gz \\
      --label outputs/.../ct_seed73001_label.nii.gz

  # Use a preset name to find the latest output automatically
  python scripts/export_rt_struct.py --preset ct_pelvis_rt

  # List all exportable outputs
  python scripts/export_rt_struct.py --list

Output
------
  outputs/dicom_export/<preset>_seed<N>/
    CT/          one .dcm per axial slice (reference image series)
    RT/
      RS_<name>.dcm    DICOM RT-STRUCT
    manifest.json      exported structures with volumes, labels, QUANTEC notes
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Clinical colour palette — matches common TPS conventions
# ---------------------------------------------------------------------------

_COLORS: dict[str, list[int]] = {
    # GTV / tumour
    "lung tumor": [255, 0, 0],
    "hepatic tumor": [255, 0, 0],
    "pancreatic tumor": [255, 30, 30],
    "colon cancer primaries": [200, 0, 0],
    "bone lesion": [180, 0, 0],
    # Spinal cord / brainstem — critical OARs
    "spinal cord": [255, 255, 0],
    "brain": [180, 180, 180],
    "brainstem": [255, 165, 0],
    # Lung
    "left lung upper lobe": [0, 220, 220],
    "left lung lower lobe": [0, 200, 200],
    "right lung upper lobe": [0, 180, 200],
    "right lung middle lobe": [0, 160, 180],
    "right lung lower lobe": [0, 140, 160],
    "airway": [0, 230, 180],
    "trachea": [0, 200, 150],
    # Cardiac
    "heart": [220, 20, 60],
    "aorta": [139, 0, 0],
    "inferior vena cava": [0, 0, 180],
    "superior vena cava": [0, 0, 160],
    "portal vein and splenic vein": [0, 0, 140],
    "pulmonary vein": [100, 0, 180],
    # Abdomen
    "liver": [139, 90, 43],
    "spleen": [128, 0, 128],
    "pancreas": [255, 200, 100],
    "gallbladder": [0, 180, 80],
    "stomach": [255, 140, 0],
    "duodenum": [255, 160, 50],
    "esophagus": [255, 165, 80],
    "small bowel": [180, 120, 60],
    "colon": [200, 100, 50],
    # Kidneys / adrenals
    "left kidney": [205, 92, 92],
    "right kidney": [195, 80, 80],
    "left adrenal gland": [100, 180, 100],
    "right adrenal gland": [90, 170, 90],
    "left kidney cyst": [220, 110, 110],
    "right kidney cyst": [210, 100, 100],
    # Pelvis
    "bladder": [173, 216, 230],
    "prostate": [0, 80, 255],
    "rectum": [255, 100, 50],
    # Bones / muscles
    "skull": [245, 222, 179],
    "sacrum": [240, 215, 170],
    "sternum": [230, 205, 160],
    "left femur": [147, 112, 219],
    "right femur": [130, 95, 210],
    "left hip": [160, 120, 230],
    "right hip": [150, 110, 220],
    "costal cartilages": [200, 195, 150],
    # Head & neck
    "thyroid gland": [50, 205, 50],
    "left common carotid artery": [180, 0, 0],
    "right common carotid artery": [160, 0, 0],
}

_FALLBACK_COLORS = [
    [0, 128, 255], [0, 255, 128], [255, 0, 128], [128, 255, 0],
    [255, 128, 0], [128, 0, 255], [0, 200, 200], [200, 0, 200],
    [100, 200, 100], [200, 100, 100],
]

# ---------------------------------------------------------------------------
# Brief QUANTEC/TG-101 dose constraint notes for educational manifest
# ---------------------------------------------------------------------------

_QUANTEC: dict[str, str] = {
    "spinal cord": "Dmax < 45 Gy (QUANTEC); < 54 Gy point",
    "brainstem": "Dmax < 54 Gy (QUANTEC)",
    "brain": "V60 < 3%, mean < 45 Gy (whole brain)",
    "heart": "Mean < 26 Gy (QUANTEC lung RT); V25 < 10%",
    "left lung upper lobe": "See lung: mean < 20 Gy, V20 < 30–35%",
    "left lung lower lobe": "See lung: mean < 20 Gy, V20 < 30–35%",
    "right lung upper lobe": "See lung: mean < 20 Gy, V20 < 30–35%",
    "right lung middle lobe": "See lung: mean < 20 Gy, V20 < 30–35%",
    "right lung lower lobe": "See lung: mean < 20 Gy, V20 < 30–35%",
    "esophagus": "Mean < 34 Gy (QUANTEC); V35 < 50%",
    "liver": "Mean < 28–32 Gy (QUANTEC); V30 < 30%",
    "left kidney": "Mean < 15–18 Gy (QUANTEC; bilateral)",
    "right kidney": "Mean < 15–18 Gy (QUANTEC; bilateral)",
    "bladder": "V80 < 15%, V65 < 25%, V40 < 50% (QUANTEC SBRT)",
    "rectum": "V60 < 50%, V70 < 20%, V75 < 15% (prostate RT)",
    "prostate": "Target — dose depends on fractionation scheme",
    "thyroid gland": "Mean < 45 Gy to avoid hypothyroidism",
    "aorta": "No QUANTEC limit; avoid high point dose",
    "trachea": "Dmax < 80 Gy (QUANTEC SBRT); avoid stenosis",
    "left femur": "V50 < 5% (femoral head avascular necrosis)",
    "right femur": "V50 < 5% (femoral head avascular necrosis)",
    "left hip": "V50 < 5%",
    "right hip": "V50 < 5%",
    "sacrum": "No established QUANTEC limit",
    "colon": "Dmax < 55 Gy (avoidance preferred)",
    "small bowel": "V45 < 195 cc (QUANTEC); Dmax < 50 Gy",
}


# ---------------------------------------------------------------------------
# Label resolution
# ---------------------------------------------------------------------------

def _resolve_anatomy_list(sample_dir: Path) -> list[str] | None:
    """Walk parent directories looking for a generation summary JSON that
    points to a YAML config containing the anatomy_list."""
    for candidate in [sample_dir, sample_dir.parent, sample_dir.parent.parent]:
        summary_path = candidate / "ct_generation_visuals_summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text())
            config_rel = data.get("config", "")
            config_path = Path(config_rel)
            if not config_path.is_absolute():
                config_path = REPO_ROOT / config_path
            if config_path.exists():
                cfg = yaml.safe_load(config_path.read_text())
                anatomy = cfg.get("ct_structures", {}).get("anatomy_list")
                if anatomy:
                    return anatomy
        except Exception:
            continue
    return None


def _build_label_map(anatomy_list: list[str] | None, unique_labels: list[int]) -> dict[int, str]:
    """Return {label_int: structure_name}.

    If anatomy_list is available, labels 1,2,... map to anatomy_list[0,1,...].
    Otherwise fall back to generic names.
    """
    label_map: dict[int, str] = {}
    for lab in unique_labels:
        if lab == 0:
            continue  # background
        if anatomy_list and 1 <= lab <= len(anatomy_list):
            label_map[lab] = anatomy_list[lab - 1]
        else:
            label_map[lab] = f"Structure_{lab:02d}"
    return label_map


# ---------------------------------------------------------------------------
# NIfTI → DICOM CT series
# ---------------------------------------------------------------------------

def _write_dicom_ct_series(
    ct_path: Path,
    out_dir: Path,
) -> tuple[str, str, str]:
    """Convert a NIfTI CT to a DICOM CT series.

    Returns (study_uid, series_uid, frame_uid) — needed when building RT-STRUCT.
    """
    try:
        import pydicom
        from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
        from pydicom.uid import generate_uid, ExplicitVRLittleEndian
    except ImportError:
        sys.exit("pydicom not found. Run: pip install pydicom")

    try:
        import nibabel as nib
    except ImportError:
        sys.exit("nibabel not found. Run: pip install nibabel")

    out_dir.mkdir(parents=True, exist_ok=True)

    ct_img = nib.load(str(ct_path))
    ct_data = ct_img.get_fdata(dtype=np.float32)  # (nx, ny, nz)
    affine = ct_img.affine

    nx, ny, nz = ct_data.shape

    # Voxel spacings from affine columns
    dx = float(np.linalg.norm(affine[:3, 0]))
    dy = float(np.linalg.norm(affine[:3, 1]))
    dz = float(np.linalg.norm(affine[:3, 2]))

    # Direction cosines (NIfTI RAS → DICOM LPS: negate x and y)
    def _to_lps_dir(v: np.ndarray) -> list[float]:
        return [-float(v[0]), -float(v[1]), float(v[2])]

    iop_row = _to_lps_dir(affine[:3, 0] / dx)   # direction along DICOM columns
    iop_col = _to_lps_dir(affine[:3, 1] / dy)   # direction along DICOM rows
    iop = [f"{v:.6f}" for v in iop_row + iop_col]

    study_uid  = generate_uid()
    series_uid = generate_uid()
    frame_uid  = generate_uid()
    patient_id = f"MAISI-{ct_path.stem[:20]}"
    study_date = datetime.now().strftime("%Y%m%d")
    study_time = datetime.now().strftime("%H%M%S")

    for k in range(nz):
        sop_uid = generate_uid()
        filename = out_dir / f"CT{k + 1:04d}.dcm"

        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID   = "1.2.840.10008.5.1.4.1.1.2"
        file_meta.MediaStorageSOPInstanceUID = sop_uid
        file_meta.TransferSyntaxUID         = ExplicitVRLittleEndian

        ds = FileDataset(str(filename), {}, file_meta=file_meta, preamble=b"\0" * 128)

        # Patient
        ds.PatientName    = "MAISI^Synthetic"
        ds.PatientID      = patient_id
        ds.PatientBirthDate = ""
        ds.PatientSex     = ""

        # Study
        ds.StudyInstanceUID  = study_uid
        ds.StudyDate         = study_date
        ds.StudyTime         = study_time
        ds.StudyDescription  = "Synthetic CT — MAISI-RT"
        ds.StudyID           = "1"
        ds.AccessionNumber   = ""

        # Series
        ds.SeriesInstanceUID  = series_uid
        ds.SeriesNumber       = "1"
        ds.SeriesDescription  = f"CT {ct_path.stem}"
        ds.Modality           = "CT"

        # Instance
        ds.SOPClassUID    = "1.2.840.10008.5.1.4.1.1.2"
        ds.SOPInstanceUID = sop_uid
        ds.InstanceNumber = str(k + 1)

        # Image geometry
        ds.ImageType                  = ["ORIGINAL", "PRIMARY", "AXIAL"]
        ds.SamplesPerPixel            = 1
        ds.PhotometricInterpretation  = "MONOCHROME2"
        ds.Rows                       = ny
        ds.Columns                    = nx
        ds.PixelSpacing               = [f"{dy:.6f}", f"{dx:.6f}"]
        ds.SliceThickness             = f"{dz:.6f}"
        ds.SliceLocation              = f"{float(affine[2, 3] + k * affine[2, 2]):.6f}"
        ds.ImageOrientationPatient    = iop

        # Slice position in LPS
        ipp_ras = affine[:3, 3] + k * affine[:3, 2]
        ipp_lps = [-float(ipp_ras[0]), -float(ipp_ras[1]), float(ipp_ras[2])]
        ds.ImagePositionPatient = [f"{v:.6f}" for v in ipp_lps]

        ds.FrameOfReferenceUID        = frame_uid
        ds.PositionReferenceIndicator = ""

        # CT values
        ds.BitsAllocated      = 16
        ds.BitsStored         = 16
        ds.HighBit            = 15
        ds.PixelRepresentation = 1  # signed int16
        ds.RescaleIntercept   = "0"
        ds.RescaleSlope       = "1"
        ds.RescaleType        = "HU"

        # Pixel data: NIfTI (nx, ny) slice → DICOM (ny, nx) rows × cols
        slice_hu = np.clip(ct_data[:, :, k].T, -1024, 3000).astype(np.int16)
        ds.PixelData = slice_hu.tobytes()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ds.save_as(str(filename), write_like_original=False)

    return study_uid, series_uid, frame_uid


# ---------------------------------------------------------------------------
# DICOM RT-STRUCT builder
# ---------------------------------------------------------------------------

def _build_rt_struct(
    dicom_ct_dir: Path,
    label_path: Path,
    label_map: dict[int, str],
    out_path: Path,
    min_voxels: int = 50,
) -> list[dict]:
    """Create a DICOM RT-STRUCT from the DICOM CT series and NIfTI label mask.

    Returns a list of exported-structure records for the manifest.
    """
    try:
        from rt_utils import RTStructBuilder
    except ImportError:
        sys.exit("rt-utils not found. Run: pip install rt-utils")

    try:
        import nibabel as nib
    except ImportError:
        sys.exit("nibabel not found. Run: pip install nibabel")

    label_img  = nib.load(str(label_path))
    label_data = label_img.get_fdata(dtype=np.float32)  # (nx, ny, nz)
    voxel_vol_ml = float(np.prod(label_img.header.get_zooms())) / 1000.0

    rtstruct = RTStructBuilder.create_new(dicom_series_path=str(dicom_ct_dir))
    rtstruct.set_series_description("MAISI-RT Synthetic Structure Set")

    fallback_idx = 0
    exported: list[dict] = []

    for lab_int, name in sorted(label_map.items()):
        if "dummy" in name.lower():
            continue

        mask_3d = label_data == lab_int  # (nx, ny, nz) bool

        n_vox = int(mask_3d.sum())
        if n_vox < min_voxels:
            continue

        # rt-utils validates mask.shape[2] == len(series_data) == nz.
        # It then reads mask[:, :, k] for each DICOM slice k.
        # Our DICOM pixel data per slice k is ct_data[:,:,k].T → shape (ny, nx).
        # So rt-utils expects mask in (ny, nx, nz) order — swap only the first two axes.
        mask_rt = mask_3d.transpose(1, 0, 2)  # (ny, nx, nz)

        color = _COLORS.get(name, _FALLBACK_COLORS[fallback_idx % len(_FALLBACK_COLORS)])
        if name not in _COLORS:
            fallback_idx += 1

        volume_ml = round(n_vox * voxel_vol_ml, 2)

        try:
            rtstruct.add_roi(
                mask=mask_rt,
                color=color,
                name=name,
                description=f"MAISI-RT synthetic | {volume_ml} mL",
                roi_generation_algorithm="AUTOMATIC",
            )
            exported.append({
                "label_int": lab_int,
                "name": name,
                "volume_ml": volume_ml,
                "color_rgb": color,
                "quantec_note": _QUANTEC.get(name, "—"),
                "exported": True,
            })
        except Exception as exc:
            exported.append({
                "label_int": lab_int,
                "name": name,
                "volume_ml": volume_ml,
                "color_rgb": color,
                "quantec_note": _QUANTEC.get(name, "—"),
                "exported": False,
                "error": str(exc),
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rtstruct.save(str(out_path))
    return exported


# ---------------------------------------------------------------------------
# Auto-discovery helpers
# ---------------------------------------------------------------------------

def _find_ct_label_pair(path: Path) -> tuple[Path, Path]:
    """Find CT image + label NIfTI pair inside a directory."""
    niftis = sorted(path.glob("*.nii.gz"))
    images = [f for f in niftis if "_image" in f.name]
    labels = [f for f in niftis if "_label" in f.name]
    if not images:
        sys.exit(f"No *_image.nii.gz found in {path}")
    if not labels:
        sys.exit(f"No *_label.nii.gz found in {path} — MRI presets have no label file")
    return images[0], labels[0]


def _list_exportable_outputs() -> list[Path]:
    """Find all sample directories that contain both CT image and label files."""
    outputs_dir = REPO_ROOT / "outputs"
    results = []
    for label in sorted(outputs_dir.rglob("*_label.nii.gz")):
        image = label.parent / label.name.replace("_label", "_image")
        if image.exists():
            results.append(label.parent)
    return results


def _find_latest_for_preset(preset_name: str) -> Path:
    """Resolve a preset name like 'ct_pelvis_rt' to its latest sample directory."""
    outputs_dir = REPO_ROOT / "outputs"
    candidates = sorted(
        (d for d in outputs_dir.iterdir()
         if d.is_dir() and preset_name.lower().replace("-", "_") in d.name.lower()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"No output directory found for preset '{preset_name}'")
    preset_dir = candidates[0]

    # Find sample subdirectories
    sample_dirs = sorted(
        (d for d in (preset_dir / "visuals").rglob("*_label.nii.gz")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not sample_dirs:
        sys.exit(f"No sample output found inside {preset_dir}")
    return sample_dirs[0].parent


# ---------------------------------------------------------------------------
# Main export orchestrator
# ---------------------------------------------------------------------------

def export(
    ct_path: Path,
    label_path: Path,
    out_dir: Path | None = None,
    min_voxels: int = 50,
    quiet: bool = False,
) -> Path:
    """Run the full NIfTI → DICOM CT + RT-STRUCT pipeline.

    Returns the output directory path.
    """
    try:
        from rich.console import Console
        from rich.table import Table
        console = Console()
    except ImportError:
        class _FallbackConsole:
            def print(self, *a, **kw): print(*a)
            def rule(self, *a, **kw): print("-" * 60)
        console = _FallbackConsole()
        Table = None

    # Resolve output dir
    stem = label_path.stem.replace(".nii", "").replace("_label", "")
    if out_dir is None:
        out_dir = REPO_ROOT / "outputs" / "dicom_export" / stem

    ct_out   = out_dir / "CT"
    rt_out   = out_dir / "RT" / f"RS_{stem}.dcm"
    manifest = out_dir / "manifest.json"

    if not quiet:
        console.rule("[bold cyan]MAISI-RT → DICOM RT-STRUCT Export")
        console.print(f"  CT image : [green]{ct_path}[/]")
        console.print(f"  Label    : [green]{label_path}[/]")
        console.print(f"  Output   : [yellow]{out_dir}[/]")
        console.print()

    # Resolve anatomy list (1-indexed → structure name)
    anatomy_list = _resolve_anatomy_list(label_path.parent)

    import nibabel as nib
    label_data = nib.load(str(label_path)).get_fdata(dtype=np.float32)
    unique_labs = [int(v) for v in np.unique(label_data) if v != 0]
    label_map   = _build_label_map(anatomy_list, unique_labs)

    if not quiet:
        console.print(f"  Structures found ({len(label_map)}): "
                      + ", ".join(label_map.values()))
        console.print()

    # Step 1 — NIfTI CT → DICOM CT series
    if not quiet:
        console.print("[bold]Step 1/2[/] Writing DICOM CT series …", end=" ")
    _write_dicom_ct_series(ct_path, ct_out)
    if not quiet:
        n_slices = len(list(ct_out.glob("*.dcm")))
        console.print(f"[green]done[/] ({n_slices} slices → {ct_out.name}/)")

    # Step 2 — DICOM CT + label → RT-STRUCT
    if not quiet:
        console.print("[bold]Step 2/2[/] Building RT-STRUCT …", end=" ")
    exported = _build_rt_struct(ct_out, label_path, label_map, rt_out, min_voxels)
    if not quiet:
        n_ok = sum(1 for e in exported if e["exported"])
        console.print(f"[green]done[/] ({n_ok}/{len(exported)} structures exported)")

    # Write manifest
    manifest_data = {
        "generated": datetime.now().isoformat(),
        "ct_source": str(ct_path),
        "label_source": str(label_path),
        "dicom_ct_dir": str(ct_out),
        "rt_struct_file": str(rt_out),
        "structures": exported,
    }
    manifest.write_text(json.dumps(manifest_data, indent=2))

    # Print summary table
    if not quiet:
        console.print()
        console.rule("[bold]Exported structures")
        if Table is not None:
            tbl = Table(show_header=True, header_style="bold magenta")
            tbl.add_column("#", style="dim", width=3)
            tbl.add_column("Structure", min_width=30)
            tbl.add_column("Volume (mL)", justify="right")
            tbl.add_column("QUANTEC note", max_width=50, overflow="fold")
            for row in exported:
                status = "[green]✓[/]" if row["exported"] else "[red]✗[/]"
                tbl.add_row(
                    status,
                    row["name"],
                    str(row["volume_ml"]),
                    row["quantec_note"],
                )
            console.print(tbl)
        else:
            for row in exported:
                mark = "OK" if row["exported"] else "FAIL"
                print(f"  [{mark}] {row['name']:35s} {row['volume_ml']:8.1f} mL")

        console.print()
        console.rule("[bold]Next steps")
        console.print(
            "  [cyan]3D Slicer[/]: drag the [yellow]CT/[/] folder into Slicer, "
            "then drag [yellow]RT/RS_*.dcm[/] → choose [italic]Segmentation[/]"
        )
        console.print(
            f"  [cyan]Manifest [/]: {manifest}  (volumes + QUANTEC notes)"
        )
        console.print()

    return out_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export MAISI NIfTI CT + label → DICOM CT series + RT-STRUCT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--pair",   metavar="DIR",
                     help="Directory containing *_image.nii.gz and *_label.nii.gz")
    grp.add_argument("--preset", metavar="NAME",
                     help="Preset name (e.g. ct_pelvis_rt) — finds latest output automatically")
    grp.add_argument("--list",   action="store_true",
                     help="List all exportable sample directories and exit")
    parser.add_argument("--ct",    metavar="FILE", help="CT NIfTI path (explicit)")
    parser.add_argument("--label", metavar="FILE", help="Label NIfTI path (explicit)")
    parser.add_argument("--out",   metavar="DIR",  help="Output directory (default: outputs/dicom_export/…)")
    parser.add_argument("--min-voxels", type=int, default=50,
                        help="Skip structures with fewer than N voxels (default: 50)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    if args.list:
        dirs = _list_exportable_outputs()
        if not dirs:
            print("No exportable outputs found in outputs/")
        else:
            print(f"Found {len(dirs)} exportable sample(s):\n")
            for d in dirs:
                print(f"  {d}")
            print(f"\nRun with:  python scripts/export_rt_struct.py --pair <dir>")
        return

    if args.pair:
        sample_dir = Path(args.pair).resolve()
        ct_path, label_path = _find_ct_label_pair(sample_dir)
    elif args.preset:
        sample_dir = _find_latest_for_preset(args.preset)
        ct_path, label_path = _find_ct_label_pair(sample_dir)
    elif args.ct and args.label:
        ct_path    = Path(args.ct).resolve()
        label_path = Path(args.label).resolve()
    else:
        parser.print_help()
        sys.exit(1)

    out_dir = Path(args.out).resolve() if args.out else None
    export(ct_path, label_path, out_dir=out_dir, min_voxels=args.min_voxels, quiet=args.quiet)


if __name__ == "__main__":
    main()
