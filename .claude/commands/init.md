Initialize project-specific Cursor configuration by analyzing the codebase.

## Your Task

Analyze this project and populate the TODO sections in .cursor/ files.

## Steps

### 1. Detect Stack & Framework

Identify the tech stack beyond just language:

**Languages**: Check for package.json (JS/TS), Pipfile/pyproject.toml (Python), go.mod (Go), Cargo.toml (Rust)

**Frameworks**: Look for framework-specific files and imports:

- Web: Next.js, React, FastAPI, Django, Express, Flask, Gin
- Testing: Jest, pytest, Vitest, Go testing
- ORM: Prisma, SQLAlchemy, TypeORM, GORM
- Infrastructure: CDK, Terraform, Pulumi, Serverless Framework

**Cloud Provider Detection** (check ALL of these):

- SDK dependencies: `aws-sdk`, `@aws-sdk/*`, `@google-cloud/*`, `@azure/*`
- Infrastructure dirs: `terraform/`, `cdk/`, `pulumi/`, `infrastructure/`
- Docker/K8s configs: GCR, ECR, ACR references in Dockerfiles or k8s manifests
- Config files: Look for cloud-specific env vars or service references

Always include detected cloud providers in the summary output.

### 2. Detect Architecture Pattern

Look for structural patterns:

- **Monorepo**: workspaces in package.json, packages/, apps/ directories
- **Serverless**: Lambda handlers, serverless.yml, SAM templates
- **Layered**: handlers/ → services/ → repositories/ or similar
- **Microservices**: Multiple service directories with separate configs

**Important**: If monorepo detected, identify each sub-project and its framework. This affects Step 6.

### 2b. Detect Publishable Packages

Look for independently versioned packages within the repo that are published to package registries:

**Detection signals:**

