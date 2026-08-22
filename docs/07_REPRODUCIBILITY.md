# إعادة الإنتاج

```bash
python -m pip install -e .
python -m pip install -r requirements-dev.txt
pytest -q
python -m g97 demo_docs.jsonl search "distributed database"
```

كل experiment لها script/workflow مستقل يسحب dataset من المصدر المسجل ويولد artifact. لا توجد corpora كبيرة داخل repo. Pin versions/checksums/SHAs تستخدم حيث كانت مجمدة؛ qrels/labels لا تدخل scoring في frozen tests؛ bootstrap seeds ثابتة؛ PR bodies تحفظ preregistration؛ parser-only fixes تسجل.

Curlie firewall: controller من WebKB فقط، sample deterministic hash، لا balancing/density selection، feasibility منفصلة عن evaluation، وإذا graph غير كافية وفق gate المجمدة يفشل البروتوكول بدل توسيع العينة post-hoc.
