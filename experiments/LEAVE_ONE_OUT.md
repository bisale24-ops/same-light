# Leave one face out

Band per concern = the largest absolute matched residual on the other two faces (the same way the shipped bands were set, without the acne jitter allowance). Scored on the held-out face: 4 lights x 4 concerns = 16 readings. Nothing removed.

| held-out face | band (wr/po/tx/ac) | matched readings outside the band | worst miss | readings as shot outside the band |
|---|---|---|---|---|
| A | 0/1/1/3 | 4 of 16 (0.85 warm wrinkle +1, 1.2 cool pore +3, 1.25 warm wrinkle +2, 1.25 warm pore +2) | 2 | 10 |
| C | 2/3/1/3 | 0 of 16 | 0 | 2 |
| D | 2/3/1/2 | 4 of 16 (0.85 warm acne -3, 1.2 cool acne -3, 1.25 warm acne -3, 0.8 cool acne -3) | 1 | 2 |

Across the three folds 8 of 48 held-out matched readings fall outside a band fitted on the other two faces. That is the honest out-of-sample number: a band fitted on two faces is not guaranteed on a third, and with three faces the bands are only a rough guide. The shipped bands (wrinkle 2, pore 3, texture 2, acne 4) also include the acne jitter allowance, which is why they are a little wider than a pure two-face fit.


## Sensitivity to where the band is drawn

Same 48 readings (12 light changes x 4 concerns), skin unchanged, counted against the shipped bands and against bands 2 points wider (the largest held-out miss):

| | outside the shipped band | outside the band + 2 |
|---|---|---|
| as shot | 10 | 4 |
| after matching | 0 | 0 |

So 6 readings as shot are verdicts that depend on the band choice. That is why a change that clears the band by 2 points or less is now shown as **borderline** instead of better or worse (`samelight.BORDERLINE_MARGIN`). After matching nothing in this set is outside either band, but the bands were fitted on this set, so that says little.
