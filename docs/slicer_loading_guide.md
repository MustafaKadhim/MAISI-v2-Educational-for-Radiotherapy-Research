# 3D Slicer Loading Guide

For CT + structures, load the generated image and label pair from a sample folder, for example:

```text
outputs/maisi2_showcase_ct_chest_cardio_lung/visuals/sample_001_seed71001/ct_seed71001_image.nii.gz
outputs/maisi2_showcase_ct_chest_cardio_lung/visuals/sample_001_seed71001/ct_seed71001_label.nii.gz
```

In 3D Slicer:

1. File → Add Data → load the image as a volume.
2. File → Add Data → load the label as a label map or segmentation.
3. Adjust opacity in the Segmentations/Volumes modules.
4. Compare with generated PNG overlays in the same sample folder.

All data are synthetic research outputs only.
