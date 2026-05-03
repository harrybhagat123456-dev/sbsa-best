import os
import json
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

OWNER_ID  = int(os.environ.get("OWNER", 0))
GH_PAT    = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_PAT", ""))
GH_REPO   = os.environ.get("GITHUB_REPO", "harrybhagat123456-dev/sbsa-best")
VAR_NAME  = "RENDER_ACCOUNTS"
ACTIVE_VAR = "ACTIVE_SLOT"

def _gh_headers():
    return {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

_pending = {}


def _get_accounts() -> list:
    url = f"https://api.github.com/repos/{GH_REPO}/actions/variables/{VAR_NAME}"
    r = requests.get(url, headers=_gh_headers(), timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return json.loads(r.json()["value"])


def _save_accounts(accounts: list) -> bool:
    value = json.dumps(accounts)
    url = f"https://api.github.com/repos/{GH_REPO}/actions/variables/{VAR_NAME}"
    r = requests.patch(url, headers=_gh_headers(),
                       json={"name": VAR_NAME, "value": value}, timeout=10)
    if r.status_code == 404:
        r = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/actions/variables",
            headers=_gh_headers(),
            json={"name": VAR_NAME, "value": value}, timeout=10)
    return r.status_code in (200, 201, 204)


def _update_active_slot(slot: int) -> bool:
    url = f"https://api.github.com/repos/{GH_REPO}/actions/variables/{ACTIVE_VAR}"
    r = requests.patch(url, headers=_gh_headers(),
                       json={"name": ACTIVE_VAR, "value": str(slot)}, timeout=10)
    if r.status_code == 404:
        r = requests.post(
            f"https://api.github.com/repos/{GH_REPO}/actions/variables",
            headers=_gh_headers(),
            json={"name": ACTIVE_VAR, "value": str(slot)}, timeout=10)
    return r.status_code in (200, 201, 204)


def register_render_manager_handlers(bot: Client):

    @bot.on_message(filters.command("addaccount") & filters.private)
    async def cmd_addaccount(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("Owner only command.")
            return
        _pending[message.from_user.id] = {"step": 1, "data": {}}
        await message.reply(
            "**➕ Add New Render Account**\n\n"
            "**Step 1/3** — Send your Render API Key\n"
            "_(Render Dashboard → Account Settings → API Keys → Create)_"
        )

    @bot.on_message(filters.command("listaccounts") & filters.private)
    async def cmd_listaccounts(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("Owner only command.")
            return
        try:
            accounts = _get_accounts()
        except Exception as e:
            await message.reply(f"❌ Error fetching accounts: `{e}`")
            return

        if not accounts:
            await message.reply("No accounts registered yet.\nUse /addaccount to add one.")
            return

        active_slot = int(os.environ.get("ACTIVE_SLOT", 1))
        lines = ["**📋 Registered Render Accounts:**\n"]
        for i, acc in enumerate(accounts, 1):
            status = "✅ ACTIVE" if i == active_slot else "⏸ Suspended"
            lines.append(
                f"**Slot {i}** [{status}]\n"
                f"  URL: `{acc.get('url', 'N/A')}`\n"
                f"  Service ID: `{acc.get('service_id', 'N/A')}`\n"
                f"  API Key: `{acc.get('api_key', '')[:8]}...`\n"
            )
        await message.reply("\n".join(lines))

    @bot.on_message(filters.command("removeaccount") & filters.private)
    async def cmd_removeaccount(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply("Owner only command.")
            return
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply("Usage: `/removeaccount <slot_number>`\nExample: `/removeaccount 2`")
            return

        slot = int(parts[1])
        try:
            accounts = _get_accounts()
        except Exception as e:
            await message.reply(f"❌ Error: `{e}`")
            return

        if slot < 1 or slot > len(accounts):
            await message.reply(f"Invalid slot. You have {len(accounts)} account(s).")
            return

        removed = accounts.pop(slot - 1)
        if _save_accounts(accounts):
            active = int(os.environ.get("ACTIVE_SLOT", 1))
            if active == slot or active > len(accounts):
                _update_active_slot(1)
            await message.reply(
                f"✅ Slot {slot} removed!\n"
                f"URL was: `{removed.get('url')}`\n"
                f"Remaining accounts: {len(accounts)}"
            )
        else:
            await message.reply("❌ Failed to save changes to GitHub. Check GITHUB_TOKEN permissions.")

    @bot.on_message(filters.private & filters.text & ~filters.command(
        ["addaccount", "listaccounts", "removeaccount", "start", "stop",
         "reset", "broadcast", "addauth", "rmauth"]))
    async def handle_addaccount_steps(client: Client, message: Message):
        uid = message.from_user.id
        if uid not in _pending:
            return

        state = _pending[uid]
        step = state["step"]
        text = message.text.strip()

        if step == 1:
            state["data"]["api_key"] = text
            state["step"] = 2
            await message.reply(
                "✅ API Key saved!\n\n"
                "**Step 2/3** — Send the Service ID\n"
                "_(Render Dashboard → Your Service → Settings → looks like `srv-xxxxxxxxxx`)_"
            )

        elif step == 2:
            if not text.startswith("srv-"):
                await message.reply(
                    "⚠️ Service ID usually starts with `srv-`\n"
                    "Please check and send it again."
                )
                return
            state["data"]["service_id"] = text
            state["step"] = 3
            await message.reply(
                "✅ Service ID saved!\n\n"
                "**Step 3/3** — Send the Bot URL (public Render URL)\n"
                "_(e.g. `https://your-bot-name.onrender.com`)_"
            )

        elif step == 3:
            if not text.startswith("http"):
                await message.reply("⚠️ URL should start with `https://`\nPlease send a valid URL.")
                return

            state["data"]["url"] = text.rstrip("/")
            new_account = state["data"]

            wait_msg = await message.reply("💾 Saving to GitHub...")
            try:
                accounts = _get_accounts()
                accounts.append(new_account)
                success = _save_accounts(accounts)
            except Exception as e:
                await wait_msg.edit_text(f"❌ Failed: `{e}`")
                _pending.pop(uid, None)
                return

            _pending.pop(uid)

            if success:
                slot_num = len(accounts)
                await wait_msg.edit_text(
                    f"✅ **Account added as Slot {slot_num}!**\n\n"
                    f"URL: `{new_account['url']}`\n"
                    f"Service ID: `{new_account['service_id']}`\n\n"
                    f"Total accounts: {slot_num}\n\n"
                    f"Keep this service **suspended** on Render.\n"
                    f"The watchdog will auto-activate it when needed!"
                )
            else:
                await wait_msg.edit_text("❌ Failed to save to GitHub. Check GITHUB_TOKEN permissions.")

    print("[RenderManager] Handlers registered: /addaccount /listaccounts /removeaccount")
