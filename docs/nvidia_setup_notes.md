# NVIDIA / MAISI Setup Notes

This streamlined repo uses the official NVIDIA `NV-Generate-CTMR` clone in `external/NV-Generate-CTMR`.

Required workflows:

```bash
# Brain MRI, general MRI, or CT image-only
python scripts/run_nvidia_case_from_config.py --config configs/maisi2/01_mr_brain_all_contrasts.yaml

# CT + paired structures
python scripts/run_nvidia_ct_structures_from_config.py --config configs/maisi2/02_ct_paired_image_mask.yaml

# CT from a user-provided MAISI label mask
python scripts/run_nvidia_ct_from_mask_config.py --config configs/maisi2/07_ct_from_own_mask.yaml
```

The helper scripts regenerate temporary NVIDIA JSON configs from the YAML files as needed.
Do not commit model weights, generated outputs, or downloaded datasets.

See [maisi2_generation_guide.md](maisi2_generation_guide.md) for the complete
public recipe map.
