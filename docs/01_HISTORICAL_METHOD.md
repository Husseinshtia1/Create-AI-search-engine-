# القيد التاريخي والمنهج

## cutoff

a) تاريخ التصميم الافتراضي: 1 يناير 1997.  
b) آخر معرفة مسموحة: 31 ديسمبر 1996.  
c) أي dataset أو paper لاحقة يمكن أن تستخدم فقط للتحقق اللاحق، ولا يجوز أن تغيّر design frozen على نفس الاختبار.

## قواعد مقاومة hindsight

1. نتحقق من سنة كل مكون قبل إدخاله.
2. نثبت المعادلات/المعاملات قبل فتح qrels أو labels عندما يكون الاختبار validation.
3. إذا حدث bug تنفيذي قبل metrics، يسمح بإصلاح parser/IO فقط، مع تسجيل ذلك.
4. إذا ظهرت metric، أي تعديل بعدها يصنّف development وليس validation.
5. نحفظ failures وnegative results بنفس وضوح النجاحات.
6. لا نضبط lambda أو K على test corpus بعد رؤية النتائج.
7. لا نحول stress test تصنيفي إلى ادعاء ad-hoc IR.

## المعرفة المسموحة النموذجية

Salton/vector-space/TF‑IDF، probabilistic IR وBM-style normalization، Rocchio، Porter، Salton/Buckley، Robertson term selection، spelling pre-1997، LSA، proximity/passages، citation analysis وcoupling/co-citation، graph theory، robots.txt، crawling، LSM-tree 1996، distributed IR 1996، HTML anchors/reference hypertext.

## المعرفة المحجوبة عن التصميم

PageRank/Google اللاحق، HITS post-cutoff، neural embeddings/transformers، modern LTR، modern web-spam systems، knowledge graphs الحديثة.

## تصنيف الأدلة

- **FROZEN VALIDATION**: التصميم مثبت قبل labels/qrels/metric.
- **EXTERNAL REPLICATION**: corpus جديدة مستقلة عن corpus التي ولّدت الفكرة.
- **STRESS TEST**: task مساعدة لا تساوي ad-hoc search.
- **DEVELOPMENT**: corpus seen؛ آلية لا إثبات مستقل.
- **DIAGNOSTIC**: format/graph/feasibility بلا ranking claim.
- **FAILED**: الفرضية لم تتفوق أو خالفت شرطها.