- Nested \`package.json\` files with \`publishConfig\` (NPM registry URL)
- Packages with \`@org/package-name\` naming convention
- Separate \`version\` fields in nested package.json files
- \`files\` field indicating what gets published
- Packages in \`packages/\`, or sub-directories with their own package.json

**For each publishable package, capture:**

- Package name (e.g., \`@acme/shared-types\`)
- Current version
- Path within repo
- Known consumers (other sub-projects or external)
- Build/publish commands

**Why this matters for the agent:**

1. **Impact awareness** - Changes to shared packages affect consumers outside this repo
2. **Version coordination** - Know when to bump versions before consumers can use changes
3. **Correct imports** - Use published package name (\`@org/pkg\`) vs local relative paths
4. **Build order** - Sub-packages may need to build before the main app
5. **Breaking change detection** - Highlight when changes might break downstream

**Output format for ## Packages:**

\`\`\`

## Packages (Publishable NPM Modules)

| Package         | Version | Path                 | Consumers              |
| --------------- | ------- | -------------------- | ---------------------- |
| \`@org/types\`  | 1.2.3   | \`packages/types/\`  | app, external services |
| \`@org/shared\` | 2.0.0   | \`packages/shared/\` | app, other-repo        |

### When modifying publishable packages:

1. Breaking changes require major version bump and coordination
2. Build sub-packages before main app if locally linked
3. Use \`@org/package-name\` imports, not relative paths
   \`\`\`

### 3. Discover Commands (CI-Prioritized)

First check CI/CD for required commands:

- `.github/workflows/*.yml` - GitHub Actions
- `Jenkinsfile`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`

Commands that run in CI are **required checks**. Other scripts are **development conveniences**.

Then check package managers: package.json scripts, Pipfile scripts, Makefile targets, pyproject.toml

**Output format for ## Commands:**

```
### Required (CI checks)
- `npm run typecheck` - TypeScript compiler
- `npm run lint` - ESLint
- `npm run test` - Jest unit tests

### Development
- `npm run dev` - Local dev server
- `npm run test:watch` - Tests in watch mode
```

### 4. Document Structure

Identify key directories and their purpose.

**Output format for ## Structure:**

```
- `app/` - Python source code (FastAPI)
  - `handlers/` - API route handlers
  - `services/` - Business logic
  - `repositories/` - Database access
- `tests/` - pytest tests
- `infrastructure/` - CDK infrastructure code
```

### 5. Find Canonical Patterns

Find 2-3 files that exemplify project patterns. Prefer files that:

- Have good structure and comments
- Demonstrate error handling
- Show testing patterns
- Are representative of the codebase style

**Also look for utility functions** that wrap common operations:

- Search `utils/`, `helpers/`, `lib/`, `common/` directories
- Look for functions that are imported across multiple files
- Examples: API wrappers, validation helpers, logging utilities, error handlers
- These are "must use" code - the agent should know about them to avoid reinventing

**Why utilities matter:** When a utility exists for a common operation, the agent should use it instead of writing custom code. Undocumented utilities lead to inconsistent implementations and debugging cycles.

**Output format for ## Patterns:**

```
- Handler pattern: `app/handlers/study_handler.py` (lines 1-50)
- Test pattern: `app/tests/test_study_service.py`
- Service pattern: `app/services/study_service.py`
- Utility: `app/utils/api_client.py` - wraps external API calls with retry logic
```

Note: Database-specific utilities (migrations, triggers, audit) are covered in more detail in Step 8.

### 6. Create Project Rules (Context-Efficient)

**Critical principle**: Only load patterns relevant to the file being edited. Minimize context waste.

#### For Single-Project Repos

Create `rules/_project-{lang}.mdc` with language globs:

```yaml
---
description: Python patterns for this project
globs: **/*.py
---
```

#### For Monorepos (Multiple Sub-Projects)

> **CRITICAL**: Scope globs by directory path, not file extension. `**/*.ts` matches ALL TypeScript files across all projects. Use `apps/api/**/*.ts` to target only the backend.

Create **separate rule files per sub-project**, scoped by directory:

```yaml
# rules/_project-backend-api.mdc
---
description: NestJS backend patterns
globs: apps/api/**/*.ts
---
# Only NestJS patterns here (entities, services, controllers)
```

```yaml
# rules/_project-frontend.mdc
---
description: React frontend patterns
globs: apps/web/**/*.ts,apps/web/**/*.tsx
---
# Only React patterns here (components, hooks, state)
```

**Naming convention**: `_project-{descriptive-name}.mdc`

- `_project-backend-api.mdc` (not `_project-typescript.mdc`)
- `_project-frontend-web.mdc` (not `_project-react.mdc`)

**Content per rule file**:

- Framework-specific patterns for THAT sub-project only
- Project-specific conventions observed in THAT directory
- Reference to code style configs used by THAT sub-project

### 7. Verify MCP (Optional)

The default mcp.json includes the official Atlassian Rovo MCP Server.
If the project uses Jira/Confluence, remind the user to authenticate via browser on first use.

### 8. Detect Local Development Environment

Identify how local services are set up and how to interact with them at runtime.

**Detection signals (check in priority order):**

1. **README.md** - Often the most accurate source for local setup
2. **Package.json scripts** - Look for `start:dev`, `db:*`, `docker:*` scripts
3. **Config directories** - `config/`, settings files with connection info
4. **Docker Compose files** - May be outdated, cross-reference with README
5. **Environment files** - `.env.example` for connection patterns

**Important**: Config files (especially Docker Compose) can be outdated. Cross-reference multiple sources and prefer README instructions.

**What to document:**

1. **Database access**: How to connect locally (e.g., `psql -d dbname`, `mysql -u root`)
2. **Running services**: What needs to be running (local Postgres, Redis, Docker, etc.)
3. **Environment setup**: Required env vars or setup steps

**Why this matters:**

During planning, the agent can query the actual database to verify assumptions about schemas, triggers, constraints, etc. This prevents bugs from incorrect assumptions.

**Output format for ## Local Development (if detected):**

```
## Local Development

### Services (source: README / verified)
- PostgreSQL: local install
- Redis: local install

### Database Access
- Dev DB: `psql -d myapp` or `PGDATABASE=myapp psql`
- Test DB: `PGDATABASE=myapp_test psql`

### Verification Queries (for planning)
- Schema: `\d tablename`
- Triggers: `SELECT tgname FROM pg_trigger WHERE tgrelid = 'schema.table'::regclass`
- Functions: `SELECT proname, prosrc FROM pg_proc WHERE proname LIKE 'pattern%'`
```

### 9. Detect Database Patterns (extends Step 8)

For projects with databases (detected via ORM in Step 1), identify migration patterns and database-specific utilities that affect schema changes.

**Detection signals:**

- Migration directories: `migrations/`, `db/migrate/`, `alembic/`, `prisma/migrations/`
- Multiple ORMs in same project (common in hybrid/legacy codebases)
- Database utilities in `utils/`, `scripts/`, `lib/`, `helpers/`
- Audit/history patterns: `*_audit`, `*_history`, `*_versions` tables

**What to document:**

1. **Migration commands**: Which command(s) run migrations? Document ALL of them if multiple exist.
2. **Custom utilities**: Search for helpers that wrap common DB operations (audit trails, soft deletes, triggers, seeds)
3. **Test database**: Is there a separate test DB? Different migration command for tests?
4. **Schema change patterns**: Any conventions that require extra steps beyond basic migrations

**Why this matters:**

Database schema changes are high-risk. Projects often have custom utilities or conventions (e.g., trigger helpers, audit table generators) that MUST be used for certain operations. If undocumented, the agent will write manual SQL that conflicts with existing patterns, causing debugging cycles.

**Key principle**: When utilities exist for common operations, document them so the agent uses them instead of reinventing.

**Output format for ## Database Migrations (if patterns detected):**

```
## Database Migrations

