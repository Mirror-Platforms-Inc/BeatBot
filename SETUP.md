# BeatBot - Setup Guide

This guide will help you set up BeatBot in your local environment.

## 1. Quick Start (Windows PowerShell)

We provide a setup script that handles dependency checks and environment configuration.

```powershell
./setup.ps1
```

## 2. Manual Setup

If you prefer to set things up manually:

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Models (Ollama)
1. Download from [ollama.ai](https://ollama.ai).
2. Pull your preferred model:
   ```bash
   ollama pull llama3.2
   ```

### Set Environment Variables
```bash
# Windows
$env:BEATBOT_MODEL_DEFAULT = "ollama/llama3.2"
$env:BEATBOT_SANDBOX_ENABLED = "true"

# Linux/Mac
export BEATBOT_MODEL_DEFAULT="ollama/llama3.2"
export BEATBOT_SANDBOX_ENABLED="true"
```

## 3. Launching BeatBot

### Interactive Chat Mode
```bash
python main.py --mode interactive
```

### Discord Mode
Follow the instructions in **[DISCORD_SETUP.md](DISCORD_SETUP.md)**, then run:
```bash
python main.py --mode discord
```

python main.py --mode discord
```

## 5. Working on a Project

BeatBot is designed to help you work on your actual codebases. To let it work on a project:

### Phase 1: Authorize the Directory
By default, BeatBot cannot see your files. You must explicitely whitelist your project path:
1. Open `config/default_config.yaml`.
2. Find `allowed_directories`.
3. Add your project path:
   ```yaml
   security:
     allowed_directories:
       - C:/Users/YourName/Projects/my-project
   ```

### Phase 2: Start an Autonomous Task
Give BeatBot a high-level **Goal** rather than a single command. 
*   **Prompt:** "Examine the project in C:/... and help me implement a new login feature."
*   **Observe:** BeatBot will enter a "Thought-Action-Observation" loop. It will list files, read code, and propose changes autonomously.
*   **Approve:** You stay in control. BeatBot will request your approval (via Terminal or Discord buttons) before making any sensitive changes.
