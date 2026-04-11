---
name: access-gpu-sandbox
description: Access the McGill-NLP shared GPU sandbox (8x RTX A6000, 384GB VRAM) for larger GPU jobs.
---

# GPU Sandbox (8x NVIDIA RTX A6000, 384GB VRAM)

## SSH Key

This skill has its own SSH key pair stored in `.ssh/` within the skill directory:
- Private key: `${CLAUDE_SKILL_DIR}/.ssh/id_rsa`
- Public key: `${CLAUDE_SKILL_DIR}/.ssh/id_rsa.pub`

## Connecting

```bash
ssh -p 2222 sandbox@ec2-35-182-158-243.ca-central-1.compute.amazonaws.com -i ${CLAUDE_SKILL_DIR}/.ssh/id_rsa
```

To run a command directly:

```bash
ssh -p 2222 sandbox@ec2-35-182-158-243.ca-central-1.compute.amazonaws.com -i ${CLAUDE_SKILL_DIR}/.ssh/id_rsa "<command>"
```

For example, to check GPU status:

```bash
ssh -p 2222 sandbox@ec2-35-182-158-243.ca-central-1.compute.amazonaws.com -i ${CLAUDE_SKILL_DIR}/.ssh/id_rsa "nvidia-smi"
```

## Usage Notes

- The sandbox has 8x NVIDIA RTX A6000 GPUs (48GB VRAM each, 384GB total).
- CUDA 12.5 driver is installed. Use PyTorch compiled for CUDA 12.4 (`torch==2.5.1+cu124` from `https://download.pytorch.org/whl/cu124`).
- Python 3.10 is available. `transformers`, `torch`, and `accelerate` are pre-installed.
- Use `-o StrictHostKeyChecking=no` on first connection to skip the host key prompt.

## Setup (for reference)

To register additional SSH keys, go to https://gpu-sandbox-keys-upload.mcgill-nlp.org (password: `O8zF1-BP27u7E9Ut`) and follow the instructions, or use the script at `~/gpu-sandbox/scripts/add-ssh-key.sh`.