### Commands
- [primary migration command] - [which ORM/what it does]
- [secondary command if exists] - [when to use it]
- [test migration command if different]

### Utilities (if any custom helpers exist)
- [utility name]: [path] - [when to use it]

### Schema Change Patterns (if any non-obvious conventions)
- [pattern]: [what extra steps are required]
```

### 10. Add Exploration Pointers

Add a brief "Exploration" section to workspace.mdc that teaches WHERE to look at runtime, not pre-documented facts. Emphasize verification — docs may be stale, code is truth.

**Output format for ## Exploration:**

```
## Exploration

When you need to understand:
- **Why a decision was made** → Check `docs/adr/` or `docs/` first, then verify against code
- **How a feature works** → Find similar in Patterns section, READ the actual code
- **What entities exist** → Check models/ORM definitions in [path]
- **Service integrations** → Check infrastructure code or event handlers
- **Environment setup** → README.md, but verify commands still work

**Verification rule**: Docs may be outdated. Always confirm against actual code before relying on documentation claims.
```

This teaches exploration without bloating context, and reinforces the "verify before trusting" mindset.

### 11. Detect Version Drift (Local ↔ Production)

Identify version discrepancies between local development environment and higher environments (staging/production) that could impact feature development.

**Why this matters:**

Features developed and tested locally may use capabilities unavailable in production due to version differences. This leads to:

- Tests passing locally but failing in CI/production
- Features breaking after deployment
- Wasted debugging time on version-specific behavior

**Detection approach:**

> **⚠️ CRITICAL: Version Detection Pitfalls**
>
> Do NOT blindly trust command-line version output. Common mistakes:
>
> 1. **Client vs Server versions** - Many tools have separate client and server binaries. For example, `psql --version` returns the PostgreSQL **client** version, which may differ from the database **server** version. Similarly for MySQL, Redis CLI, MongoDB shell, etc.
> 2. **User's installed version ≠ Project's expected version** - The developer running `/init` may have a different version installed than what the project expects. The goal is to document what the project **requires**, not what happens to be installed.
> 3. **README is the source of truth for local setup** - If README says `brew install postgresql@16`, that's the expected local version regardless of what `psql --version` returns.
>
> **Resolution priority:**
>
> 1. README setup instructions (e.g., `brew install postgresql@16` → local is v16)
> 2. Docker Compose for local dev (e.g., `image: postgres:16`)
> 3. Version manager files (`.nvmrc`, `.python-version`, `.ruby-version`, `go.mod`)
> 4. Only fall back to CLI commands if none of the above exist

#### Step 1: Detect Local Versions

For each detected technology, check local version. **Prioritize README documentation** over command output when there's a discrepancy:

| Technology    | Detection Method                            | Notes                                                                                      |
| ------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| PostgreSQL    | README first, then \`SELECT version()\`     | ⚠️ \`psql --version\` returns **client** version, not server. Check README for more info.` |
| MySQL         | README first, then \`mysql --version\`      |                                                                                            |
| MongoDB       | \`mongod --version\`                        |                                                                                            |
| Redis         | \`redis-server --version\`                  |                                                                                            |
| Node.js       | \`.nvmrc\` file or \`node --version\`       |                                                                                            |
| Python        | \`.python-version\` or \`python --version\` |                                                                                            |
| Ruby          | \`.ruby-version\` or \`ruby --version\`     |                                                                                            |
| Go            | \`go.mod\` go directive or \`go version\`   |                                                                                            |
| Elasticsearch | \`curl localhost:9200\`                     |                                                                                            |

**Important**: README setup instructions often specify the **intended** version (e.g., `brew install postgresql@16`). This is more reliable than detecting the user's current installed version, which may differ. So you should always compare both and infer the correct version, if unclear ask the user for clarification.

**Note**: If a service is not installed locally, skip it. Focus on technologies actually used by the project (detected in Step 1).

#### Step 2: Search for Production Version Hints

Scan these sources for version indicators (in priority order):

1. **Infrastructure as Code** (most reliable)
   - \`terraform/\*.tf\` - RDS engine_version, ElastiCache engine_version
   - \`cdk/\`, \`pulumi/\` - similar version parameters
   - \`cloudformation/\*.yaml\` - EngineVersion properties

2. **CI/CD Configuration**
   - \`.github/workflows/\*.yml\` - container images, setup actions with versions
   - \`.gitlab-ci.yml\`, \`Jenkinsfile\`, \`bitbucket-pipelines.yml\`
   - Look for: \`image:\`, \`uses:\`, \`node-version:\`, \`python-version:\`

3. **Dockerfiles**
   - \`Dockerfile\`, \`Dockerfile.prod\`, \`docker/\*.Dockerfile\`
   - \`docker-compose.prod.yml\`, \`docker-compose.staging.yml\`
   - Look for: \`FROM postgres:14\`, \`FROM node:18-alpine\`

4. **Deployment Documentation**
   - \`README.md\`, \`docs/deployment.md\`, \`CONTRIBUTING.md\`
   - Look for explicit version requirements or constraints

5. **Environment Files**
   - \`.env.production.example\`, \`.env.staging\`
   - May contain version hints in comments or variable names

**Important**: Version hints are just that—hints. The agent should note confidence level:

- **High confidence**: IaC with explicit version (e.g., \`engine_version = "14.9"\`)
- **Medium confidence**: CI/Docker images (e.g., \`FROM postgres:14\`)
- **Low confidence**: Documentation or env file comments

#### Step 3: Document Discrepancies with Impact

For each technology where local version > production hint, research feature differences:

| Common Version Gaps | Impact Examples                                    |
| ------------------- | -------------------------------------------------- |
| PostgreSQL 16 vs 14 | No MERGE, JSON_TABLE, enhanced JSON path           |
| PostgreSQL 15 vs 13 | No MERGE, logical replication improvements         |
| Node.js 22 vs 18    | No native fetch stability, test runner differences |
| Node.js 20 vs 16    | No native fetch, different ESM handling            |
| Redis 7 vs 6        | No Functions, GETEX, ACL improvements              |
| Python 3.12 vs 3.9  | No match statement, no tomllib                     |
| MySQL 8.0 vs 5.7    | Window functions, CTEs, JSON improvements          |

**Output format for ## ⚠️ Version Drift (Local ↔ Production):**

```
## ⚠️ Version Drift (Local ↔ Production)

