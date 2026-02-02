# 🤖 Discord Setup Guide for BeatBot

BeatBot is now ready to be your remote autonomous assistant!

## 1. Create a Discord Application
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Click **New Application** and name it "BeatBot".
3.  Go to the **Bot** tab and click **Add Bot**.
4.  **IMPORTANT**: Under "Privileged Gateway Intents", enable **Message Content Intent**.
5.  Copy the **Token** (Click "Reset Token" if needed).

## 2. Configure Your Environment
Set the token as an environment variable (PowerShell):
```powershell
$env:BEATBOT_DISCORD_TOKEN = "YOUR_TOKEN_HERE"
```

## 3. Configure User Access
1.  Open `config/default_config.yaml`.
2.  Find `messaging.discord`.
3.  Add your Discord User ID to `allowed_users`.
    *   To get ID: Enable Developer Mode in Discord App Settings > Advanced, then Right Click your name > Copy User ID.

```yaml
messaging:
  discord:
    allowed_users: 
      - "123456789012345678"
```

## 4. Run the Bot
```bash
python main.py --mode discord
```

## 5. Invite the Bot
When the bot starts, it will print an Invite Link properly formatted with permissions. Click it to add the bot to your server.

## Features
*   **Chat**: Mention `@BeatBot` or DM it.
*   **Commands**: Use `!help` or just ask naturally.
*   **Approvals**: When BeatBot tries to run a command (e.g. `ls -la`), it will send a Card with **Approve/Deny** buttons.
*   **Heartbeat**: If configured, it will message you proactively (e.g. Morning Briefing).
