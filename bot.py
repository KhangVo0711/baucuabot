import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import cooldown, BucketType
import random, json, os, time

# ====== CONFIG ======
TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"

BAU_CUA = ["bầu", "cua", "tôm", "cá", "nai", "gà"]
EMOJI = {
    "bầu": "🍐",
    "cua": "🦀",
    "tôm": "🦐",
    "cá": "🐟",
    "nai": "🦌",
    "gà": "🐓"
}

# ====== BOT ======
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== DATA ======
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(data, uid):
    if uid not in data:
        data[uid] = {
            "money": 1000,
            "win": 0,
            "lose": 0,
            "history": [],
            "last_daily": 0
        }
    return data[uid]

def get_rank(money):
    if money >= 100000:
        return "🔵 Kim Cương"
    elif money >= 20000:
        return "🟡 Vàng"
    elif money >= 5000:
        return "⚪ Bạc"
    return "🟤 Đồng"

# ====== EVENTS ======
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

# ====== SLASH COMMANDS ======

@bot.tree.command(name="money", description="Xem số dư")
async def money(interaction: discord.Interaction):
    data = load_data()
    user = get_user(data, str(interaction.user.id))
    save_data(data)

    embed = discord.Embed(title="💰 Ví tiền", color=0x2ecc71)
    embed.add_field(name="Số dư", value=f"{user['money']} 💵")
    embed.add_field(name="Rank", value=get_rank(user["money"]))
    await interaction.response.send_message(embed=embed)

# ====== DAILY ======
@bot.tree.command(name="daily", description="Nhận tiền mỗi ngày")
async def daily(interaction: discord.Interaction):
    data = load_data()
    user = get_user(data, str(interaction.user.id))
    now = int(time.time())

    if now - user["last_daily"] < 86400:
        remain = 86400 - (now - user["last_daily"])
        hours = remain // 3600
        await interaction.response.send_message(
            f"⏳ Bạn đã nhận rồi! Còn {hours} giờ nữa."
        )
        return

    reward = 500
    user["money"] += reward
    user["last_daily"] = now
    save_data(data)

    embed = discord.Embed(title="🎁 DAILY", color=0xf1c40f)
    embed.add_field(name="Phần thưởng", value=f"+{reward} 💵")
    embed.add_field(name="Số dư", value=f"{user['money']} 💵")
    await interaction.response.send_message(embed=embed)

# ====== DAT ======
@bot.tree.command(name="dat", description="Đặt cược bầu cua")
@app_commands.describe(
    con="bầu, cua, tôm, cá, nai, gà",
    tien="Số tiền hoặc all",
    chedo="x1, x2, x3, all"
)
@cooldown(1, 10, BucketType.user)
async def dat(
    interaction: discord.Interaction,
    con: str,
    tien: str,
    chedo: str = "x1"
):
    con = con.lower()
    chedo = chedo.lower()

    if con not in BAU_CUA:
        await interaction.response.send_message("Con không hợp lệ")
        return

    data = load_data()
    user = get_user(data, str(interaction.user.id))

    if tien == "all":
        tien = user["money"]
    else:
        if not tien.isdigit():
            await interaction.response.send_message("Tiền không hợp lệ")
            return
        tien = int(tien)

    if tien <= 0 or user["money"] < tien:
        await interaction.response.send_message("Không đủ tiền")
        return

    he_so = {"x1": 1, "x2": 2, "x3": 3, "all": 1}.get(chedo, 1)

    ket_qua = random.choices(BAU_CUA, k=3)
    trung = ket_qua.count(con)

    embed = discord.Embed(title="🎲 BẦU CUA", color=0xe67e22)
    embed.add_field(
        name="Kết quả",
        value=" | ".join([EMOJI[x] for x in ket_qua]),
        inline=False
    )

    if trung > 0:
        win_money = tien * trung * he_so
        user["money"] += win_money
        user["win"] += 1
        result = f"🎉 Trúng {trung} → +{win_money} 💵"
    else:
        user["money"] -= tien
        user["lose"] += 1
        result = f"💀 Thua -{tien} 💵"

    user["history"].append({
        "bet": con,
        "money": tien,
        "result": result
    })
    user["history"] = user["history"][-10:]

    embed.add_field(name="Kết quả cược", value=result, inline=False)
    embed.add_field(name="Số dư", value=f"{user['money']} 💵")
    embed.add_field(name="Rank", value=get_rank(user["money"]))

    save_data(data)
    await interaction.response.send_message(embed=embed)

# ====== HISTORY ======
@bot.tree.command(name="history", description="Xem lịch sử cược")
async def history(interaction: discord.Interaction):
    data = load_data()
    user = get_user(data, str(interaction.user.id))

    if not user["history"]:
        await interaction.response.send_message("📭 Chưa có lịch sử")
        return

    text = ""
    for i, h in enumerate(user["history"], 1):
        text += f"{i}. {h['bet']} | {h['result']}\n"

    embed = discord.Embed(title="🧾 Lịch sử cược", description=text, color=0x3498db)
    await interaction.response.send_message(embed=embed)

# ====== RANK ======
@bot.tree.command(name="rank", description="Bảng xếp hạng")
async def rank(interaction: discord.Interaction):
    data = load_data()
    top = sorted(data.items(), key=lambda x: x[1]["money"], reverse=True)[:10]

    embed = discord.Embed(title="🏆 BXH", color=0xf39c12)
    for i, (uid, info) in enumerate(top, 1):
        user = await bot.fetch_user(int(uid))
        embed.add_field(
            name=f"#{i} {user.name}",
            value=f"{info['money']} 💵 | {get_rank(info['money'])}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ====== RUN ======
bot.run(TOKEN)