Version differences between local development and higher environments that may impact feature development.

| Technology | Local | Production Hint | Source | Confidence |
|------------|-------|-----------------|--------|------------|
| PostgreSQL | 16 | 14 | \`terraform/rds.tf:23\` | High |
| Node.js | 22 | 18 | \`.github/workflows/ci.yml:15\` | Medium |
| Redis | 7.2 | 6.2 | \`docker-compose.prod.yml:8\` | Medium |

### Feature Constraints

**PostgreSQL (local 16, prod 14):**
- ❌ MERGE statement (v15+) - use INSERT ON CONFLICT instead
- ❌ JSON_TABLE (v16+) - use jsonb_to_recordset instead
- ⚠️ Test migrations against v14 before deploying

**Node.js (local 22, prod 18):**
- ⚠️ Native fetch available but verify behavior matches
- ❌ Built-in test runner stability (v20+)
- Check node:* imports compatibility

**Redis (local 7.2, prod 6.2):**
- ❌ Redis Functions (v7+) - use Lua scripts instead
- ❌ GETEX command (v6.2.0+) - verify exact prod version
- ACL syntax differences

### Development Guidelines
1. When using version-specific features, check this table first
2. Test database migrations against the production version locally if possible
3. If uncertain about a feature's availability, check official docs for version introduced
4. Consider adding CI step to test against production versions
```

**If no version drift detected:**

```
## ⚠️ Version Drift (Local ↔ Production)

No version discrepancies detected between local and production environments.

Production version hints not found for: [list technologies where hints couldn't be determined]

If you know the production versions, add them manually.
```

## Output

Summarize what was discovered:

- Stack: [language] + [framework] + [testing]
- Cloud/Infra: [cloud providers detected] + [IaC tool if any]
- Architecture: [pattern] (if monorepo, list sub-projects detected)
- Publishable packages: [list any @org/package-name packages found]
- Local development: [how to access local DB, required services]
- Version drift: [any discrepancies found between local and production]
- Key commands: [list required checks]
- Files updated: workspace.mdc, list each \_project-\*.mdc created with its scope

**Important**:

- If cloud providers are detected, add a "## Cloud Infrastructure" section to workspace.mdc
- If publishable packages are detected, add a "## Packages" section documenting them with version, path, and consumers
- If local dev environment is detected, add a "## Local Development" section with DB access commands
- If database/audit patterns are detected, add a "## Database Migrations" section with utilities and checklists
- If version drift is detected, add a "## ⚠️ Version Drift (Local ↔ Production)" section with feature constraints
