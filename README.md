# G97 Search Research Release v0.1

**مشروع بحثي/هندسي لإعادة اشتقاق محرك بحث ويب كامل تحت قيد معرفي تاريخي ينتهي في 31 ديسمبر 1996.**

هذا الإصدار يجمع نتيجتين في حزمة واحدة:

1. **Research Ledger**: جميع التجارب التي أجريناها، الناجحة والفاشلة، مع حدود الاستنتاج والمنهجية ومصادر البيانات.
2. **Reference Engine**: تنفيذ Python قابل للتشغيل لمعمارية G97 الحالية: parsing/canonicalization، lexical retrieval، delta index، external anchor descriptions، query-local graph corroboration كميزة تجريبية، selective intervention controller، snippets، CLI وHTTP serving.

> لا يدّعي هذا الإصدار أن G97 يتفوق على Google أو أن جميع مكوناته جديدة. بعض الأفكار لها prior art واضح قبل 1997. القيمة الحالية للمشروع هي في **إعادة البناء المنهجي، الاختبارات المجمدة، فصل أدوار الأدلة، وتطوير مبدأ حماية baseline عبر تدخل انتقائي محسوب المخاطر**.

## البدء السريع

```bash
python -m pip install -e .
python -m g97 demo_docs.jsonl search "distributed database" -k 3
python -m pytest -q
```

لتشغيل واجهة HTTP محلية:

```bash
python -m g97 demo_docs.jsonl serve --host 127.0.0.1 --port 8080
```

## القيد التاريخي

التاريخ الوهمي للتصميم: **1 يناير 1997**. لا يُسمح باستعمال معرفة ظهرت بعد **31 ديسمبر 1996** كمدخل تصميم. datasets الحديثة تستخدم كـretrospective validation فقط بعد تجميد الخوارزمية.

## النتيجة المركزية الحالية

> **Preserve a strong simple baseline; intervene only when observable evidence justifies intervention.**

وفي طبقة الويب:

> **Predict the benefit of changing the baseline, calibrate the risk, and allow NoAction to win.**

## محتوى الإصدار

- `g97/`: Reference Engine قابلة للتشغيل.
- `tests/`: invariant/runtime tests.
- `experiments/`: الأكواد الأصلية لجميع التجارب المجمدة والتطويرية والتشخيصية.
- `.github/workflows/`: workflows إعادة الإنتاج.
- `docs/`: المنهج، المصادر، النتائج، failures، prior art، المعمارية وخارطة التطوير.
- `results/summary.csv`: ملخص metrics.
- `manifest.json`: provenance/status.

## حالة Curlie

بروتوكول Curlie/Homepage2Vec الخارجي جُمّد قبل retrieval metrics: 20,000 UID من test split باختيار SHA1 deterministic، candidate budget=30، وv8 controller مجمد بالكامل من WebKB. feasibility/evaluation تبقى مسارًا منفصلًا؛ لا تُعامل أي نتيجة parser/graph ناقصة كدليل علمي.
