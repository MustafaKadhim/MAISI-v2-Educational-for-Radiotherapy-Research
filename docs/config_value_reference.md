# MAISI/NVIDIA config value reference

This page summarizes the config values used by this workspace for:

- CT paired image/mask generation: `ct_structures.body_region` and `ct_structures.anatomy_list`
- Brain MR generation: `nvidia.modality`

Sources in this repo:

- CT `body_region` options: `external/NV-Generate-CTMR/docs/inference.md`
- CT `anatomy_list` labels: `external/NV-Generate-CTMR/configs/label_dict.json`
- Brain/MR `modality` labels: `external/NV-Generate-CTMR/configs/modality_mapping.json`

## CT case: `body_region`

`body_region` is a list of one or more coarse scan regions.

For `maisi3d_rflow` / `rflow-ct`, NVIDIA marks `body_region` as deprecated and says it can be set to `[]`; the generated region is mainly determined by `anatomy_list`. In this project it is still exposed because the upstream CT inference config includes it.

Valid region strings documented by NVIDIA:

| Value | Meaning / typical use |
|---|---|
| `head` | Head / neck field of view |
| `chest` | Chest / thorax-focused CT |
| `thorax` | Thorax synonym/region option listed by NVIDIA |
| `abdomen` | Abdominal CT |
| `pelvis` | Pelvic CT |
| `lower` | Lower body / lower-extremity region |

Common training-data region combinations from NVIDIA's inference guide:

| `body_region` | Recommended `output_size` | Recommended `spacing` mm |
|---|---:|---:|
| `["chest", "abdomen"]` | `[512, 512, 128]` | `[0.781, 0.781, 2.981]` |
| `["chest"]` | `[512, 512, 128]` | `[0.684, 0.684, 2.422]` |
| `["chest", "abdomen", "lower"]` | `[512, 512, 256]` | `[0.793, 0.793, 1.826]` |
| `["lower"]` | `[512, 512, 384]` | `[0.839, 0.839, 0.728]` |
| `["abdomen", "lower"]` | `[512, 512, 384]` | `[0.808, 0.808, 0.729]` |
| `["head", "chest", "abdomen"]` | `[512, 512, 384]` | `[0.977, 0.977, 2.103]` |
| `["abdomen"]` | `[512, 512, 128]` | `[0.723, 0.723, 1.182]` |
| `["head", "chest", "abdomen", "lower"]` | `[512, 512, 384]` | `[1.367, 1.367, 4.603]` |
| `["head", "chest"]` | `[512, 512, 128]` | `[0.645, 0.645, 2.219]` |

Example:

```yaml
ct_structures:
  body_region: ["chest"]
```

## CT case: `anatomy_list`

`anatomy_list` is a list of anatomy/structure names. Names should match `label_dict.json` exactly. Dummy labels from the upstream label dictionary are intentionally omitted below.

Example:

```yaml
ct_structures:
  anatomy_list: ["lung tumor", "heart", "left lung upper lobe", "right lung lower lobe"]
```

### Abdominal / pelvic organs and vessels

| Label ID | `anatomy_list` value |
|---:|---|
| 1 | `liver` |
| 3 | `spleen` |
| 4 | `pancreas` |
| 5 | `right kidney` |
| 6 | `aorta` |
| 7 | `inferior vena cava` |
| 8 | `right adrenal gland` |
| 9 | `left adrenal gland` |
| 10 | `gallbladder` |
| 11 | `esophagus` |
| 12 | `stomach` |
| 13 | `duodenum` |
| 14 | `left kidney` |
| 15 | `bladder` |
| 17 | `portal vein and splenic vein` |
| 19 | `small bowel` |
| 58 | `left iliac artery` |
| 59 | `right iliac artery` |
| 60 | `left iliac vena` |
| 61 | `right iliac vena` |
| 62 | `colon` |
| 116 | `left kidney cyst` |
| 117 | `right kidney cyst` |
| 118 | `prostate` |

### Tumors / lesions

| Label ID | `anatomy_list` value |
|---:|---|
| 23 | `lung tumor` |
| 24 | `pancreatic tumor` |
| 26 | `hepatic tumor` |
| 27 | `colon cancer primaries` |
| 128 | `bone lesion` |

### Chest / airway / cardiovascular

| Label ID | `anatomy_list` value |
|---:|---|
| 25 | `hepatic vessel` |
| 28 | `left lung upper lobe` |
| 29 | `left lung lower lobe` |
| 30 | `right lung upper lobe` |
| 31 | `right lung middle lobe` |
| 32 | `right lung lower lobe` |
| 57 | `trachea` |
| 108 | `left atrial appendage` |
| 109 | `brachiocephalic trunk` |
| 110 | `left brachiocephalic vein` |
| 111 | `right brachiocephalic vein` |
| 112 | `left common carotid artery` |
| 113 | `right common carotid artery` |
| 115 | `heart` |
| 119 | `pulmonary vein` |
| 123 | `left subclavian artery` |
| 124 | `right subclavian artery` |
| 125 | `superior vena cava` |
| 126 | `thyroid gland` |
| 132 | `airway` |

### Brain / head / spine

| Label ID | `anatomy_list` value |
|---:|---|
| 22 | `brain` |
| 120 | `skull` |
| 121 | `spinal cord` |

### Vertebrae

