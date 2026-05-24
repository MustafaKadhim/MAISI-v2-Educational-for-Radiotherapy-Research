# Release Checklist

- [ ] README quickstart is current
- [ ] `docs/maisi2_generation_guide.md` matches the current NVIDIA release notes
- [ ] `python -m py_compile scripts/*.py` passes
- [ ] Brain visual rebuild passes:
  `python scripts/run_nvidia_case_from_config.py --config configs/maisi2/01_mr_brain_all_contrasts.yaml --skip-generation`
- [ ] CT visual rebuild passes:
  `python scripts/run_nvidia_ct_structures_from_config.py --config configs/maisi2/02_ct_paired_image_mask.yaml --skip-generation`
- [ ] README gallery rebuild passes:
  `python scripts/make_readme_gallery.py`
- [ ] MAISI 2 recipe notebook opens:
  `jupyter notebook tutorials/03_generation_recipe_cookbook.ipynb`
- [ ] No generated outputs, model weights, venvs, or caches are committed
- [ ] Clinical disclaimer remains visible
