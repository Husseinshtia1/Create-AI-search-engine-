# سجل التجارب

## Synthetic/system experiments
G97 v2 تفوقت على TF-IDF في synthetic 3,000-doc setup؛ G97 v3 aggressive multiplication فشلت. Crawler v0 clever priority خسر أمام BFS 10/12 worlds؛ v1 refresh تلوثت hidden-quality oracle ورفضت؛ v2 BFS+refresh+recovery+conservative suppression هو design الحالي. Bundled query processing وconservative v1 فشلا، diagnosis-first v2 تحسن 29/30 worlds. Passage reranking انخفض ~1.8% nDCG فبقيت passages للsnippets.

## ADI
TF-IDF MAP 0.443025؛ PRF 0.424344؛ LSA40 0.409968؛ C96 0.373525. ARR forced routing فشل؛ selective gate تحسن هامشيًا ~0.15%.

## CACM
C96 MAP 0.320769؛ A6 ContextGraph 0.334000 (+4.12%)؛ bootstrap ΔMAP CI [+0.004559,+0.022965]. Global degree/recursive authority أدنى من baseline.

## CISI
C96 0.238474؛ global degree 0.229110؛ recursive global 0.230799؛ local coupling 0.240911 (+1.02%، CI crosses zero). Global variants negative significant.

## Cranfield
C96 MAP 0.182664؛ TF-IDF 0.289093. لا lexical baseline واحد مهيمن عالميًا.

## Cora
Text 0.287237 → local citation 0.292174 (+1.72%)، CI موجب؛ global variants سلبية قليلًا.

## Citeseer
Text 0.284816 → local citation 0.287093 (+0.80%)، CI موجب. Global variants تحسنت ضئيلًا، فرفضنا ادعاء `global always hurts`.

## WebKB v1
Cornell/Texas/Wisconsin pooled: Text 0.561372؛ raw local hyperlink 0.523075 (−6.82%). hyperlink ≠ topical corroboration.

## Washington v2
Text 0.580321؛ raw local 0.553640؛ link×lexical consistency 0.566208. qualification استعادت جزءًا من الضرر ولم تتفوق.

## v3 original HTML anchors/context
Text 0.566857؛ raw 0.555830؛ lexical-qualified 0.563424؛ anchor-only 0.565657؛ combined neighborhood 0.564641. More evidence لم يكن أفضل.

## v4 misc holdout
Text 0.458778؛ Anchor-All 0.458758؛ gated v4 0.458764. FAILED. q90 ties جعلت intended 10% gate تسمح 41.2% contributions.

## v5 exact budget
Text 0.564081؛ Anchor-All 0.563634؛ Exact Budget 0.563739؛ 33 wins/322 losses للحالات المتغيرة. FAILED.

## v6 external-description rescue
Anchor وجدت relevant docs خارج body depth، لكن budget-matched Hybrid خسر أمام deeper body عند K=10/20/50. General rescue FAILED.

## v7
Handwritten gate: Recall@30 0.244735→0.241782؛ 3 wins/69 losses. FAILED.

## v7 predictability
LOUO AUC 0.7436؛ per-university 0.7007–0.8025؛ top10% precision 32.63% مقابل prevalence 12.78%. benefit قابلة للتنبؤ جزئيًا لكن natural score>0 policy أضرت baseline.

## v8 risk calibration
Body Recall@30 0.244735؛ v8 0.244801؛ Δ +0.000066؛ gate ~2.59%. **WEAK POSITIVE / NOT EXTERNALLY VALIDATED**.

## Curlie
Protocol frozen: published test split؛ 20,000 smallest-SHA1 UIDs؛ no balancing/density filtering؛ budget30؛ WebKB-only controller؛ labels بعد rankings/features؛ feasibility ≥1000 inbound targets. أي parser-only corrections تسجل ولا تعد results.
