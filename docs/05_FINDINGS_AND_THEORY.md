# النتائج النظرية الحالية

1. **Global prestige غير مستقرة**: سلبية في CACM/CISI/Cora، إيجابية ضئيلة في Citeseer؛ إذن ليست signal عامة موثوقة.
2. **Query-local relation تحتاج semantics مناسبة**: citation/coupling/co-citation موجبة الاتجاه 4/4 scholarly experiments؛ raw web hyperlinks فشلت.
3. **Anchor text External Description وليست Authority**، لكن هذه prior art قديمة؛ contribution المحتملة ليست بناء anchor index.
4. **Complementarity لا تعني utility**: anchor وجدت relevant hits جديدة لكن noise جعل equal-budget hybrid أسوأ من deeper body.
5. **Benefit prediction ممكنة مبدئيًا**: OOF AUC≈0.744، لكن decision calibration هي المشكلة.
6. **NoAction action أصلية**: `a*=argmax E[Gain]-Risk` مع baseline unchanged خيارًا حقيقيًا.
7. **Evidence Roles**: `E_B` body، `E_X` external description، `E_R` relational corroboration، `E_A` authority؛ لا تُخلط دائمًا في scalar واحد.
8. prior art يمنع ادعاء novelty في links+text، coupling/co-citation، anchor indexing، selective feedback، content-link clustering، mixtures العامة.

الفرضية الأضيق التي ما زالت تستحق البحث: **bounded query-conditioned evidence roles + benefit/risk calibrated intervention with baseline-preserving NoAction default**. ليست novelty claim بعد.
