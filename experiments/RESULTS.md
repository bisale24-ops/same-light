# Light matching, all 12 cases

3 faces x 4 lights (exposure 0.8-1.25, warm and cool), skin unchanged in every case (only the light changed, programmatically). Score gap against the same face at its original light, YouCam Skin Analysis ui_scores (wrinkle, pore, texture, acne). `raw` = scanned as it comes, `matched` = after Same Light matches the light to the baseline. Noise bands: wrinkle 2, pore 3, texture 2, acne 4. Nothing removed.

| face | light | exposure gap | warmth gap | raw (wr/po/tx/ac) | matched (wr/po/tx/ac) | sum abs raw | sum abs matched | readings over band raw | readings over band matched |
|---|---|---|---|---|---|---|---|---|---|
| faceA | 0.85 warm | -0.14 | +0.07 | +4/+4/+3/+1 | +1/+1/+0/+0 | 12 | 2 | 3 | 0 |
| faceA | 1.2 cool | +0.18 | -0.07 | -3/-7/-5/+1 | +0/+3/+0/-2 | 16 | 5 | 3 | 0 |
| faceA | 1.25 warm | +0.25 | +0.05 | -1/+3/+1/-2 | +2/+2/+1/+0 | 7 | 5 | 0 | 0 |
| faceA | 0.8 cool | -0.21 | -0.07 | +5/-5/-1/+0 | +0/+1/+0/+1 | 11 | 2 | 2 | 0 |
| faceC | 0.85 warm | -0.14 | +0.07 | +0/+1/+1/+2 | +0/+0/+0/+2 | 4 | 2 | 0 | 0 |
| faceC | 1.2 cool | +0.18 | -0.06 | -1/+4/-1/+2 | +0/+0/+0/-1 | 8 | 1 | 1 | 0 |
| faceC | 1.25 warm | +0.26 | +0.07 | +0/-1/+0/-1 | +0/+1/-1/+2 | 2 | 4 | 0 | 0 |
| faceC | 0.8 cool | -0.22 | -0.06 | +0/+9/+1/+3 | +0/+0/+0/+0 | 13 | 0 | 1 | 0 |
| faceD | 0.85 warm | -0.15 | +0.07 | +1/+0/+1/+0 | +0/+0/+0/-3 | 2 | 3 | 0 | 0 |
| faceD | 1.2 cool | +0.17 | -0.05 | +0/-1/+0/-3 | +0/+0/+0/-3 | 4 | 3 | 0 | 0 |
| faceD | 1.25 warm | +0.26 | +0.06 | +0/+1/+0/-3 | +0/+0/+0/-3 | 4 | 3 | 0 | 0 |
| faceD | 0.8 cool | -0.23 | -0.05 | +0/-1/+0/+0 | +0/+0/+0/-3 | 1 | 3 | 0 | 0 |

**Totals over the 12 cases:** sum of absolute score gaps 84 raw against 33 matched (61% less); concern readings outside their noise band 10 raw against 0 matched, out of 48.

**Where matching did not help, or hurt** (a concern reading where the matched gap is larger than the raw gap):

- faceA, 1.2 cool, acne: raw +1, matched -2
- faceA, 1.25 warm, wrinkle: raw -1, matched +2
- faceA, 0.8 cool, acne: raw +0, matched +1
- faceC, 1.25 warm, texture: raw +0, matched -1
- faceC, 1.25 warm, acne: raw -1, matched +2
- faceD, 0.85 warm, acne: raw +0, matched -3
- faceD, 0.8 cool, acne: raw +0, matched -3

Read the over-band numbers with care: the noise bands were set from the largest matched gaps, so "0 matched readings over band" is true by construction and proves nothing. The fair comparison is the sum of absolute gaps (84 raw, 33 matched) and the 7 readings listed above where matching moved a score further than the light alone had (all inside their band; all but one on acne, whose score jitters by about 2 on identical re-encoded photos).

What this does not show: it is three faces and one kind of light change (a programmatic exposure and tint shift on one photo each), so it measures how well the matching undoes a known shift, not how it behaves with a real camera, a real room, makeup, shadows or a changed pose. A fourth face was refused by the API (face too small in frame). The earlier headline, 40 points of fake change cut to 13, came from the four cases measured first (`normalise.json`); this table is the full set of twelve measured later and replaces it as the number to quote: 84 points of gap cut to 33.
