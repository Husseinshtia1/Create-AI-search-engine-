# الملخص التنفيذي

## الهدف
السؤال البحثي: إذا قُيد ذكاء اصطناعي قوي بكل ما كان متاحًا حتى 31 ديسمبر 1996، هل يمكنه إعادة اشتقاق محرك بحث ويب كامل ثم اختباره علميًا؟ لا ندعي عمى معرفيًا حقيقيًا؛ نستخدم formal cutoff ونمنع المعرفة اللاحقة من أن تكون design input.

## ما بُني
`Discovery → Crawl → Parse → Canonicalize → Archive → Delta/Main Index → Query Diagnosis → Candidate Retrieval → Evidence Roles → Intervention Controller → Ranking → Snippets → Serving → Evaluation`.

## النتيجة المركزية
- Query-local scholarly relations أعطت gains في CACM/CISI/Cora/Citeseer، لكن raw web hyperlinks فشلت على WebKB.
- Anchor text مفيدة كExternal Description لكنها noisy ولا تنجح كboost أو candidate rescue عام.
- OOF benefit prediction وصلت AUC≈0.7436؛ risk calibration v8 حفظت baseline تقريبًا وأعطت weak positive فقط.
- المبدأ الحالي: **Preserve a strong baseline; predict intervention benefit, calibrate risk, and allow NoAction to win.**

## أرقام محورية
CACM ContextGraph +4.12% MAP مع CI موجب؛ CISI local +1.02% غير حاسم بينما global variants سلبية significant؛ Cora local +1.72%؛ Citeseer +0.80%؛ WebKB raw local links −6.82%; v8 Recall@30 0.244735→0.244801 (غير validated خارجيًا).

## حدود الادعاء
لا ندعي التفوق على Google، ولا novelty للanchor indexing أو links+text أو coupling/co-citation أو selective feedback. الفرضية الأضيق التي تستحق مزيدًا من prior-art/validation هي evidence-role-aware bounded interventions controlled by expected benefit/risk with a baseline-preserving NoAction default.
