import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import math

TELEGRAM_TOKEN = "yourTokenofFatherBot" #Change yourTokenofFatherBot to your Token, create a bot on @fatherbot and get Token Bot.

user_states = {}
def escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_\*\[\]\(\)~>#+=|{}.!\\-])', r'\\\1', text) 
    
def format_money(amount):
    if amount >= 1_000_000_000:
        return f"{round(amount / 1_000_000_000, 2)}B$"
    elif amount >= 1_000_000:
        return f"{round(amount / 1_000_000, 2)}M$"
    else:
        return f"{amount}$"

async def fund_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng nhập tên dự án sau lệnh /fund. Ví dụ: /fund Zeta")
        return

    query = " ".join(context.args)
    url = f"https://api.cryptorank.io/v0/funding-rounds-v2/find?search={query}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if not data:
            await update.message.reply_text("Không tìm thấy dự án nào phù hợp.")
            return

        user_id = update.message.from_user.id
        user_states[user_id] = {"projects": data}

        message_lines = ["🔍 Danh sách dự án tìm thấy:"]
        for idx, project in enumerate(data, start=1):
            name = project.get("name", "Không tên")
            message_lines.append(f"{idx}. {name}")

        message_lines.append("\nLựa chọn dự án cần kiểm tra [Để lại mã số bên dưới]:")
        await update.message.reply_text("\n".join(message_lines))

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"Đã xảy ra lỗi khi gọi API: {e}")

async def reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_states or "projects" not in user_states[user_id]:
        return

    try:
        choice = int(text) - 1
        projects = user_states[user_id]["projects"]

        if choice < 0 or choice >= len(projects):
            await update.message.reply_text("Lựa chọn không hợp lệ. Vui lòng nhập lại số thứ tự.")
            return

        selected_project = projects[choice]
        key = selected_project["key"]
        name = selected_project["name"]
        api_url = f"https://api.cryptorank.io/v0/funding-rounds/with-tiered-investors/by-coin-key/{key}"

        resp = requests.get(api_url)
        resp.raise_for_status()
        rounds_data = resp.json()

        if not rounds_data:
            await update.message.reply_text(f"Không có thông tin gọi vốn cho dự án {name}.")
            return

        total_raise = sum(item["raise"] or 0 for item in rounds_data)
        result = [f"📊 {name}\nTổng số tiền gọi vốn: {format_money(total_raise)}\n"]

        for r in rounds_data:
            date = r.get("date", "")[:10]
            round_type = r.get("type", "Unknown")
            raise_amount = r.get("raise", 0)
            announcement = r.get("linkToAnnouncement", "")
            investors = r.get("investors", {})
            raise_str = format_money(raise_amount)
            result.append(f"🔹 {round_type} Round [{announcement}] - {date}\nSố tiền: {raise_str}")

            tier_lines = []
            for tier in ['tier1', 'tier2', 'tier3', 'tier4', 'tier5', 'angel', 'other']:
                for inv in investors.get(tier, []):
                    name = inv["name"]
                    is_lead = inv["type"] == "LEAD"
                    tier_str = f"- {name}"
                    if is_lead:
                        tier_str += " (*)"
                    tier_lines.append(tier_str)
            if tier_lines:
                result.append("Các quỹ đầu tư:\n" + "\n".join(tier_lines))
            result.append("")

        await update.message.reply_text("\n".join(result[:4096]))

    except ValueError:
        await update.message.reply_text("Vui lòng nhập một số hợp lệ.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"Đã xảy ra lỗi khi gọi API chi tiết: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("fund", fund_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply_handler))
    print("Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
