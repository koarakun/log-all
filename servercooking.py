
import discord
from discord.ext import commands
import asyncio
import datetime
import random

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
bot.remove_command("help")

@bot.event
async def on_ready(): # type: ignore
    print("起動完了")

@bot.command()
async def test(ctx):
    await ctx.send("test.ok!")

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#管理者向けのコマンド

#chat on off
@bot.command()
@commands.has_permissions(administrator=True)
async def chatoff(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        channel = ctx.channel
        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
        embed = discord.Embed(title="chatの無効化", description=f"{ctx.author.mention} が {channel.mention} のchatを無効化しました。", color=discord.Color.red())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="このコマンドはテキストチャンネルでのみ使用できます。", color=discord.Color.red())
        await ctx.send(embed=embed)

@chatoff.error
async def chatoff_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red()))

@bot.command()
@commands.has_permissions(administrator=True)
async def chaton(ctx):
    if isinstance(ctx.channel, discord.TextChannel):
        channel = ctx.channel
        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites)
        embed = discord.Embed(title="chatの有効化", description=f"{ctx.author.mention} が {channel.mention} のchatを有効化しました。", color=discord.Color.green())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="このコマンドはテキストチャンネルでのみ使用できます。", color=discord.Color.red())
        await ctx.send(embed=embed)

@chaton.error
async def chaton_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red()))

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#chatのクリア
@bot.command()
async def clear(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        error_embed = discord.Embed(
            title="エラー",
            description=f"{ctx.author.mention} さんはこのコマンドを実行する権限がありません。",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        return

    # 確認メッセージを送信する
    message = await ctx.send(embed=discord.Embed(
        title="チャンネルのリセット",
        description=f"{ctx.channel.mention}をリセットしますか？\nリセットする場合:white_check_mark: を押してください",
        color=discord.Color.green()
    ))
    await message.add_reaction("✅")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message == message

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await message.clear_reactions()
        await message.edit(embed=discord.Embed(
            title="タイムアウト",
            description="時間内に✅が押されなかったためリセットはキャンセルされました。",
            color=discord.Color.red()
        ))
    else:
        await clear_and_recreate_channel(ctx)

async def clear_and_recreate_channel(ctx):
    if not ctx.author.guild_permissions.manage_channels:
        error_embed = discord.Embed(
            title="エラー",
            description=f"{ctx.author.mention} さんはこのコマンドを実行する権限がありません。",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        return

    # 削除するチャンネルの情報を取得する
    old_channel = ctx.channel
    category = old_channel.category
    channel_name = old_channel.name
    channel_position = old_channel.position
    channel_overwrites = old_channel.overwrites

    # チャンネルを削除する
    await old_channel.delete()

    # 同じカテゴリに同じ名前、設定でチャンネルを作成する
    new_channel = await category.create_text_channel(
        name=channel_name, position=channel_position, overwrites=channel_overwrites
    )

    # メッセージを送信する
    author_mention = ctx.author.mention
    message = f"{author_mention} がチャンネルをリセットしました"
    embed = discord.Embed(title="チャンネルのリセットに成功しました", description=message, color=discord.Color.green())
    await new_channel.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#埋め込みコマンド
@bot.command()
@commands.has_permissions(administrator=True)
async def embedded(ctx, title, *, message):
    # ファイルを添付する場合
    if ctx.message.attachments:
        file = await ctx.message.attachments[0].to_file()
        embed = discord.Embed(title=f"\u200e{title}\u200e", description=f"\n{message}", color=discord.Color.gold())
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)
    # ファイルを添付しない場合
    else:
        embed = discord.Embed(title=f"\u200e{title}\u200e", description=f"\n{message}", color=discord.Color.gold())
        await ctx.send(embed=embed)

@embedded.error
async def embedded_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(description="エラー\nこのコマンドを実行するには管理者権限が必要です。", color=discord.Color.red())
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#サーバー状況
@bot.command()
@commands.has_permissions(administrator=True)
async def membercount(ctx):
    category = await ctx.guild.create_category("サーバー状況", position=0)
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, connect=True)
    }
    channel = await category.create_voice_channel(f"👤参加人数｜{len(ctx.guild.members)}", overwrites=overwrites)

    async def update_member_count():
        while True:
            await channel.edit(name=f"👤参加人数｜{len(ctx.guild.members)}", reason="自動更新")
            await asyncio.sleep(30)

    bot.loop.create_task(update_member_count())

