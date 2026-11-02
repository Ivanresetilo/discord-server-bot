import time
from datetime import timedelta

import discord
from discord.ext import commands

import config
import db

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


def has_role(member, name):
    return any(r.name == name for r in getattr(member, "roles", []))


def find_channel(guild, name):
    for ch in guild.text_channels:
        if ch.name == name:
            return ch
    return None


async def log(guild, text):
    ch = find_channel(guild, config.LOG_CHANNEL)
    if ch:
        await ch.send(text)


# ---------- Тикеты ----------


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать тикет", style=discord.ButtonStyle.primary, custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
        if existing:
            await interaction.response.send_message(
                f"У тебя уже есть открытый тикет: {existing.mention}", ephemeral=True
            )
            return
        category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        support = discord.utils.get(guild.roles, name=config.SUPPORT_ROLE)
        if support:
            overwrites[support] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )
        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}", overwrites=overwrites, category=category
        )
        await channel.send(
            f"{user.mention} привет! Опиши свою проблему — поддержка ответит.\n"
            f"Закрыть тикет: `!close`"
        )
        await interaction.response.send_message(f"Тикет создан: {channel.mention}", ephemeral=True)
        await log(guild, f"🎫 {user} открыл тикет {channel.mention}")


# ---------- События ----------


@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"Бот запущен: {bot.user}")


@bot.event
async def on_member_join(member):
    ch = find_channel(member.guild, config.WELCOME_CHANNEL)
    if ch:
        await ch.send(f"👋 Добро пожаловать на **{config.GUILD_NAME}**, {member.mention}!")
    if config.WELCOME_ROLE:
        role = discord.utils.get(member.guild.roles, name=config.WELCOME_ROLE)
        if role:
            await member.add_roles(role)
    await log(member.guild, f"➕ {member} зашёл на сервер")


# ---------- Тикеты: команды ----------


@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    """Опубликовать панель создания тикетов."""
    embed = discord.Embed(
        title="🎫 Поддержка",
        description="Нажми кнопку ниже, чтобы открыть личный тикет с поддержкой.",
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed, view=TicketView())


@bot.command()
async def close(ctx):
    """Закрыть текущий тикет."""
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("Это не тикет-канал.")
        return
    if not (
        ctx.author.guild_permissions.manage_channels
        or ctx.channel.name == f"ticket-{ctx.author.id}"
        or has_role(ctx.author, config.SUPPORT_ROLE)
    ):
        await ctx.send("Нет прав закрыть этот тикет.")
        return
    await ctx.send("Тикет закрывается…")
    await log(ctx.guild, f"🔒 Тикет {ctx.channel.name} закрыт пользователем {ctx.author}")
    await ctx.channel.delete()


# ---------- Модерация ----------


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="без причины"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} кикнут. Причина: {reason}")
    await log(ctx.guild, f"👢 {ctx.author} кикнул {member} ({reason})")


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="без причины"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} забанен. Причина: {reason}")
    await log(ctx.guild, f"🔨 {ctx.author} забанил {member} ({reason})")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason="без причины"):
    """Мут участника на N минут."""
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until, reason=reason)
    await ctx.send(f"🔇 {member} в муте на {minutes} мин. Причина: {reason}")
    await log(ctx.guild, f"🔇 {ctx.author} замутил {member} на {minutes} мин ({reason})")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member} размучен.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    """Удалить последние N сообщений."""
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Удалено {len(deleted) - 1} сообщений.", delete_after=5)
    await log(ctx.guild, f"🧹 {ctx.author} очистил {len(deleted) - 1} сообщений в {ctx.channel.mention}")


# ---------- Экономика ----------


@bot.command(aliases=["bal", "баланс"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    b = db.get_balance(member.id)
    await ctx.send(f"💰 {member.display_name}: **{b['amount']}** {config.CURRENCY}")


@bot.command()
async def daily(ctx):
    b = db.get_balance(ctx.author.id)
    now = int(time.time())
    if now - b["last_daily"] < 86400:
        left = 86400 - (now - b["last_daily"])
        await ctx.send(f"⏳ Следующая награда через {left // 3600} ч {(left % 3600) // 60} мин.")
        return
    db.set_last_daily(ctx.author.id, now)
    db.add(ctx.author.id, config.DAILY_REWARD)
    await ctx.send(f"🎁 +{config.DAILY_REWARD} {config.CURRENCY}! Приходи завтра за новой.")


@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("Сумма должна быть больше нуля.")
        return
    b = db.get_balance(ctx.author.id)
    if b["amount"] < amount:
        await ctx.send("Не хватает средств.")
        return
    db.add(ctx.author.id, -amount)
    db.add(member.id, amount)
    await ctx.send(f"💸 {ctx.author.display_name} → {member.display_name}: **{amount}** {config.CURRENCY}")


@bot.command()
async def top(ctx):
    rows = db.top(10)
    if not rows:
        await ctx.send("Пока пусто.")
        return
    lines = []
    for i, r in enumerate(rows, 1):
        member = ctx.guild.get_member(r["user_id"])
        name = member.display_name if member else f"ID {r['user_id']}"
        lines.append(f"{i}. **{name}** — {r['amount']} {config.CURRENCY}")
    await ctx.send("🏆 **Топ богачей**\n" + "\n".join(lines))


# ---------- Объявления ----------


@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, text):
    """Красивое объявление от имени сервера."""
    embed = discord.Embed(description=text, color=discord.Color.gold())
    embed.set_author(name=config.GUILD_NAME, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    await ctx.send(embed=embed)
    await ctx.message.delete()


@bot.command()
async def help(ctx):
    await ctx.send(
        "**Команды:**\n"
        "👤 `!balance` `!daily` `!pay @юзер сумма` `!top`\n"
        "🎫 `!ticketpanel` (админ) · `!close` — в тикете\n"
        "🛡 `!kick` `!ban` `!mute мин` `!unmute` `!clear n` (модерация)\n"
        "📢 `!announce текст` (админ)"
    )


if __name__ == "__main__":
    db.init_db()
    bot.run(config.BOT_TOKEN)
