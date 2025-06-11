# GitHub Secrets Setup Guide

## Required Secrets

You need to add the following secrets to your GitHub repository for the workflows to work:

### 1. QC_TOKEN
Your QuantConnect API token.

**Value:** `f6f5df71e9938e3c4eca2298528bcc383c2a5fad14283313ecb9d07c68463e78`

### 2. QC_ORG_ID  
Your QuantConnect organization ID.

**Value:** `c9d123ffc99a793105570496669ef511`

## How to Add Secrets

1. Go to your GitHub repository: https://github.com/Abdullah1172/option-automated
2. Click on **Settings** (in the repository navigation)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add each secret:
   - **Name:** `QC_TOKEN`
   - **Secret:** `f6f5df71e9938e3c4eca2298528bcc383c2a5fad14283313ecb9d07c68463e78`
   - Click **Add secret**
6. Repeat for the organization ID:
   - **Name:** `QC_ORG_ID`
   - **Secret:** `c9d123ffc99a793105570496669ef511`
   - Click **Add secret**

## Verify Secrets

After adding, you should see both secrets listed (values will be hidden):
- QC_TOKEN
- QC_ORG_ID

The workflows will now use these secrets instead of hardcoded values.