@membercount.error
async def membercount_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=discord.Color.red())
        await ctx.send(embed=embed)

@bot.event
async def on_member_join(member): # type: ignore
    category = discord.utils.get(member.guild.categories, name="サーバー状況")
    if category is not None:
        channel = discord.utils.get(category.voice_channels, name__startswith="👤参加人数｜")
        if channel is not None:
            await channel.edit(name=f"👤参加人数｜{len(member.guild.members)}", reason="新規参加者")

@bot.event
async def on_member_remove(member): # type: ignore
    category = discord.utils.get(member.guild.categories, name="サーバー状況")
    if category is not None:
        channel = discord.utils.get(category.voice_channels, name__startswith="👤参加人数｜")
        if channel is not None:
            await channel.edit(name=f"参加人数｜{len(member.guild.members)}", reason="退出者")
#--------------------------------------------------------------------------------------------------------------------------------------------------------
#ロールパネル
@bot.command()
@commands.has_permissions(administrator=True)
async def rollpanel(ctx, description, *roles: discord.Role):
    panel = discord.Embed(title="ロールパネル", description=description, color=0x00ff00)
    panel.add_field(name="", value="\n\n".join([f"{i+1}\u20e3 {role.mention}" for i, role in enumerate(roles)]), inline=False)
    panel.set_footer(text="※ 注意：連続してリアクションを押すとロールが付与されない場合があります。3秒ほど待ってからリアクションを押してください。")
    message = await ctx.send(embed=panel)
    for i in range(len(roles)):
        await message.add_reaction(f"{i+1}\u20e3")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) in [f"{i+1}\u20e3" for i in range(len(roles))] and reaction.message.id == message.id

    try:
        while True:
            reaction, user = await bot.wait_for('reaction_add', timeout=None, check=check)
            index = [f"{i+1}\u20e3" for i in range(len(roles))].index(str(reaction.emoji))
            role = roles[index]
            if role in user.roles: # type: ignore
                await user.remove_roles(role) # type: ignore
                await reaction.remove(user)
            else:
                await user.add_roles(role) # type: ignore
                await message.remove_reaction(str(reaction.emoji), user)
    except asyncio.TimeoutError:
        pass

    try:
        await ctx.message.delete()
        await message.delete()
    except:
        pass

    async def delete_messages():
        def check_message(message):
            return "rollpanel" in message.content.lower() and message.created_at > datetime.datetime.now() - datetime.timedelta(minutes=3)
        messages = await ctx.channel.history(limit=100).flatten()
        messages_to_delete = [message for message in messages if check_message(message)]
        await ctx.channel.delete_messages(messages_to_delete)

    await delete_messages()

@rollpanel.error
async def rollpanel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するための権限がありません。", color=0xff0000)
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#認証パネル
@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, description, role: discord.Role):
    panel = discord.Embed(title="認証パネル", description=description, color=0x00ff00)
    panel.add_field(name="", value=f"✅{role.mention}", inline=False)
    panel.set_footer(text="※ 注意：連続してリアクションを押すとロールが付与されない場合があります。3秒ほど待ってからリアクションを押してください。")
    message = await ctx.send(embed=panel)
    await message.add_reaction("✅")

    # メッセージIDを使用して、各認証パネルを個別に識別する
    panel_id = message.id

    def check(reaction, user):
        # メッセージIDが一致し、bot自身でないユーザーからのリアクションかどうかをチェックする
        return user != bot.user and str(reaction.emoji) == "✅" and reaction.message.id == panel_id

    try:
        while True:
            reaction, user = await bot.wait_for('reaction_add', timeout=None, check=check)
            if role in user.roles: # type: ignore
                await user.remove_roles(role) # type: ignore
                await reaction.remove(user)
            else:
                await user.add_roles(role) # type: ignore
                await message.remove_reaction("✅", user)
    except asyncio.TimeoutError:
        pass

    try:
        await ctx.message.delete()
        await message.delete()
    except:
        pass

    async def delete_messages():
        def check_message(message):
            return "verify" in message.content.lower() and message.created_at > datetime.datetime.now() - datetime.timedelta(minutes=3)
        messages = await ctx.channel.history(limit=100).flatten()
        messages_to_delete = [message for message in messages if check_message(message)]
        await ctx.channel.delete_messages(messages_to_delete)

    await delete_messages()

