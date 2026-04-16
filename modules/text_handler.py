import os
import json
import requests
import subprocess
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from utils import safe_listen

async def text_to_txt(bot: Client, message: Message):
    user_id = message.from_user.id
    # Inform the user to send the text data and its desired file name
    editable = await message.reply_text(f"<blockquote><b>Welcome to the Text to .txt Converter!\nSend the **text** for convert into a `.txt` file.</b></blockquote>")
    input_message: Message = await safe_listen(bot, message.chat.id, user_id, timeout=60)
    if input_message is None or not input_message.text:
        await message.reply_text("**Send valid text data**")
        return

    text_data = input_message.text.strip()
    await input_message.delete()

    await editable.edit("**🔄 Send file name or send /d for filename**")
    inputn: Message = await safe_listen(bot, message.chat.id, user_id, timeout=60)
    if inputn is None:
        raw_textn = '/d'
    else:
        raw_textn = inputn.text or '/d'
        await inputn.delete()
    await editable.delete()

    if raw_textn == '/d':
        custom_file_name = 'txt_file'
    else:
        custom_file_name = raw_textn

    txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
    os.makedirs(os.path.dirname(txt_file), exist_ok=True)  # Ensure the directory exists
    with open(txt_file, 'w') as f:
        f.write(text_data)
        
    await message.reply_document(document=txt_file, caption=f"`{custom_file_name}.txt`\n\n<blockquote>You can now download your content! 📥</blockquote>")
    os.remove(txt_file)

# Define paths for uploaded file and processed file
UPLOAD_FOLDER = '/path/to/upload/folder'
EDITED_FILE_PATH = '/path/to/save/edited_output.txt'

#========================================================================================================================

CONTENT_TYPES = ['videos', 'notes', 'DppNotes', 'DppVideos']

async def json_to_txt(bot: Client, message: Message):
    user_id = message.from_user.id
    editable = await message.reply_text(
        "<blockquote><b>📂 Send the PW JSON file to convert it to a .txt link file.</b></blockquote>"
    )

    input_msg: Message = await safe_listen(bot, message.chat.id, user_id, timeout=60)

    if input_msg is None or not input_msg.document or not input_msg.document.file_name.endswith('.json'):
        await editable.edit("❌ Please send a valid <b>.json</b> file.")
        if input_msg:
            await input_msg.delete()
        return

    await editable.edit("⏳ Downloading and processing JSON file...")
    file_path = await input_msg.download()
    await input_msg.delete()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        os.remove(file_path)
    except Exception as e:
        await editable.edit(f"❌ Failed to parse JSON:\n<blockquote>{e}</blockquote>")
        return

    # Top-level key is the batch name
    batch_name = list(data.keys())[0] if data else "output"
    batch_data = data.get(batch_name, {})

    lines_out = [f"# {batch_name}", ""]
    total_links = 0
    parent_headings = []       # unique parent section names for summary
    _seen_parents = set()

    for section_name, section_data in batch_data.items():
        if not isinstance(section_data, dict):
            continue
        # Collect all links under this parent section first
        section_links = []
        for subsection_name, subsection_data in section_data.items():
            if not isinstance(subsection_data, dict):
                continue
            for ctype in CONTENT_TYPES:
                items = subsection_data.get(ctype, [])
                if not items:
                    continue
                for item in items:
                    name = item.get('name', 'Unnamed').strip()
                    url = item.get('url', '').strip()
                    if not url:
                        continue
                    if url.startswith('https://'):
                        url_part = url[8:]
                    elif url.startswith('http://'):
                        url_part = url[7:]
                    else:
                        url_part = url
                    section_links.append(f"{name}://{url_part}")

        if not section_links:
            continue

        # Write parent heading once, then all links under it
        lines_out.append(section_name)
        lines_out.append("")  # blank line after heading
        for link_line in section_links:
            lines_out.append(link_line)
            total_links += 1
        lines_out.append("")  # blank line after section

        # Track unique parent headings for summary
        if section_name not in _seen_parents:
            parent_headings.append(section_name)
            _seen_parents.add(section_name)

    if total_links == 0:
        await editable.edit("❌ No links found in the JSON file.")
        return

    txt_content = '\n'.join(lines_out)
    safe_name = batch_name.replace(' ', '_').replace('/', '_')[:60]
    output_file = f"downloads/{safe_name}.txt"
    os.makedirs('downloads', exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(txt_content)

    await editable.delete()
    await message.reply_document(
        document=output_file,
        caption=(
            f"<b>✅ JSON → TXT Converted!</b>\n"
            f"<blockquote>"
            f"📚 <b>Batch:</b> {batch_name}\n"
            f"🔗 <b>Total Links:</b> {total_links}"
            f"</blockquote>"
        )
    )
    os.remove(output_file)

    # Send parent section names as a separate summary message
    heading_text = f"<b>📋 Topic Names ({len(parent_headings)}) — create these in your group:</b>\n\n"
    heading_text += "\n".join(f"• {h}" for h in parent_headings)
    heading_text += "\n\n<i>Once created, go into each topic → /topicid → add [id] before the heading in your txt file.</i>"

    # Split into chunks if too long
    MAX_LEN = 4000
    if len(heading_text) <= MAX_LEN:
        await message.reply_text(heading_text, parse_mode=enums.ParseMode.HTML)
    else:
        lines_h = heading_text.split("\n")
        chunk = ""
        for line in lines_h:
            if len(chunk) + len(line) + 1 > MAX_LEN:
                await message.reply_text(chunk, parse_mode=enums.ParseMode.HTML)
                chunk = line + "\n"
            else:
                chunk += line + "\n"
        if chunk.strip():
            await message.reply_text(chunk, parse_mode=enums.ParseMode.HTML)

#========================================================================================================================
def register_text_handlers(bot):
    @bot.on_message(filters.command(["t2t"]))
    async def call_text_to_txt(bot: Client, m: Message):
        await text_to_txt(bot, m)

    @bot.on_message(filters.command(["json"]))
    async def call_json_to_txt(bot: Client, m: Message):
        await json_to_txt(bot, m)
    
