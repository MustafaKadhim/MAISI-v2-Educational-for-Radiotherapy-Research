# Model Card — MAISI-RT Sandbox

> **Note:** MAISI-RT Sandbox is a framework, not a model. This document
> describes the models it is designed to work with. No model weights are
> included in this repository.

## Framework overview

| Property | Value |
|---|---|
| Framework name | MAISI-RT Sandbox |
| Version | 0.1.0 |
| Task | Radiotherapy-oriented QA and visualization for synthetic CT/MR data |
| Input | NIfTI volumes (`.nii`, `.nii.gz`) |
| Output | QA reports, visualization PNGs, label maps, Slicer guides |

## Upstream models

MAISI-RT Sandbox is designed to process outputs from the following NVIDIA models:

### MAISI-v2 RFlow variants

- **Developer:** NVIDIA
- **Variants:** `rflow-mr-brain`, `rflow-mr`, `rflow-ct`
- **Task:** Synthetic CT and MR volume generation
- **Supported public workflows in this repo:**
  - Brain MRI image-only generation across T1w, T2w, FLAIR, SWI, including skull-stripped variants
  - General MR image-only generation examples for prostate, breast, and abdomen
  - CT image-only generation
  - CT paired image/mask generation
  - CT from a user-provided MAISI label mask
- **License:** Governed by NVIDIA's own license — see NVIDIA's official documentation
- **Weights:** Not included in this repository

### MAISI-v1 legacy CT

- **Developer:** NVIDIA
- **Variant:** `ddpm-ct`
- **Task:** Legacy CT image/mask generation
- **Note:** Kept as an advanced comparison path. This repository's beginner tutorials focus on MAISI-v2 `rflow-*` variants.
- **License:** Governed by NVIDIA's license — see NVIDIA's official repository
- **Weights:** Not included in this repository

## Intended use

- Research into synthetic medical image generation
- Education and teaching for radiotherapy students and physicists
- AI model prototyping and evaluation
- Community demonstrations of RT structure labeling pipelines

## Out-of-scope use

- Clinical diagnosis
- Treatment planning
- Dose calculation
- Patient-specific quality assurance
- Regulatory submission

## Performance and validation

MAISI-RT Sandbox has not been clinically validated. QA thresholds in
`configs/qa_rules.yaml` are illustrative and not derived from clinical data.

## Ethical considerations

- Synthetic data may perpetuate biases present in the training data of the
  upstream NVIDIA models.
- Synthetic anatomy may not represent the full diversity of patient anatomy.
- Users should not use synthetic outputs as a substitute for real clinical data
  in any safety-critical application.

## Citation

If you use MAISI-RT Sandbox in your research, please cite:

- This repository (see `CITATION.cff`)
- MAISI / NVIDIA NV-Generate-CTMR (follow NVIDIA's citation guidelines)
