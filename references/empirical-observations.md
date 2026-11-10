# Empirical observations of the S3NS API surface

Facts on this page come from probing the live S3NS (`s3nsapis.fr`) API surface, not from
the documentation. They complement the scraped docs. They never override them, except where
a functional test (a real call that succeeded or failed) says otherwise.

How to read an entry:

- Each entry is dated and states its evidence. The surface changes over time, so re-check
  anything older than a few months before relying on it.
- **Hypothesis** marks a conclusion the evidence suggests but does not prove.
- Project, organization and account identifiers are deliberately omitted.

Evidence strength, weakest first:

| Tier | What it proves | What it does not prove |
|------|----------------|------------------------|
| Schema (discovery document lists the method) | The universe publishes a document for the API | That the method is served |
| DNS (`<api>.s3nsapis.fr` resolves) | The API host is routed | That the service is available or offered |
| Liveness (unauthenticated or authenticated probe) | A handler exists behind the route | That the feature works end to end |
| Functional (a real call succeeds) | The feature works | Anything about other features |

## Discovery documents are often verbatim copies of public Google Cloud

**2026-07.** Of the 70 discovery documents S3NS served, **39 were exact copies** of the
public Google Cloud document (no method omitted) and 31 were tailored. `storage` was a copy.
`bigquery` (27 methods omitted), `cloudasset` (72) and `artifactregistry` (115) were tailored.

The S3NS `compute` document includes `globalForwardingRules.insert`, `globalAddresses` and
global `urlMaps`, while the Load Balancing differences page says global load balancers are
not available.

Documents also drift. The `pubsub` document was tailored (about 70 methods omitted), and a
later refresh served a full copy.

⇒ A method listed in an S3NS discovery document is **not** evidence that the method is
served. Use the `tpc-differences` pages, or a probe.

## DNS resolution proves routing, not availability

**2026-11-08.** These hosts resolve:

- `spanner`, `cloudbuild` and `cloudasset`, listed as **À venir** (upcoming) on PREMI3NS.
- `bigquerydatatransfer` and `bigquerydatapolicy`, which the BigQuery differences page lists
  as unavailable.
- `iamcredentials`. It did not resolve in July 2026.

A random control name (`<random>.s3nsapis.fr`) returns NXDOMAIN, so this is not a wildcard
record.

⇒ NXDOMAIN means the API is absent. A resolving host means only that it is routed.

## Liveness status codes need a control probe

**2026-07.** Unauthenticated probes against real method URLs returned a mix of codes, not a
blanket response. Examples: `storage.objects.compose` returned 400,
`storage.buckets.lockRetentionPolicy` returned 401, `bigquery.jobs.query` returned 400, and
the three `pubsub` methods probed returned 403.

| Status | Meaning |
|--------|---------|
| 400, 405 | The request reached a handler: strong sign the method is served |
| 401, 403 | Authentication gate: weak, because it may be a blanket gate. Compare with a control |
| 404 | Ambiguous on its own. Compare with a made-up method on the same host |
| 501, or a "not implemented" body | Not served |

The control probe is a made-up method path on the same host. If the real method answers
exactly like the control, treat it as not served.

## Anywhere Cache is not served

**Recorded 2026-11-08.** With valid credentials, `storage.anywhereCaches.get` and
`storage.anywhereCaches.list` return `404 route not found`. That is the same response as the
made-up control method on `storage.s3nsapis.fr`. No S3NS page mentions Anywhere Cache.

⇒ Treat Anywhere Cache as unavailable on S3NS, even though the `storage` discovery document
lists its methods.

## The offered-services list is scoped per organization

**2026-11-08, hypothesis.** One organization's `gcloud services list --available` returned
31 APIs. Every one maps to a **Qualifié SecNumCloud 3.2** service on PREMI3NS, or to platform
plumbing such as `cloudbilling`, `apikeys` or `essentialcontacts`. None of the 10 services
then marked **Qualification en cours** appeared: `run`, `bigtableadmin`, `file`,
`secretmanager`, `composer`, `dataproc`, `storagetransfer`, `aiplatform`, `cloudquotas`,
`accessapproval`. Yet the docs describe all 10 as available, and their hosts resolve.

The effective `gcp.restrictServiceUsage` org policy on that project is `allowAll: true`. So
an org policy is not what removes them. The scope is set outside the customer's org-policy
plane, possibly by the PREMI3NS contract or an opt-in for services still in qualification.
This is not confirmed.

Consistent with this, authenticated calls to `run` returned `401 token rejected` with a
token that other APIs accepted.

⇒ A service missing from one organization's `services list --available` is **not**
unavailable on S3NS. Check the docs and the PREMI3NS status, then ask the organization
administrator or S3NS whether the service is enabled for that organization.

## Signed URLs: HMAC works, V4 via `signBlob` is untested

**2026-07, functional.** `gcloud storage sign-url` with an HMAC key worked on an S3NS
machine. `storage.projects.hmacKeys.create` is served.

**2026-11-08.** The V4 path needs `iamcredentials.projects.serviceAccounts.signBlob`.
`iamcredentials` now resolves and PREMI3NS lists *Service Account Credentials* as qualified.
No functional test of V4 signing has been run yet.

## How to reproduce

```bash
# DNS: compare a real API host with a random control name
getent hosts run.s3nsapis.fr; getent hosts "zz$(date +%s).s3nsapis.fr" || echo NXDOMAIN

# Discovery document: compare method counts with public Google Cloud
curl -s 'https://storage.s3nsapis.fr/$discovery/rest?version=v1' | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["rootUrl"], len(json.dumps(d["resources"])))'

# Offered services for your organization, and the org policy that could restrict them
gcloud services list --available --project=PROJECT --format='value(config.name)'
gcloud org-policies describe gcp.restrictServiceUsage --project=PROJECT --effective
```
