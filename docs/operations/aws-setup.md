# AWS setup roadmap

How to go from a blank AWS account to a monthly backup of this repo's data in
Amazon S3, and later (optional) to querying that data from Claude.

The backup itself is already built: `.github/workflows/backup-data.yml` runs on
the 2nd of every month, checks every cleaned file for changes
(`scripts/check_data_changes.py`), logs them in `datasets/changes/`, opens a
GitHub issue when something changed, and copies the data to S3. Until the steps
below are done, it does everything except the S3 copy.

| Phase | What you get | Time | Needed for the backup? |
|---|---|---|---|
| 0. Secure the account | Safe sign-in, a spending alert | ~30 min | Yes |
| 1. Create the bucket | A private, versioned place for the data | ~15 min | Yes |
| 2. Connect GitHub | The workflow can write to the bucket, with no stored keys | ~30 min | Yes |
| 3. Query layer (Athena) | SQL over the backed-up files | ~1 hour | No, later |
| 4. Claude connector | Claude can query the data in a Team project | a few days of build | No, later |

Throughout, replace `<ACCOUNT_ID>` (12 digits, top right of the AWS console) and
`<BUCKET>` with your own values. These steps use the **US East (Ohio)
`us-east-2`** region; any region works if you use it consistently.

---

## Phase 0: Secure the account

Do this once, before creating anything else.

1. **Decide who owns the account.** For K1C work, the account should belong to
   the organization: sign-up email on a shared K1C mailbox (not a personal
   address) and a K1C payment method, so access doesn't depend on one person.
2. **Protect the root user.** Sign in as root, then **Security credentials,
   Assign MFA device** (an authenticator app is fine). After this, use root only
   for billing and account-level settings.
3. **Set a budget alert.** **Billing and Cost Management, Budgets, Create
   budget, Monthly cost budget**, amount **$5**, alert emails to you and one
   colleague. Expected costs are well under $1 a month (see Costs below), so any
   alert means something unexpected is running.
4. **Create your everyday sign-in.** **IAM Identity Center, Enable**, then:
   - **Users, Add user** for yourself.
   - **Permission sets, Create**, choose the predefined **AdministratorAccess**.
   - **AWS accounts**, select the account, **Assign users or groups**, pick your
     user and that permission set.
   - Sign in through the access portal URL Identity Center gives you (bookmark
     it). Use this sign-in from now on, not root.
5. **Add alternate contacts.** **Account, Alternate contacts**: billing and
   security contacts at K1C.

## Phase 1: Create the bucket

In the console (signed in through Identity Center), region **us-east-2**:

1. **S3, Create bucket**
   - **Name:** something unique like `k1c-chicago-education-data` (bucket names
     are global; add a suffix if taken). This is `<BUCKET>`.
   - **Object Ownership:** ACLs disabled (the default).
   - **Block all public access:** on (the default). Leave it on.
   - **Bucket Versioning:** **Enable**. If a file is overwritten or deleted, the
     old version is kept.
   - **Default encryption:** SSE-S3 (the default).
2. **Add a cleanup rule for old versions.** Bucket, **Management, Create
   lifecycle rule**: name it `expire-old-versions`, apply to all objects, choose
   **Permanently delete noncurrent versions of objects**, **365 days** after they
   become noncurrent. Monthly folders are never overwritten, so they are kept;
   only replaced copies in `latest/` expire.

What the workflow will write:

```
s3://<BUCKET>/chicago-education-data/
  2026-11/                    one full copy per month (never changed afterwards)
    enrollment/data/clean/...
    five_essentials/data/clean/...
    yrbs/data/clean/...
    budget/data/clean/...
    reference/...
    datasets/changes/...       snapshot.json, CHANGELOG.md, latest_summary.md
  2026-12/
  latest/                     always mirrors main
```

## Phase 2: Connect GitHub to the bucket

GitHub signs in to AWS with a short-lived token (OpenID Connect), so no AWS keys
are stored in GitHub. The role below can only touch this one folder in this one
bucket, and only from this repo's `main` branch.

1. **Add GitHub as an identity provider.** **IAM, Identity providers, Add
   provider**:
   - Type: **OpenID Connect**
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
2. **Create the permissions policy.** **IAM, Policies, Create policy, JSON**, paste
   (with your bucket name), name it `chicago-education-data-backup-write`:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "ListTheBackupFolder",
         "Effect": "Allow",
         "Action": "s3:ListBucket",
         "Resource": "arn:aws:s3:::<BUCKET>",
         "Condition": { "StringLike": { "s3:prefix": ["chicago-education-data/*"] } }
       },
       {
         "Sid": "ReadWriteTheBackupFolder",
         "Effect": "Allow",
         "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
         "Resource": "arn:aws:s3:::<BUCKET>/chicago-education-data/*"
       }
     ]
   }
   ```

   `DeleteObject` lets `latest/` mirror files that were removed from the repo;
   versioning keeps a recoverable copy.
3. **Create the role.** **IAM, Roles, Create role, Custom trust policy**, paste:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
             "token.actions.githubusercontent.com:sub": "repo:mariamraheem/chicago-education-data:ref:refs/heads/main"
           }
         }
       }
     ]
   }
   ```

   Attach `chicago-education-data-backup-write`, name the role
   `github-chicago-education-data-backup`, and copy its **ARN**
   (`arn:aws:iam::<ACCOUNT_ID>:role/github-chicago-education-data-backup`).
   If the repo ever moves to a K1C GitHub organization, update the `sub` line.
