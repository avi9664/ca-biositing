# GitHub Deployment Fixes

## Summary

Fixed multiple issues in the GitHub Actions deployment workflows for both
staging and production environments.

## Issues Identified and Fixed

### 1. Missing `jq` Dependency

**Problem:** The `validate-deployment.sh` script uses `jq` to parse JSON output
from `gcloud` commands, but `jq` was not installed in the GitHub Actions runner
environment, causing validation failures.

**Fix:**

- Added automatic `jq` installation in the `validate-deployment.sh` script with
  fallback for different package managers
- Added explicit `jq` installation step in both `deploy-staging.yml` and
  `deploy-production.yml` workflows before the validation step
- Updated the jq query in the script to handle optional fields with `?` operator
  (`'.status.conditions[]?'`)

### 2. Missing Environment Variables

**Problem:** The deployment scripts (`cloud-migrate-ci.sh` and
`cloud-update-services.sh`) were not receiving critical environment variables
(`DEPLOY_ENV`, `GCP_REGION`, `GCP_PROJECT`) from the GitHub Actions workflows.

**Fix:**

- Updated both deployment workflows to explicitly pass environment variables to
  migration and service update steps
- Added environment variable definitions with proper defaults in the bash
  scripts
- Added debugging output to print environment variables for troubleshooting

### 3. Insufficient Error Handling and Debugging

**Problem:** The deployment scripts lacked visibility into what was happening
during execution, making it difficult to diagnose failures.

**Fix:**

- Added comprehensive logging to all deployment scripts
- Added echo statements to display:
  - Environment name
  - Image tags being deployed
  - GCP region and project
  - Image URLs being used
  - Progress messages for each step

## Files Modified

### Workflow Files

1. `.github/workflows/deploy-staging.yml`
   - Added `Install jq` step in `validate-deployment` job
   - Added environment variables to `run-migrations` job
   - Added environment variables to `update-services` job
   - Added debugging output for all deployment steps

2. `.github/workflows/deploy-production.yml`
   - Same changes as staging workflow

### Deployment Scripts

3. `scripts/validate-deployment.sh`
   - Added automatic `jq` installation with package manager detection
   - Fixed jq query to handle optional conditions with `?` operator
   - Added GCP_REGION environment variable support

4. `scripts/cloud-migrate-ci.sh`
   - Added explicit environment variable definitions with defaults
   - Added comprehensive logging and debugging output
   - Improved variable expansion and quoting

5. `scripts/cloud-update-services.sh`
   - Added explicit environment variable definitions with defaults
   - Added comprehensive logging for each service update
   - Improved variable expansion and quoting
   - Added success confirmation message

## Testing Recommendations

Before merging to main:

1. **Test in a feature branch PR first** to trigger the staging deployment
   preview
2. **Verify the following logs appear** in GitHub Actions:
   - Environment variable values printed correctly
   - `jq` installation succeeds
   - Service URLs are correctly resolved
   - Health checks pass within the timeout period
3. **Monitor Cloud Run logs** to ensure services start properly with the new
   images

## Environment Variables Reference

The following environment variables are now properly set:

| Variable      | Description                             | Default          | Source                 |
| ------------- | --------------------------------------- | ---------------- | ---------------------- |
| `DEPLOY_ENV`  | Target environment (staging/production) | `staging`        | Workflow env           |
| `GCP_REGION`  | GCP region for resources                | `us-west1`       | Workflow env           |
| `GCP_PROJECT` | GCP project ID                          | `biocirv-470318` | Workflow env           |
| `IMAGE_TAG`   | Docker image tag (commit SHA)           | `latest`         | Computed from workflow |

## Validation Script Improvements

The `validate-deployment.sh` script now:

1. Checks for `jq` availability and installs if missing
2. Uses safer jq queries with `?` operator for optional fields
3. Supports all three package managers: apt-get, yum, and homebrew
4. Provides clear error messages if installation fails
5. Has proper error handling with `set -euo pipefail`

## Next Steps

1. Commit these changes to your feature branch
2. Push to GitHub and create/update a PR to trigger CI/CD
3. Monitor the deployment workflow execution
4. If successful, merge to main for production deployment

## Rollback Plan

If issues persist:

1. Revert the workflow changes only, keeping script improvements
2. Manually trigger deployments using `workflow_dispatch`
3. Check Cloud Run logs and service health directly via GCP Console
4. Verify WIF authentication is working correctly

## Additional Notes

- All scripts now follow bash best practices with `set -euo pipefail`
- Environment variables have sensible defaults to prevent unset variable errors
- Logging is comprehensive enough to diagnose most deployment issues
- The fixes are backward compatible with manual script execution