@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するための権限がありません。", color=0xff0000)
        await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------------------------------------
#ギブウェイ
@bot.command()
async def giveaway(ctx, prize_name, duration, winners: int):
    duration_seconds = 0
    if "s" in duration:
        duration_seconds = int(duration.replace("s", ""))
    elif "m" in duration:
        duration_seconds = int(duration.replace("m", "")) * 60
    elif "h" in duration:
        duration_seconds = int(duration.replace("h", "")) * 60 * 60
    elif "d" in duration:
        duration_seconds = int(duration.replace("d", "")) * 24 * 60 * 60

    embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                          description=f"🎉景品{prize_name}\n\n"
                                      f"👍参加希望の方はリアクションを押してください\n\n"
                                      f"👀{ctx.author.mention} がこの企画を主催しています！\n\n"
                                      f"⏱終了まであと {duration} (開催時間：{duration_seconds}秒)\n\n"
                                      f"🏆当選者数：{winners}人",
                          color=0xff0000)

    message = await ctx.send(embed=embed)

    await message.add_reaction("👍")

    await ctx.message.delete()

    await asyncio.sleep(duration_seconds)

    message = await ctx.channel.fetch_message(message.id)
    reaction = discord.utils.get(message.reactions, emoji="👍")

    users = []
    async for user in reaction.users():
        if user != bot.user:
            users.append(user)

    if not users:
        embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                              description="参加者がいなかったため、プレゼント企画を中止します",
                              color=0xff0000)
        await ctx.send(embed=embed)
        return

    if winners > len(users):
        embed = discord.Embed(title="🔊プレゼント企画のお知らせ",
                              description="参加者が足りないため、プレゼント企画を中止します",
                              color=0xff0000)
        await ctx.send(embed=embed)
        return

    chosen_winners = random.sample(users, k=winners)

    winners_mention = "、".join([winner.mention for winner in chosen_winners])

    embed = discord.Embed(title="🔊当選者発表",
                          description=f"{prize_name}のプレゼント企画の当選者は{winners_mention}さんです！🎉おめでとうございます！\n\n"
                                      f"お手数ですが{ctx.author.mention}様のDMまで商品を受け取りに行ってください\n\n",
                          color=0x00ff00)
    await ctx.send(embed=embed)

#---------------------------------------------------------------
#通話ログ
# サーバーごとにボイスログの出力先を保持する辞書
voice_log_channels = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def voicelog(ctx, channel: discord.TextChannel):
    voice_log_channels[ctx.guild.id] = channel.id
    embed = discord.Embed(title="通話ログの出力先を設定しました", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)

@voicelog.error
async def voicelog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if after.channel:
            voice_log_channel_id = voice_log_channels.get(member.guild.id)
            if voice_log_channel_id is not None:
                voice_log_channel = member.guild.get_channel(voice_log_channel_id)
                if voice_log_channel is not None:
                    now = datetime.datetime.now()
                    if now.hour < 12:
                        time_str = now.strftime("%Y/%m/%d 午後%I:%M")
                    else:
                        time_str = now.strftime("%Y/%m/%d 午前%I:%M")
                    embed = discord.Embed(title="通話参加ログ", description=f"{member.mention} が {after.channel.mention} に参加しました。\n\n{time_str}", color=0x00ff00)
                    if member.avatar:
                        embed.set_thumbnail(url=str(member.avatar.url))
                    await voice_log_channel.send(embed=embed)
        elif before.channel:
            voice_log_channel_id = voice_log_channels.get(member.guild.id)
            if voice_log_channel_id is not None:
                voice_log_channel = member.guild.get_channel(voice_log_channel_id)
                if voice_log_channel is not None:
                    now = datetime.datetime.now()
                    if now.hour < 12:
                        time_str = now.strftime("%Y/%m/%d 午後%I:%M")
                    else:
                        time_str = now.strftime("%Y/%m/%d 午前%I:%M")
                    embed = discord.Embed(title="通話退出ログ", description=f"{member.mention} が {before.channel.mention} から退出しました。\n\n{time_str}", color=0xff0000)
                    if member.avatar:
                        embed.set_thumbnail(url=str(member.avatar.url))
                    await voice_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#メッセージの削除ログ