4. **Tell the workflow where to go.** In GitHub: repo **Settings, Secrets and
   variables, Actions, Variables tab, New repository variable**, three times:

   | Name | Value |
   |---|---|
   | `AWS_ROLE_ARN` | the role ARN from step 3 |
   | `AWS_REGION` | `us-east-2` |
   | `S3_BUCKET` | `<BUCKET>` |

   These are not secrets (nothing here grants access by itself), so variables
   are fine.
5. **Test it.** **Actions, Back Up Data, Run workflow** (on `main`). When it
   finishes, the run page shows the change summary and "Copied to s3://...".
   Check the bucket in the S3 console for a `chicago-education-data/<this month>/`
   folder.

If the AWS sign-in step fails with "Not authorized to perform
sts:AssumeRoleWithWebIdentity", the trust policy's `sub` or `aud` line doesn't
match: check the repo name, branch and audience exactly.

**Phases 0 to 2 are all the backup needs.** The rest is for querying the data.

---

## Phase 3 (later): Query the backup with Athena

Athena runs SQL directly on files in S3, charged by data scanned.

1. **Results location.** Create a folder `athena-results/` in the bucket (or a
   second bucket). **Athena, Workgroups, primary, Edit**: set the query result
   location to `s3://<BUCKET>/athena-results/` and a **per-query data usage
   limit** of 1 GB as a guardrail.
2. **One folder per table.** Athena reads every file in a folder as one table,
   so files with different columns need separate folders. Before this phase,
   change the "Copy data to S3" step to also write
   `s3://<BUCKET>/tables/<file name>/<file>` for the files you want to query
   (the 5Essentials `long` files can share one folder because their columns match).
3. **Create a database and tables.** In the Athena query editor:

   ```sql
   CREATE DATABASE chicago_education;

   CREATE EXTERNAL TABLE chicago_education.yrbs_prevalence_long (
     geography string, year string, indicator string, indicator_label string,
     group_type string, `group` string, n string, pct string, se string,
     ci_low string, ci_high string, suppress string
   )
   ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
   LOCATION 's3://<BUCKET>/tables/yrbs_prevalence_long/'
   TBLPROPERTIES ('skip.header.line.count' = '1');
   ```

   Columns are declared as text because the CSV reader fails on blank numbers
   (some YRBS rows have no confidence interval); convert in queries with
   `TRY_CAST(pct AS double)`. A Glue crawler can create tables automatically,
   but writing them by hand keeps column types under your control.
4. **Test:**

   ```sql
   SELECT CAST(year AS int) AS year, TRY_CAST(pct AS double) AS pct
   FROM chicago_education.yrbs_prevalence_long
   WHERE geography = 'Chicago' AND indicator = 'qn26' AND group_type = 'Total'
   ORDER BY year;
   ```

## Phase 4 (later): Let Claude query the data

Claude can't read S3 or Athena directly. On a Claude Team plan it reaches outside
data through a **custom connector**: a remote MCP server that Claude calls.

- **What to build:** a small MCP server with read-only tools, for example
  `list_datasets`, `describe_table` and `run_query` (SELECT only, row-limited),
  running on AWS (Lambda behind a public HTTPS URL) with its own IAM role that
  can only run Athena queries and read `chicago-education-data/` and
  `athena-results/`.
- **Requirements from Claude:** the server must be reachable over the public
  internet; it can use OAuth or a fixed header (API key) for sign-in. Only a
  Team **Owner** or **Primary Owner** can add the connector to the organization;
  each member then connects it themselves and turns it on per conversation.
- **Check first:** confirm connectors are available inside Claude Projects for
  your plan before building around Projects.
- **Simpler alternative for public data:** the GitHub Pages site already serves
  every dashboard dataset as JSON under `/api/`. A connector (or plain Claude
  Project instructions listing those URLs) can read them without AWS. AWS is
  worth it once private data (Salesforce, survey responses) needs to be queried
  alongside the public data.

Claude documentation:
[custom connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp),
[using connectors](https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities).

---

## Costs (approximate; check current AWS pricing)

| Item | Usage | Rough monthly cost |
|---|---|---|
| S3 storage | ~80 MB added per month; ~1 GB after a year | a few cents |
| S3 requests | a few thousand uploads per month | a few cents |
| Athena (Phase 3) | about $5 per TB scanned; these files are megabytes | cents |
| Lambda (Phase 4) | light use stays within the free tier | ~$0 |

The $5 budget alert from Phase 0 will flag anything unexpected.

## Checklist

- [ ] Account owned by K1C (shared email, K1C billing)
- [ ] Root MFA on; root not used day to day
- [ ] $5 monthly budget alert
- [ ] Identity Center user for each person who needs access
- [ ] Bucket private, versioned, encrypted, with the 365-day version cleanup rule
- [ ] GitHub OIDC provider and `github-chicago-education-data-backup` role
- [ ] Repo variables `AWS_ROLE_ARN`, `AWS_REGION`, `S3_BUCKET`
- [ ] Manual run of **Back Up Data** succeeded and the month folder is in S3
