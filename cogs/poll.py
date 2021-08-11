# RT - Poll (Vote)

from discord.ext import commands, tasks
import discord

from typing import Callable, Tuple, List, Dict
from emoji import UNICODE_EMOJI_ENGLISH
from asyncio import create_task


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data
        self.emojis = [chr(0x1f1e6 + i) for i in range(26)]
        self.queue: Dict[str, discord.RawReactionActionEvent] = {}
        self.panel_updater.start()

    @commands.command(
        extras={"headding": {"ja": "投票パネルを作成します。", "en": "..."},
                "parent": "ServerPanel"},
        aliases=["vote"]
    )
    @commands.cooldown(1, 8)
    async def poll(self, ctx, title, only_one: bool, *, content):
        """!lang ja
        --------
        投票パネルを作成します。
        
        Parameters
        ----------
        title : str
            投票パネルのタイトルです。
        only_one : bool
            これをonにした場合は投票を一人一票までとします。  
            投票を一人一票としない場合はoffを入れてください。
        content : str
            改行で分けた投票に入れる項目です。  
            行の最初に絵文字を置くとその絵文字が投票パネルに使われます。  
            もし絵文字を置かない場合は自動で英文字の絵文字が割り振られます。

        Examples
        --------
        ```
        rt!poll 好きな人は？ on
        😊 tasuren
        ミスティックガール
        吹雪ちゃん
        NYN姉貴
        🤭 野獣先輩
        ```
        好きな人を問う投票パネルを一人一票までとして作ります。
        
        !lang en
        --------
        上にあるものの英語版です。"""
        description, emojis = self.make_description(content)

        embed = discord.Embed(
            title=title,
            description=description,
            color=ctx.author.color
        )
        embed.set_footer(text="※連打防止のため結果の反映は数秒遅れます。")
        mes = await ctx.webhook_send(
            "".join(("RT投票パネル", " (一人一票)" if only_one else "", "\n📊 **[...]**")),
            wait=True, embed=embed, username=ctx.author.display_name,
            avatar_url=ctx.author.avatar.url,
        )
        for emoji in emojis:
            try:
                await mes.add_reaction(emoji)
            except discord.ext.commands.errors.CommandInvokeError:
                await ctx.reply(f"{emoji}が見つかりませんでした。")

    def make_description(self, content: str, on_integer: Callable = None) -> Tuple[str, List[str]]:
        # 渡された情報から投票パネルの説明に入れる文字列を作成する。
        description, i, emojis, emoji = "", -1, [], ""
        index, did = int(on_integer is not None), False

        for line in content.splitlines():
            if line and line != "\n":
                # もし初期状態の作成時ではないならindexを0じゃないのに変更しておく。
                if index and not did:
                    index = line.find("` ") + 2
                    did = True

                i += 1
                # 絵文をを取り出す。絵文字がないなら絵文字を用意する。
                if line[index] == "<" and ">" in line and line.count(":") > 1:
                    # もし外部絵文なら。
                    emojis.append(line[line.find("<"):line.find(">") + 1])
                elif line[index] in UNICODE_EMOJI_ENGLISH:
                    # もし普通の絵文字なら。
                    emojis.append(line[index])
                elif line[index] == self.emojis[i]:
                    emojis.append(line[index])
                else:
                    # もし絵文字がないなら作る。(ABCの絵文字。)
                    emojis.append((emoji := self.emojis[i]))
                    line = emoji + " " + line

                description += (f"`{0 if on_integer is None else on_integer(emojis[-1])}` "
                                + line[index:] + "\n")
        del content, i, emoji
        return description, emojis

    def check_panel(self, payload: discord.RawReactionActionEvent) -> bool:
        # RTの投票パネルか確認するための関数です。
        return (payload.message.content.startswith("RT投票パネル") and not payload.member.bot
                and payload.message.guild and payload.message.embeds
                and any(str(payload.emoji) == str(reaction.emoji)
                        for reaction in payload.message.reactions))

    def graph(self, p: dict, size: int = 35) -> str:
        # グラフを作るための関数です。
        r, t = '[', len(p)

        for n in list(p.keys()):
            p[n] = int(p[n] / t * size)
            if p[n] % 2 == 0:
                p[n] += 1

            if p[n] > 1:
                r += '<'
            if p[n] > 3:
                r += '=' * int((p[n] - 3 if p[n] - 3 > 0 else 0) / 2)
            r += n
            if p[n] > 3:
                r += '=' * int((p[n] - 3) / 2)
            if p[n] > 1:
                r += '>'
        return r + ']'

    async def update_panel(self, payload: discord.RawReactionActionEvent):
        # RTの投票パネルをアップデートする。
        embed = payload.message.embeds[0]
        emojis = {str(reaction.emoji): reaction.count - 1
                  for reaction in payload.message.reactions}
        # 最大桁数を数える。
        before = 1
        for key in emojis:
            if before < (now := len(str(emojis[key]))):
                before = now
        # Embedを編集する。
        description, _ = self.make_description(
            embed.description, lambda emoji: str(emojis[emoji]).zfill(before)
        )
        if description != embed.description:
            # もしカウントが変わっているならメッセージを編集する。
            embed.description = description
            wb = discord.utils.get(
                await payload.message.channel.webhooks(), name="RT-Tool")
            if wb:
                await wb.edit_message(
                    payload.message_id, embed=embed,
                    content="".join(
                        (payload.message.content[:payload.message.content.find("\n")],
                         "\n📊 **", self.graph(emojis), "**"))
                )
        del description, emojis

    def cog_unload(self):
        self.panel_updater.cancel()

    @tasks.loop(seconds=5)
    async def panel_updater(self):
        # キューにあるpayloadからパネルを更新する。
        # 連打された際に連打全部に対応して編集するようなことが起きないように。
        for cmid in list(self.queue.keys()):
            create_task(self.update_panel(self.queue[cmid]))
            del self.queue[cmid]

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload: discord.RawReactionActionEvent):
        if self.bot.is_ready():
            if self.check_panel(payload):
                if payload.event_type == "REACTION_ADD":
                    # もし一人一票までなら投票できるかチェックをする。
                    if "一" in payload.message.content:
                        users = len(
                            [reaction for reaction in payload.message.reactions
                             if any(user.id == payload.member.id
                                    for user in await reaction.users().flatten())]
                        )
                        if users > 1:
                            return
                self.queue[f"{payload.channel_id}.{payload.message_id}"] = payload

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.on_full_reaction_add(payload)


def setup(bot):
    bot.add_cog(Poll(bot))