| Label ID | `anatomy_list` value |
|---:|---|
| 33 | `vertebrae L5` |
| 34 | `vertebrae L4` |
| 35 | `vertebrae L3` |
| 36 | `vertebrae L2` |
| 37 | `vertebrae L1` |
| 38 | `vertebrae T12` |
| 39 | `vertebrae T11` |
| 40 | `vertebrae T10` |
| 41 | `vertebrae T9` |
| 42 | `vertebrae T8` |
| 43 | `vertebrae T7` |
| 44 | `vertebrae T6` |
| 45 | `vertebrae T5` |
| 46 | `vertebrae T4` |
| 47 | `vertebrae T3` |
| 48 | `vertebrae T2` |
| 49 | `vertebrae T1` |
| 50 | `vertebrae C7` |
| 51 | `vertebrae C6` |
| 52 | `vertebrae C5` |
| 53 | `vertebrae C4` |
| 54 | `vertebrae C3` |
| 55 | `vertebrae C2` |
| 56 | `vertebrae C1` |
| 127 | `vertebrae S1` |

### Ribs / shoulder girdle / sternum

| Label ID | `anatomy_list` value |
|---:|---|
| 63 | `left rib 1` |
| 64 | `left rib 2` |
| 65 | `left rib 3` |
| 66 | `left rib 4` |
| 67 | `left rib 5` |
| 68 | `left rib 6` |
| 69 | `left rib 7` |
| 70 | `left rib 8` |
| 71 | `left rib 9` |
| 72 | `left rib 10` |
| 73 | `left rib 11` |
| 74 | `left rib 12` |
| 75 | `right rib 1` |
| 76 | `right rib 2` |
| 77 | `right rib 3` |
| 78 | `right rib 4` |
| 79 | `right rib 5` |
| 80 | `right rib 6` |
| 81 | `right rib 7` |
| 82 | `right rib 8` |
| 83 | `right rib 9` |
| 84 | `right rib 10` |
| 85 | `right rib 11` |
| 86 | `right rib 12` |
| 87 | `left humerus` |
| 88 | `right humerus` |
| 89 | `left scapula` |
| 90 | `right scapula` |
| 91 | `left clavicula` |
| 92 | `right clavicula` |
| 114 | `costal cartilages` |
| 122 | `sternum` |

### Pelvis / lower body / muscles

| Label ID | `anatomy_list` value |
|---:|---|
| 93 | `left femur` |
| 94 | `right femur` |
| 95 | `left hip` |
| 96 | `right hip` |
| 97 | `sacrum` |
| 98 | `left gluteus maximus` |
| 99 | `right gluteus maximus` |
| 100 | `left gluteus medius` |
| 101 | `right gluteus medius` |
| 102 | `left gluteus minimus` |
| 103 | `right gluteus minimus` |
| 104 | `left autochthon` |
| 105 | `right autochthon` |
| 106 | `left iliopsoas` |
| 107 | `right iliopsoas` |

### Whole-body label

| Label ID | `anatomy_list` value |
|---:|---|
| 200 | `body` |

## Brain case: `modality`

In `configs/maisi2/01_mr_brain_all_contrasts.yaml`, `nvidia.modality` or
`nvidia.modalities` may be supplied as either string keys or numeric IDs from
`modality_mapping.json`.

Recommended/supported brain MR choices from NVIDIA's `rflow-mr-brain` release:

| `modality` string | Numeric ID | Notes |
|---|---:|---|
| `mri_t1` | 9 | T1-weighted whole-brain MRI; default in this workspace |
| `mri_t2` | 10 | T2-weighted whole-brain MRI |
| `mri_flair` | 11 | FLAIR whole-brain MRI |
| `mri_swi` | 20 | SWI whole-brain MRI |
| `mri_t1_skull_stripped` | 29 | T1-weighted skull-stripped brain MRI |
| `mri_t2_skull_stripped` | 30 | T2-weighted skull-stripped brain MRI |
| `mri_flair_skull_stripped` | 31 | FLAIR skull-stripped brain MRI |
| `mri_swi_skull_stripped` | 32 | SWI skull-stripped brain MRI |

Example:

```yaml
nvidia:
  modality: "mri_t1"
```

Equivalent numeric form:

```yaml
nvidia:
  modality: 9
```

For non-brain MRI with the official `rflow-mr` model, keep the same modality
strings but choose an anatomy-appropriate FOV. Starter examples live in:

- `configs/maisi2/04_mr_prostate_t2.yaml`
- `configs/maisi2/05_mr_breast_t1.yaml`
- `configs/maisi2/06_mr_abdomen_t1.yaml`

Full modality mapping file, for reference:

| `modality` string | Numeric ID |
|---|---:|
| `unknown` | 0 |
| `ct` | 1 |
| `ct_wo_contrast` | 2 |
| `ct_contrast` | 3 |
| `mri` | 8 |
| `mri_t1` | 9 |
| `mri_t2` | 10 |
| `mri_flair` | 11 |
| `mri_pd` | 12 |
| `mri_dwi` | 13 |
| `mri_adc` | 14 |
| `mri_ssfp` | 15 |
| `mri_mra` | 16 |
| `mri_t1c` | 17 |
| `mri_swi` | 20 |
| `mri_t1_skull_stripped` | 29 |
| `mri_t2_skull_stripped` | 30 |
| `mri_flair_skull_stripped` | 31 |
| `mri_swi_skull_stripped` | 32 |
| `mri_mra_skull_stripped` | 33 |
