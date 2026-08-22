# خطة المحرك الإنتاجي — جميع الجوانب

## Crawler/Networking
workers، DNS cache، connection reuse، per-host queues، robots، retries/backoff، redirects، MIME/size/time limits، decompression controls.

## Canonicalization
scheme/host/default ports/fragments، query preserved by default، redirect canonical map، URL fingerprint.

## Parsing/Dedup
Title/body/anchor/meta، charset، outgoing context، exact hash + near-duplicate fingerprint planned، representative clusters دون حذف provenance.

## Storage
raw archive، parsed store، immutable index segments، link/anchor stores، frontier state، experiment registry.

## Ranking
strong lexical baseline عبر dev لا test؛ evidence roles منفصلة؛ graph bounded؛ interventions logged.

## Freshness
observed change/staleness/importance بلا hidden oracle؛ delta يجعل الجديد searchable قبل popularity.

## Serving
broker→shards→replicas→topK merge؛ caches؛ circuit breakers؛ degraded partial results.

## Observability
crawl success/errors، queue depths، segment age/merge debt، query p50/p95/p99، cache hit، intervention rate، freshness/reach latency.

## Security
SSRF controls، block private/link-local، redirect/body/decompression limits، HTML untrusted/no script execution، output escaping، rate limits، robots/takedown.

## Governance
source URL/timestamp/hash، deletion/reindex، dataset/license registry، frozen research data منفصلة عن product feedback.

## Modes
Research mode يحافظ algorithmic cutoff ≤1996 مع modern plumbing فقط. Product mode يسمح current protocol/security/runtime، وكل post-1996 algorithm يوسم ويستبعد من historical claims.
