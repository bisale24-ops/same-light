# Real footage: what happened when Same Light met real camera frames

Frames from free stock clips (Pexels licence) in which one person is filmed by one camera while the light on the face changes. Frames at 10%, 50% and 90% of each clip, fixed in advance; the 10% frame is the baseline. In the second pass each frame was cut to selfie framing by one fixed automatic rule (largest skin-coloured blob, padded, square: `experiments/clip_frames.py`). No frame was chosen or replaced by a person; YouCam decided what was usable. Images are not republished here, only clip ids and results. 14 clips tried.

## What YouCam did with them

| clip (Pexels id) | frames given to YouCam | result |
|---|---|---|
| 8055709 | whole frame | baseline refused: face out of bound |
| 10050974 | whole frame | baseline refused: large face angle |
| 7298060 | whole frame | baseline refused: face out of bound |
| 7679947 | cropped | baseline refused: large face angle |
| 10043022 | cropped | baseline refused: face too small |
| **9464484** | cropped | **scanned, see below** |
| 6287106 | cropped | baseline refused: large face angle |
| 7297906 | cropped | baseline refused: no face |
| 6299222 | cropped | baseline refused: face too small |
| 4824123 | cropped | baseline accepted; 50% frame refused (face too small); 90% frame 65% darker than baseline: retake (light too different) |
| 6287086 | cropped | baseline refused: face too small |
| 6274541 | cropped | baseline refused: no face |
| 6287171 | cropped | baseline refused: large face angle |
| 10250519 | cropped | baseline refused: face out of bound |
| 7038590 | not tried | set aside before scanning: hair motion blur over the face |

Of 14 clips, one produced a comparison. That is a result about the API's capture rules (a near-frontal, whole, large face), which is why the app has a guided camera; it also means this is **one clip, not a validation**.

## The one clip scanned: 9464484 (a man, strong blue and orange light splitting the face)

Baseline 10%; light2 = 50% frame (25% brighter than baseline, calibrated range); light3 = 90% frame (refused by YouCam: no face; the automatic crop had missed the face).

| | wrinkle | pore | texture | acne | total gap |
|---|---|---|---|---|---|
| gap as shot | -6 | -8 | -10 | 0 | **24** |
| gap after matching | -4 | -11 | -18 | +6 | **39** |

**Matching made the total gap larger (24 to 39).** Verdicts: as shot wrinkle, pore, texture worse and acne noise; after matching wrinkle and acne borderline, pore and texture worse. The pose and expression also changed between the two frames, so part of the gap is not light at all.

Why it fails, in plain words: Same Light reads one average light for the whole face and moves the whole photo toward the baseline's average. When one half of the face is blue and the other orange, there is no single light to match; the correction cannot undo it, and here it pushed the score the wrong way.

## What I tried and did not ship

A guard for uneven light: compare the left and right half of the face crop for brightness and warmth. On the clip frames, the four test faces and the sample photos, the split-light clip's warmth difference (0.43 at baseline, 0.24 at the matched frame) is not separable from a test face that worked (face D, 0.23) or from sun-and-sky frames (0.19 to 0.36), and brightness difference is dominated by head pose. Any threshold would be fitted to one example, so no new rule was added.

## What it changes for the claim

Same Light's matching is measured to work for an even change of exposure or colour temperature on three faces (`experiments/RESULTS.md`), and has now been seen to fail on one real frame pair with split coloured light. The claim stays "a score change that beats the light noise, under evenly lit photos"; it does not cover strongly uneven or coloured light.
