# سجل المصادر وكيف استُخدمت

| المصدر | الاستخدام | النزاهة |
|---|---|---|
| `lucene4ir/lucene4ir` | CACM corpus/qrels/common_words | ranking frozen before qrels |
| `GianRomani/CISI-project-MLOps` | CISI.ALL/QRY/REL | SHA1s + structure inspection قبل scoring |
| `oussbenk/cranfield-trec-dataset` | Cranfield | query-ID mapping تنسيق فقط |
| `tkipf/pygcn` | Cora content/cites | labels للتقييم فقط |
| `chenyazhen/pygcn_citeseer` | Citeseer | labels للتقييم فقط |
| Geom-GCN/WebKB mirrors | WebKB vectors/links | stress/holdout؛ labels بعد ranking |
| CMU WebKB original | raw HTML/anchors/neighborhood | development + same-family misc holdout |
| CMU Industry Sector | candidate external corpus | diagnostics فقط |
| Homepage2Vec/Curlie Figshare | external modern web validation | retrospective; frozen protocol |

## مصادر prior art/historical
- Jacques Savoy 1996, IP&M 32(2):155–170, DOI `10.1016/S0306-4573(96)85003-5`.
- O'Neil et al. 1996, LSM-tree, DOI `10.1007/s002360050048`.
- McBryan 1994, `GENVL and WWWW`.
- Weiss et al. HyPursuit 1996.
- HTML 2.0 / RFC 1866 (1995).
- Porter 1980؛ Rocchio 1971؛ Salton/Buckley 1990؛ Robertson 1990.

## كيف استُخدمت المصادر
1. **Design source**: فقط المنشور ≤1996 يلهم architecture/algorithm في المسار التاريخي.
2. **Benchmark source**: قد تكون حديثة، لكن لا تغيّر algorithm بعد النتائج.
3. **Prior-art source**: تمنع novelty overclaim.
4. **Operational mirror**: GitHub mirrors للحصول على bytes reproducible، مع checksums/SHAs حيث أمكن.

لا تعاد corpora الكبيرة داخل repo؛ workflows تسحبها من مصادرها، وعلى المستخدم مراجعة التراخيص للاستخدام التجاري.
