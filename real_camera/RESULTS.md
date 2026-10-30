# Real-camera feasibility test

Frames of real footage: the same person and the same camera within one clip, light changing as they move in sunlight (free stock clips, Pexels licence; frames at 10%, 50% and 90% of each clip, fixed in advance; none dropped or replaced). The skin is the same, but pose and expression change between frames, which also moves scores, so this is a feasibility test on three clips, not a validation: it says nothing about other skin, cameras or rooms.

## k6282217

Baseline light reading: ok.

| light | drift from baseline | reading | comparable | calibrated | scores as shot (wr/po/tx/ac) | gap as shot | gap matched | total gap as shot -> matched | verdict as shot | verdict matched |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | refused by YouCam: error_large_face_angle | | | | | | | | | |

## k6595457

Baseline light reading: ok.

| light | drift from baseline | reading | comparable | calibrated | scores as shot (wr/po/tx/ac) | gap as shot | gap matched | total gap as shot -> matched | verdict as shot | verdict matched |
|---|---|---|---|---|---|---|---|---|---|---|
| light2 | warmer than your baseline | ok | True | True | refused by YouCam: as shot error_large_face_angle, matched error_large_face_angle |  |  |  |  |  |
| light3 | 15% brighter and warmer than your baseline | ok | True | True | 82/77/98/81 | +3/-4/+4/-3 | +7/+1/+4/-2 | 14 -> 14 | wrinkle:borderline, pore:borderline, texture:borderline, acne:noise | wrinkle:better, pore:noise, texture:borderline, acne:noise |

## k7884812

Baseline light reading: ok.

| light | drift from baseline | reading | comparable | calibrated | scores as shot (wr/po/tx/ac) | gap as shot | gap matched | total gap as shot -> matched | verdict as shot | verdict matched |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | refused by YouCam: error_src_face_too_small | | | | | | | | | |

## k8151900

Baseline light reading: ok.

| light | drift from baseline | reading | comparable | calibrated | scores as shot (wr/po/tx/ac) | gap as shot | gap matched | total gap as shot -> matched | verdict as shot | verdict matched |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | refused by YouCam: error_src_face_too_small | | | | | | | | | |

