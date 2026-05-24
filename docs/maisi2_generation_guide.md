# MAISI 2 generation guide

This guide is the public-facing map for people who want to generate synthetic
CT/MR examples without first learning the full NVIDIA codebase.

The local recipes wrap the official NVIDIA
[NV-Generate-CTMR](https://github.com/NVIDIA-Medtech/NV-Generate-CTMR)
workflows. As of 2026-05-23, the official README lists MAISI-v2 rectified-flow
variants for `rflow-mr-brain`, `rflow-mr`, and `rflow-ct`, plus legacy
`ddpm-ct` from MAISI-v1.

## Fast mental model

| Goal | Use this model | Local recipe | Local command |
|---|---|---|---|
| Brain MRI, all released contrasts | `rflow-mr-brain` | `configs/maisi2/01_mr_brain_all_contrasts.yaml` | `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/01_mr_brain_all_contrasts.yaml` |
| CT plus paired segmentation mask | `rflow-ct` | `configs/maisi2/02_ct_paired_image_mask.yaml` | `python scripts/run_nvidia_ct_structures_from_config.py --config configs/maisi2/02_ct_paired_image_mask.yaml` |
| CT image only, no mask | `rflow-ct` | `configs/maisi2/03_ct_image_only.yaml` | `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/03_ct_image_only.yaml` |
| Prostate T2 MRI | `rflow-mr` | `configs/maisi2/04_mr_prostate_t2.yaml` | `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/04_mr_prostate_t2.yaml` |
| Breast T1 MRI | `rflow-mr` | `configs/maisi2/05_mr_breast_t1.yaml` | `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/05_mr_breast_t1.yaml` |
| Abdomen T1 MRI | `rflow-mr` | `configs/maisi2/06_mr_abdomen_t1.yaml` | `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/06_mr_abdomen_t1.yaml` |
| CT from your own label mask | `rflow-ct` ControlNet | `configs/maisi2/07_ct_from_own_mask.yaml` | `python scripts/run_nvidia_ct_from_mask_config.py --config configs/maisi2/07_ct_from_own_mask.yaml` |

Showcase CT recipes used for the README gallery:

| Body region | Recipe |
|---|---|
| Head/neck | `configs/maisi2/showcase_ct_head_neck.yaml` |
| Chest/cardio/lung | `configs/maisi2/showcase_ct_chest_cardio_lung.yaml` |
| Abdomen organs/tumor | `configs/maisi2/showcase_ct_abdomen_organs_tumor.yaml` |
| Pelvis RT | `configs/maisi2/showcase_ct_pelvis_rt.yaml` |

Activate the environment first:

```bash
source MAISI_venv/bin/activate
```

## What the official MAISI 2 release supports

| Official variant | Architecture | What it generates | Practical starting point |
|---|---|---|---|
| `rflow-mr-brain` | MAISI-v2 rectified flow | Brain MRI image-only volumes. Whole-brain and skull-stripped T1w, T2w, FLAIR, SWI. | Use recipe 01. This is the best model for brain MRI demos. |
| `rflow-mr` | MAISI-v2 rectified flow | MR image-only volumes for non-brain or broader MRI examples. NVIDIA lists prostate T2, breast T1, abdomen T1/T2, plus older brain MRI support. | Use recipes 04-06. For brain MRI, prefer `rflow-mr-brain`. |
| `rflow-ct` | MAISI-v2 rectified flow | CT image-only, CT plus paired 132-class segmentation masks, and CT generated from a valid user mask. | Use recipes 02, 03, and 07. |
| `ddpm-ct` | MAISI-v1 DDPM | Legacy CT image/mask generation. | Keep as an advanced comparison only; `rflow-ct` is the low-barrier default. |

The official README says the MAISI-v2 RFlow models use 30 inference steps.
`ddpm-ct` uses 1000 steps and is much slower, so this repo keeps the public
learning path centered on the MAISI-v2 `rflow-*` variants.

## Brain MRI contrast choices

Use these values in `nvidia.modality` or `nvidia.modalities`.

| Modality string | Numeric ID | Output |
|---|---:|---|
| `mri_t1` | 9 | T1-weighted whole-brain MRI |
| `mri_t2` | 10 | T2-weighted whole-brain MRI |
| `mri_flair` | 11 | FLAIR whole-brain MRI |
| `mri_swi` | 20 | SWI whole-brain MRI |
| `mri_t1_skull_stripped` | 29 | T1-weighted skull-stripped brain MRI |
| `mri_t2_skull_stripped` | 30 | T2-weighted skull-stripped brain MRI |
| `mri_flair_skull_stripped` | 31 | FLAIR skull-stripped brain MRI |
| `mri_swi_skull_stripped` | 32 | SWI skull-stripped brain MRI |

Recipe 01 runs all of these. To make the first GPU run short, temporarily keep
only one or two entries in `modalities`.

## CT paired mask controls

For `rflow-ct` paired generation, edit:

```yaml
ct_structures:
  body_region: ["chest"]
  anatomy_list: ["lung tumor"]
  controllable_anatomy_size: []
```

`anatomy_list` names must match NVIDIA's `configs/label_dict.json`. This repo
summarizes commonly useful labels in
[config_value_reference.md](config_value_reference.md).

The paired workflow produces:

```text
outputs/.../
  raw/sample_001_seed.../
    sample_..._image.nii.gz
    sample_..._label.nii.gz
  visuals/sample_001_seed.../
    ct_seed..._image.nii.gz
    ct_seed..._label.nii.gz
    ct_orthogonal_panel.png
    ct_structure_overlay_axial_4x4.png
```

## CT from your own mask

Use recipe 07 only after setting:

```yaml
ct_from_mask:
  mask_path: "path/to/your_maisi_132_label_mask_with_body200.nii.gz"
```

The mask must be:

- NIfTI, one channel, integer labels.
- In the MAISI 132-class label vocabulary.
- Include the body envelope label `200`.

If a mask comes from another segmentation tool, remap labels to MAISI IDs first.
The official NVIDIA script can resample shape/spacing, but best results come
from preparing a valid grid before inference.

## Field of view rule

The key quality rule is:

```text
field of view in mm = output_size * spacing
```

Stay close to FOVs used in the official training distribution.

| Recipe | Starter `output_size` | Starter `spacing` mm | Approximate FOV mm |
|---|---:|---:|---:|
| Brain MRI | `[256, 256, 256]` | `[1.0, 1.0, 1.0]` | `256 x 256 x 256` |
| CT demo | `[256, 256, 128]` | `[1.5, 1.5, 2.0]` | `384 x 384 x 256` |
| Prostate T2 MRI | `[256, 256, 128]` | `[0.66, 0.66, 0.70]` | `169 x 169 x 90` |
| Breast T1 MRI | `[256, 256, 128]` | `[0.68, 0.78, 1.56]` | `174 x 200 x 200` |
| Abdomen T1 MRI | `[256, 256, 128]` | `[1.48, 1.21, 2.25]` | `379 x 310 x 288` |

Avoid tiny debug volumes such as `[128, 128, 64]`; they may be numerically
convenient but anatomically out-of-distribution.

## Visualization workflow

Every local wrapper creates PNGs automatically:

- Orthogonal center panels.
- 4x4 random slice grids.
- Axial/coronal/sagittal sweep grids.
- CT structure overlays when a mask is available.
- JSON summaries for reproducibility.

For LinkedIn or presentation figures, run:

```bash
source MAISI_venv/bin/activate
python scripts/make_readme_gallery.py
python scripts/make_showcase_figures.py
python scripts/make_animated_gifs.py
```

Figures are written to `figures/`.

## Suggested public learning path

1. Read the top-level [README](../README.md).
2. Open [tutorials/00_getting_started.ipynb](../tutorials/00_getting_started.ipynb).
3. Run [tutorials/01_ct_deep_dive.ipynb](../tutorials/01_ct_deep_dive.ipynb) to learn HU windows and masks.
4. Run [tutorials/02_brain_mri_exploration.ipynb](../tutorials/02_brain_mri_exploration.ipynb) to learn MRI visual inspection.
5. Use [tutorials/03_generation_recipe_cookbook.ipynb](../tutorials/03_generation_recipe_cookbook.ipynb) to choose a generation recipe.
6. Generate one GPU sample, inspect the PNGs, then scale up seeds/modalities.

## Safety note

This repo is for research, education, and AI prototyping only. Synthetic outputs
are not clinically validated and must not be used for diagnosis, treatment
planning, dose calculation, patient-specific QA, or clinical decision-making.
