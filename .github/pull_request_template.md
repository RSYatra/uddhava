# Pull Request

## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Security fix
- [ ] Dependency update

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Related to #

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

## Testing Checklist

<!-- Mark completed items with an 'x' -->

- [ ] I have tested these changes locally
- [ ] All existing tests pass
- [ ] I have added new tests for new functionality
- [ ] I have tested edge cases and error scenarios
- [ ] I have tested with different user roles (if applicable)
- [ ] I have verified database migrations work correctly (if applicable)

## Code Quality Checklist

- [ ] My code follows the project's coding standards
- [ ] I have run `ruff format .` to format my code
- [ ] I have run `ruff check .` and fixed all issues
- [ ] I have run pre-commit hooks and all checks pass
- [ ] I have added docstrings to new functions/classes
- [ ] I have updated type hints where necessary
- [ ] I have removed debug statements and commented code

## Security Checklist

- [ ] No sensitive data (passwords, API keys, tokens) in code
- [ ] No hardcoded credentials or configuration
- [ ] Input validation is implemented for new endpoints
- [ ] Authentication/authorization is properly implemented
- [ ] SQL injection prevention measures are in place
- [ ] XSS prevention measures are in place (if applicable)

## Database Changes

<!-- If this PR includes database changes, provide details -->

- [ ] No database changes
- [ ] New migration created: `alembic/versions/XXXXXX_description.py`
- [ ] Migration tested locally
- [ ] Migration includes both upgrade and downgrade
- [ ] Data migration strategy documented (if applicable)

## API Changes

<!-- If this PR changes any API endpoints, provide details -->

- [ ] No API changes
- [ ] New endpoint(s) added
- [ ] Existing endpoint(s) modified
- [ ] Endpoint(s) deprecated/removed
- [ ] API documentation updated
- [ ] Backward compatibility maintained

## Deployment Notes

<!-- Any special instructions for deployment -->

- [ ] No special deployment steps required
- [ ] Environment variables need to be updated
- [ ] Database migration needs to be run
- [ ] Manual data cleanup required
- [ ] Service restart required
- [ ] Configuration changes required

### Deployment Steps

<!-- If special deployment steps are needed, list them here -->

1.
2.
3.

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved
- [ ] Potential performance impact (explain below)

## Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

**Impact:**


**Migration Path:**


## Screenshots/Videos

<!-- If applicable, add screenshots or videos to demonstrate changes -->

## Additional Context

<!-- Add any other context about the PR here -->

## Reviewer Notes

<!-- Any specific areas you want reviewers to focus on -->

---

## Pre-merge Checklist

<!-- To be completed by the reviewer -->

- [ ] Code review completed
- [ ] All CI checks passing
- [ ] No merge conflicts
- [ ] Documentation updated (if needed)
- [ ] Changelog updated (if applicable)
- [ ] Approved by required reviewers