del_log_channel_ids = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def dellog(ctx, channel: discord.TextChannel):
    del_log_channel_ids[ctx.guild.id] = channel.id
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)

@dellog.error
async def dellog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.guild.id in del_log_channel_ids:
        del_log_channel_id = del_log_channel_ids[message.guild.id]
        del_log_channel = message.guild.get_channel(del_log_channel_id)
        if del_log_channel is not None:
            now = datetime.datetime.now()
            if now.hour < 12:
                time_str = now.strftime("%Y/%m/%d 午後%I:%M")
            else:
                time_str = now.strftime("%Y/%m/%d 午前%I:%M")
            embed = discord.Embed(title="メッセージ削除ログ", color=0xff0000)
            embed.add_field(name="チャンネル", value=message.channel.mention, inline=False)
            embed.add_field(name="時間", value=time_str, inline=False)
            embed.add_field(name="メッセージ送信者", value=message.author.mention, inline=False)
            embed.add_field(name="メッセージ内容", value=message.content, inline=False)
            if message.author.avatar:
                embed.set_thumbnail(url=str(message.author.avatar.url))
            await del_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#サーバー参加メッセージ
join_log_channel_ids = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def joinlog(ctx, channel: discord.TextChannel):
    join_log_channel_ids[ctx.guild.id] = channel.id
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)


@joinlog.error
async def joinlog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    join_log_channel_id = join_log_channel_ids.get(guild_id)
    if join_log_channel_id is not None:
        join_log_channel = member.guild.get_channel(join_log_channel_id)
        if join_log_channel is not None:
            await asyncio.sleep(3) # 3秒待つ
            now = datetime.datetime.now()
            if now.hour < 12:
                time_str = now.strftime("%Y/%m/%d 午後%I:%M")
            else:
                time_str = now.strftime("%Y/%m/%d 午前%I:%M")
            embed = discord.Embed(title=f"{member.guild.name}へようこそ！！", color=0xff0000)
            embed.add_field(name="ユーザー", value=member.mention, inline=False)
            embed.add_field(name="時間", value=time_str, inline=False)
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            await join_log_channel.send(embed=embed)

#----------------------------------------------------------------------------------------
#サーバー退出メッセージ
left_log_channel_ids = {} # 空の辞書を作成

@bot.command()
@commands.has_permissions(administrator=True)
async def leftlog(ctx, channel: discord.TextChannel):
    left_log_channel_ids[ctx.guild.id] = channel.id # 辞書に保存
    embed = discord.Embed(title="ログ出力先設定完了", description=f"ログ出力先を {channel.mention} に設定しました。", color=0x00ff00)
    await ctx.send(embed=embed)

@leftlog.error
async def leftlog_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_member_remove(member):
    left_log_channel_id = left_log_channel_ids.get(member.guild.id) # 辞書からログ出力先のチャンネルIDを取得
    if left_log_channel_id is not None:
        left_log_channel = member.guild.get_channel(left_log_channel_id)
        if left_log_channel is not None:
            await asyncio.sleep(3) # 3秒待つ
            now = datetime.datetime.now()
            if now.hour < 12:
                time_str = now.strftime("%Y/%m/%d 午後%I:%M")
            else:
                time_str = now.strftime("%Y/%m/%d 午前%I:%M")
            embed = discord.Embed(title="さようなら", color=0xff0000)
            embed.add_field(name="ユーザー", value=member.mention, inline=False)
            embed.add_field(name="時間", value=time_str, inline=False)
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            else:
                embed.set_thumbnail(url=member.default_avatar.url)
            await left_log_channel.send(embed=embed)

#-------------------------------------------------------------------------------------------------------------
#チケット発行機能
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = discord.Embed(title="お問い合わせ", description=":tickets:を押すとチケットを発行します。\n発行後メンションしたチャンネルにて質問などをご記入下さい。", color=0x00ff00)

    message = await ctx.channel.send(embed=embed)
    await message.add_reaction("🎟️")


