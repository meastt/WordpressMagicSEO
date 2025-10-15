# State Persistence Setup for Vercel

## Problem
Vercel serverless functions don't have persistent file storage. The `/tmp` directory is ephemeral and gets wiped between function invocations, causing state to be lost.

## Solution
Use GitHub Gists as persistent storage for state files.

## Setup Instructions

### 1. Create GitHub Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `gist` scope
3. Copy the token

### 2. Set Environment Variables in Vercel
Add these environment variables to your Vercel project:

```
GITHUB_TOKEN=your_github_token_here
GIST_ID_PHOTOTIPSGUY_COM=new
GIST_ID_GRIDDLEKING_COM=new
GIST_ID_TIGERTRIBE_NET=new
```

### 3. How It Works
- First run: Creates a new GitHub Gist for each site
- Subsequent runs: Updates the existing Gist with current state
- State persists between Vercel deployments and function invocations

### 4. Manual Gist Creation (Alternative)
If you prefer to create Gists manually:

1. Go to https://gist.github.com
2. Create a new private Gist named `{site_name}_state.json`
3. Copy the Gist ID from the URL
4. Set `GIST_ID_{SITE_NAME}=gist_id` in Vercel environment variables

## Example Gist URLs
- `https://gist.github.com/username/abc123def456` → Gist ID: `abc123def456`

## Benefits
- ✅ Persistent storage across Vercel deployments
- ✅ No database setup required
- ✅ Free GitHub Gists
- ✅ Version history in GitHub
- ✅ Private by default

## Fallback
If GitHub Gist is not available, the system falls back to local file storage (for development).
