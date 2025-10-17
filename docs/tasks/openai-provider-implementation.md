# OpenAI Provider Implementation

## Overview
Implement full OpenAI provider support to enable using GPT-4, GPT-4o, and GPT-4o Mini models for job matching alongside Claude models.

## Current State
- ✅ OpenAIProvider class exists in `src/job_finder/ai/providers.py`
- ✅ Basic OpenAI API integration implemented
- ✅ Model configurations added to Firestore for all OpenAI models
- ✅ Config structure supports provider switching

## Implementation Tasks

### 1. Test OpenAI Provider
- [ ] Verify OpenAIProvider can connect to API
- [ ] Test with GPT-4o Mini (most cost-effective)
- [ ] Verify JSON response parsing works correctly
- [ ] Test error handling for rate limits and API errors
- [ ] Ensure max_tokens limits are respected

### 2. Update Configuration
- [ ] Verify OPENAI_API_KEY environment variable is set
- [ ] Test switching between Claude and OpenAI providers
- [ ] Verify model-specific settings work for OpenAI models
- [ ] Document environment variable requirements

### 3. Cost Tracking
- [ ] Implement token usage tracking for OpenAI calls
- [ ] Add cost estimation based on model pricing
- [ ] Compare costs between Claude and OpenAI models
- [ ] Add cost tracking to job match results

### 4. Model Selection Strategy
- [ ] Document when to use which model:
  - GPT-4o Mini: High volume, cost-sensitive (cheapest)
  - GPT-4o: Good balance of performance and cost
  - Claude Haiku: Fast, cost-effective alternative to GPT-4o Mini
  - Claude Sonnet: Better reasoning than GPT-4o
  - Opus/GPT-4: Complex analysis requiring best capabilities

### 5. Testing
- [ ] Write integration tests for OpenAI provider
- [ ] Test fallback behavior when API is down
- [ ] Test rate limiting handling
- [ ] Verify resume intake data generation with OpenAI models
- [ ] Compare output quality between Claude and OpenAI

### 6. Documentation
- [ ] Update README with OpenAI setup instructions
- [ ] Document API key configuration
- [ ] Add model comparison guide
- [ ] Update CLAUDE.md with provider selection guidance

### 7. Monitoring
- [ ] Add logging for provider selection
- [ ] Track success/failure rates per provider
- [ ] Monitor token usage and costs
- [ ] Alert on API errors or rate limits

## Model Pricing Reference

### OpenAI Models (as of 2025)
- **GPT-4o Mini**: $0.15/$0.60 per MTok (input/output) - Most cost-effective
- **GPT-4o (latest)**: $2.50/$10 per MTok - Good balance
- **GPT-4o**: $5/$15 per MTok - Older version
- **GPT-4 Turbo**: $10/$30 per MTok
- **GPT-4**: $30/$60 per MTok - Legacy, expensive

### Claude Models (as of 2025)
- **Haiku 3.5**: $1/$5 per MTok - Most cost-effective
- **Sonnet 3.5**: $3/$15 per MTok - Best balance
- **Opus 3**: $15/$75 per MTok - Highest capability

## Acceptance Criteria
- [ ] Can successfully analyze jobs with any configured OpenAI model
- [ ] Error handling works correctly for API failures
- [ ] Token usage and costs are tracked
- [ ] Documentation is complete and accurate
- [ ] Tests pass for OpenAI provider functionality

## Related Files
- `src/job_finder/ai/providers.py` - Provider implementations
- `src/job_finder/ai/matcher.py` - Job matching logic
- `config/config.yaml` - AI configuration
- `scripts/setup_firestore_config.py` - Firestore config setup

## Notes
- OpenAI API key must be set in environment variable `OPENAI_API_KEY`
- Consider using GPT-4o Mini for high-volume processing to minimize costs
- Claude Haiku and GPT-4o Mini have similar cost profiles - benchmark both
- Monitor rate limits - OpenAI and Anthropic have different rate limiting