@ticket.error
async def ticket_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="エラー", description="このコマンドを実行するには管理者権限が必要です。", color=0xff0000)
        await ctx.send(embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if not user.bot and reaction.message.author == bot.user and str(reaction.emoji) == "🎟️":
        overwrites = {
            reaction.message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            reaction.message.guild.me: discord.PermissionOverwrite(read_messages=True),
            user: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await reaction.message.guild.create_text_channel(name=f"|🎫-{user.display_name}|", overwrites=overwrites)

        message = await reaction.message.channel.fetch_message(reaction.message.id)
        await message.remove_reaction("🎟️", user)

        embed = discord.Embed(title="チケット作成完了", description=f"{user.mention} さんのチケットが作成されました。\n問い合わせが終わったら:x:を押してチケットを閉じてください", color=0x00ff00)
        message = await channel.send(embed=embed)
        await message.add_reaction("❌")

    elif not user.bot and reaction.message.author == bot.user and str(reaction.emoji) == "❌":
        channel = reaction.message.channel
        await channel.delete()

#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#ワードブロック

server_settings = {}


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # サーバーごとの設定を取得
    guild_id = message.guild.id
    if guild_id not in server_settings:
        server_settings[guild_id] = {"timeout": 60, "blockwords": []}
    timeout = server_settings[guild_id]["timeout"]
    blockwords = server_settings[guild_id]["blockwords"]

    # ブロックワードに該当するメッセージを削除
    if any(word in message.content for word in blockwords):
        await message.delete()

        # 権限削除処理
        for channel in message.guild.channels:
            overwrites = channel.overwrites_for(message.author)
            overwrites.send_messages = False
            if isinstance(channel, discord.VoiceChannel):
                overwrites.connect = False
            await channel.set_permissions(message.author, overwrite=overwrites)

        # 切断処理
        for vc in message.guild.voice_channels:
            for member in vc.members:
                if member == message.author:
                    await member.move_to(None)

        # タイムアウトメッセージ送信
        timeout_embed = discord.Embed(
            title="タイムアウト",
            description=f"<@{message.author.id}> が不適切な文章を送信したため{timeout}秒タイムアウトになりました。",
            color=discord.Color.red()
        ).set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        await message.channel.send(embed=timeout_embed)

        # タイムアウト処理
        await asyncio.sleep(timeout)

        # 権限戻し処理
        for channel in message.guild.channels:
            await channel.set_permissions(message.author, overwrite=None)

        # タイムアウト終了メッセージ送信
        end_embed = discord.Embed(
            title="タイムアウト終了",
            description=f"<@{message.author.id}> のタイムアウトが終了しました。",
            color=discord.Color.green()
        ).set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        await message.channel.send(embed=end_embed)

    else:
        # コマンド処理
        await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def wordtimeout(ctx, seconds: int):
    """タイムアウト時間を設定します。"""
    guild_id = ctx.guild.id
    server_settings[guild_id]["timeout"] = seconds
    await ctx.send(f"タイムアウト時間を{seconds}秒に設定しました。")

@wordtimeout.error
async def wordtimeout_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="エラー",
            description="このコマンドは管理者権限を持っているユーザーのみが実行できます。",
            color=discord.Color.red()
        ))

@bot.command()
@commands.has_permissions(administrator=True)
async def blockword(ctx, *words):
    """ブロックする単語を設定します。"""
    guild_id = ctx.guild.id
    server_settings[guild_id]["blockwords"] = list(words)
    await ctx.send(f"ブロックする単語を{', '.join(words)}に設定しました。")

@blockword.error
async def blockword_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="エラー",
            description="このコマンドは管理者権限を持っているユーザーのみが実行できます。",
            color=discord.Color.red()
        ))

#Wordreset
@bot.command()
@commands.has_permissions(administrator=True)
async def wordreset(ctx):
    """登録したブロックワードをリセットします。"""
    guild_id = ctx.guild.id
    server_settings[guild_id]["blockwords"] = []
    await ctx.send("ブロックワードをリセットしました。")

@wordreset.error
async def wordreset_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="エラー",
            description="このコマンドは管理者権限を持っているユーザーのみが実行できます。",
            color=discord.Color.red()
        ))

