---
name: access-fpt-cloud
description: Connect to the FPT Cloud serverless GPU (2x H100 80GB) via SSH for quick GPU jobs.
---

# FPT Cloud Serverless GPU (2x NVIDIA H100 80GB)

## When to use

Use for quick jobs — short experiments, verifying a single result, or testing a small script on GPU hardware.

## Quick connect (existing container)

```bash
ssh root@tcp-endpoint.serverless.fptcloud.com -p 34919 \
    -i ~/.ssh/id_rsa -o ProxyJump=none -o StrictHostKeyChecking=no
```

If the connection is refused, the container may have been deleted or the port may have changed. Follow the steps below to create a new one.

## FPT AI Factory website & credentials

- **Website:** https://ai.fptcloud.com
- **Username:** `retreat2026`
- **Password:** `Retreat@2026`

## If the account balance is exhausted

1. Go to https://ai.fptcloud.com
2. Sign in, or create a new account if needed.
3. Open **Billing**.
4. Apply referral code: `SIVAREDDYPROF-BNI8WX1W5X`
5. Once the credit is added, start using FPT AI Factory services.

## Creating a new GPU container

1. Log in at https://ai.fptcloud.com
2. Go to **GPU Container** → **Create Container**.
3. Select the **2x H100** option.
4. Change the template to **NVIDIA PyTorch**.
5. In the **SSH terminal access** section, add the user's SSH public key (from `~/.ssh/id_rsa.pub`).
6. Set **Volume capacity** to `300GB` and **Workspace path** to `/workspace`.
7. Click **Create Container**.

## Getting the SSH command for a new container

1. Go to **GPU Container** from the sidebar.
2. Open the newly created container.
3. Copy the SSH connection command. It will look like:

```bash
ssh root@tcp-endpoint.serverless.fptcloud.com -p <PORT> -i ~/.ssh/id_rsa
```

Add `-o ProxyJump=none -o StrictHostKeyChecking=no` if needed.
