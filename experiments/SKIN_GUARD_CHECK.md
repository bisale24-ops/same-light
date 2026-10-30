# Skin-share guard check

Flat swatches, not faces: this checks that the colour test never calls a skin tone 'not skin', not that it works on real photos. Reading = what the app would do with the photo (ok / weak = warning / unreadable = no verdict).

| input | skin share of the crop | reading |
|---|---|---|
| Monk 1 #f6ede4 | 1.00 | ok |
| Monk 2 #f3e7db | 1.00 | ok |
| Monk 3 #f7ead0 | 1.00 | ok |
| Monk 4 #eadaba | 1.00 | ok |
| Monk 5 #d7bd96 | 1.00 | ok |
| Monk 6 #a07e56 | 1.00 | ok |
| Monk 7 #825c43 | 1.00 | ok |
| Monk 8 #604134 | 1.00 | ok |
| Monk 9 #3a312a | not applied (dark crop) | ok |
| Monk 10 #292420 | not applied (dark crop) | ok |
| grey wall | 0.00 | unreadable |
| white wall | 0.00 | unreadable |
| blue | not applied (dark crop) | ok |
| green | 0.00 | unreadable |
| red shirt | 0.00 | unreadable |
| black hair | not applied (dark crop) | ok |
| faceA (photo) | 0.83 | ok |
| faceB (photo) | 0.65 | ok |
| faceC (photo) | 0.90 | ok |
| faceD (photo) | not applied (dark crop) | ok |

Known limits: the darkest Monk tones (9 and 10) sit where colour cannot tell skin from dark hair, so the test is not applied there rather than allowed to refuse a face (the API itself refuses frames that are too dark). Bright non-skin colours near the skin hue (beige, wood) would pass as skin; the guard is a loose check, not a face detector.