@bot.command()
async def wordlist(ctx):
    """登録されているブロックワードとタイムアウト時間を表示します。"""
    guild_id = ctx.guild.id
    timeout = server_settings[guild_id]["timeout"]
    blockwords = server_settings[guild_id]["blockwords"]
    embed = discord.Embed(
        title="ブロックワードとタイムアウト時間",
        description=f"タイムアウト時間: {timeout}秒\nブロックワード: {', '.join(blockwords)}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

#--------------------------------------------------------------------------------------------------------------------------
#help機能
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="cookingbotの使い方", description="リアクションを押すとDMにてコマンド一覧が送信されます。", color=discord.Color.blue())
    embed.add_field(name="🔧 管理者用コマンド", value="サーバーを管理する人向けのコマンドです。", inline=False)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🔧")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return

    channel = await bot.fetch_channel(payload.channel_id)
    user = await bot.fetch_user(payload.user_id)
    message = await channel.fetch_message(payload.message_id) # type: ignore

    if payload.emoji.name == "🔧":
        embed = discord.Embed(
            title="管理者用コマンドの説明",
            description="以下は、管理者用コマンドの説明です。",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="`?chatoff`",
            value="メッセージを送信したチャンネルのメッセージ送信権限を管理者のみにします。",
            inline=False
        )
        embed.add_field(
            name="`?chaton`",
            value="メッセージを送信したチャンネルのメッセージ送信権限をeveryoneにします。",
            inline=False
        )
        embed.add_field(
            name="`?clear`",
            value="メッセージを送信したチャンネルのログをすべて削除します。",
            inline=False
        )
        embed.add_field(
            name="`?embedded`",
            value="指定したメッセージを埋め込みでbotが送信します。形式は以下の通りです`?embedded タイトル 文章`",
            inline=False
        )
        embed.add_field(
            name="`?membercount`",
            value="serverの参加人数を表示するチャンネルを作成します。",
            inline=False
        )
        embed.add_field(
            name="`?rollpanel`",
            value="リアクションを押すとそれに対応したロールが付与されます。形式は以下の通りです`?rollpanel @ロール1 @ロール2`ロールは最大９個までです。",
            inline=False
        )
        embed.add_field(
            name="`?verify`",
            value="リアクションを押すと指定したろーるが付与されます。形式は以下の通りです`?verify @ロール` ロールは１個だけ指定可能です。",
            inline=False
        )
        embed.add_field(
            name="`?giveaway`",
            value="プレゼント企画を開催できます。形式は以下の通りです`?giveaway プレゼント内容 時間 当選人数` 時間はs m h dで表してください。",
            inline=False
        )
        embed.add_field(
            name="`?voicelog`",
            value="通話のログを監視できます。形式は以下の通りです`?voicelog #チャンネル` ",
            inline=False
        )
        embed.add_field(
            name="`?dellog`",
            value="メッセージの削除ログを監視できます。形式は以下の通りです`?dellog #チャンネル`",
            inline=False
        )
        embed.add_field(
            name="`?joinlog`",
            value="サーバーの参加ログを監視できます。形式は以下の通りです`?joinlog #チャンネル`",
            inline=False
        )
        embed.add_field(
            name="`?leftlog`",
            value="サーバーの退出ログを監視できます。形式は以下の通りです`?leftlog #チャンネル`",
            inline=False
        )
        embed.add_field(
            name="`?ticket`",
            value="チケットパネルを作成出来ます",
            inline=False
        )
        embed.add_field(
            name="`?blockword`",
            value="ブロックワードが設定できます。コマンドの形式は以下の通りです`?blockword ワード1 ワード2 ワード3`",
            inline=False
        )
        embed.add_field(
            name="`?wordtimeout`",
            value="ブロックワードを送信したユーザーをタイムアウトする時間を設定できます。コマンドの形式は以下の通りです`?wordtimeout 30",
            inline=False
        )
        embed.add_field(
            name="`?wordreset`",
            value="登録したブロックワードをリセットできます。",
            inline=False
        )
        embed.add_field(
            name="`?wordlist`",
            value="ワードブロックの一覧を表示できます。",
            inline=False
        )
        
        await user.send(embed=embed)

    if str(payload.emoji) in ["🔧",]:
     await message.remove_reaction(payload.emoji, user)

bot.run("MTA4NzMxODY4MjY4Mzg1MDc2Mg.G1cuUe.9c3ezAHftRDArVjP736B_If-gYrAW-Q_j2PU8s")