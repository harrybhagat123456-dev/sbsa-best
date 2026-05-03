import os
import json
import base64
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from vars import OWNER

GH_PAT   = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_PAT", ""))
GH_REPO  = os.environ.get("GITHUB_REPO", "harrybhagat123456-dev/sbsa-best")
GH_FILE  = "render_accounts.json"   # stored as a plain file in the repo

_pending = {}


def _gh_headers():
    return {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _fetch_file() -> tuple:
    """
    Returns (data_dict, sha_or_None).
    data_dict has keys: "accounts" (list) and "active_slot" (int, 1-based).
    """
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE}"
    r = requests.get(url, headers=_gh_headers(), timeout=10)
    if r.status_code == 404:
        return {"accounts": [], "active_slot": 1}, None
    r.raise_for_status()
    payload = r.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content), payload["sha"]


def _push_file(data: dict, sha) -> bool:
    """Push updated data dict back to GitHub."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE}"
    encoded = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    body = {
        "message": "bot: update render accounts",
        "content": encoded,
    }
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=_gh_headers(), json=body, timeout=10)
    return r.status_code in (200, 201)


def _get_accounts() -> list:
    data, _ = _fetch_file()
    return data.get("accounts", [])


def _save_accounts(accounts: list) -> bool:
    data, sha = _fetch_file()
    data["accounts"] = accounts
    return _push_file(data, sha)


def _get_active_slot() -> int:
    data, _ = _fetch_file()
    return int(data.get("active_slot", 1))


def _update_active_slot(slot: int) -> bool:
    data, sha = _fetch_file()
    data["active_slot"] = slot
    return _push_file(data, sha)


def register_render_manager_handlers(bot: Client):

    @bot.on_message(filters.command("addaccount") & filters.private, group=-1)
    async def cmd_addaccount(client: Client, message: Message):
        try:
            logging.info(f"[RenderManager] /addaccount from {message.from_user.id}, OWNER={OWNER}")
            if message.from_user.id != OWNER:
                await message.reply("Owner only command.")
                return
            _pending[message.from_user.id] = {"step": 1, "data": {}}
            await message.reply(
                "**➕ Add New Render Account**\n\n"
                "**Step 1/3** — Send your Render API Key\n"
                "_(Render Dashboard → Account Settings → API Keys → Create)_"
            )
        except Exception as e:
            logging.exception(f"[RenderManager] /addaccount error: {e}")
            try:
                await message.reply(f"❌ Error: `{e}`")
            except Exception:
                pass

    @bot.on_message(filters.command("listaccounts") & filters.private, group=-1)
    async def cmd_listaccounts(client: Client, message: Message):
        try:
            logging.info(f"[RenderManager] /listaccounts from {message.from_user.id}, OWNER={OWNER}")
            if message.from_user.id != OWNER:
                await message.reply("Owner only command.")
                return
            data, _ = _fetch_file()
            accounts = data.get("accounts", [])
            if not accounts:
                await message.reply("No accounts registered yet.\nUse /addaccount to add one.")
                return
            active_slot = int(data.get("active_slot", 1))
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
        except Exception as e:
            logging.exception(f"[RenderManager] /listaccounts error: {e}")
            try:
                await message.reply(f"❌ Error: `{e}`")
            except Exception:
                pass

    @bot.on_message(filters.command("removeaccount") & filters.private, group=-1)
    async def cmd_removeaccount(client: Client, message: Message):
        try:
            logging.info(f"[RenderManager] /removeaccount from {message.from_user.id}, OWNER={OWNER}")
            if message.from_user.id != OWNER:
                await message.reply("Owner only command.")
                return
            parts = message.text.split()
            if len(parts) < 2 or not parts[1].isdigit():
                await message.reply("Usage: `/removeaccount <slot_number>`\nExample: `/removeaccount 2`")
                return
            slot = int(parts[1])
            data, sha = _fetch_file()
            accounts = data.get("accounts", [])
            if slot < 1 or slot > len(accounts):
                await message.reply(f"Invalid slot. You have {len(accounts)} account(s).")
                return
            removed = accounts.pop(slot - 1)
            data["accounts"] = accounts
            active = int(data.get("active_slot", 1))
            if active == slot or active > len(accounts):
                data["active_slot"] = 1
            if _push_file(data, sha):
                await message.reply(
                    f"✅ Slot {slot} removed!\n"
                    f"URL was: `{removed.get('url')}`\n"
                    f"Remaining: {len(accounts)} account(s)"
                )
            else:
                await message.reply("❌ Failed to save. Check GITHUB_TOKEN has repo write access.")
        except Exception as e:
            logging.exception(f"[RenderManager] /removeaccount error: {e}")
            try:
                await message.reply(f"❌ Error: `{e}`")
            except Exception:
                pass

    @bot.on_message(filters.private & filters.text & ~filters.command(
        ["addaccount", "listaccounts", "removeaccount", "start", "stop",
         "reset", "broadcast", "addauth", "rmauth"]), group=-1)
    async def handle_addaccount_steps(client: Client, message: Message):
        try:
            uid = message.from_user.id
            if uid not in _pending:
                return

            state = _pending[uid]
            step = state["step"]
            text = message.text.strip()
            logging.info(f"[RenderManager] addaccount step={step} from {uid}")

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
                    data, sha = _fetch_file()
                    accounts = data.get("accounts", [])
                    accounts.append(new_account)
                    data["accounts"] = accounts
                    success = _push_file(data, sha)
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
                    await wait_msg.edit_text(
                        "❌ Failed to save to GitHub.\n"
                        "Make sure GITHUB_TOKEN has **Contents: Read & Write** permission."
                    )
        except Exception as e:
            logging.exception(f"[RenderManager] step handler error: {e}")

    print(f"[RenderManager] Handlers registered (group=-1): /addaccount /listaccounts /removeaccount | OWNER={OWNER}")
