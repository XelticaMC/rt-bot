# RT - Rt Role

from typing import Union
from discord.embeds import E

from discord.ext import commands
import discord

from aiofiles import open as async_open
from collections import defaultdict
from ujson import loads, dumps
from os.path import exists


class RTRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = defaultdict(dict)
        if exists("data/rtrole.json"):
            try:
                with open("data/rtrole.json", "r") as f:
                    self.data.update(loads(f.read()))
            except Exception as e:
                print("Error on RTRole:", e)
        else:
            with open("data/rtrole.json", "w") as f:
                f.write(r"{}")

        if not getattr(self, "did", False):
            @bot.check
            async def has_role(ctx):
                if ctx.guild:
                    if (role := discord.utils.find(
                        lambda r: (
                            "RT-" in r.name or (
                                str(ctx.guild.id) in self.data
                                and str(r.id) in self.data[str(ctx.guild.id)]
                                and ctx.command.qualified_name in \
                                    self.data[str(ctx.guild.id)][str(r.id)].get(
                                        "commands", ""
                                    )
                            )
                        ), ctx.guild.roles
                    )):
                        return bool(ctx.author.get_role(role.id))
                return True
            self.did = True

    async def save(self):
        async with async_open("data/rtrole.json", "w") as f:
            await f.write(dumps(self.data, ensure_ascii=True, indent=2))

    @commands.group(
        aliases=["rtロール", "りつロール", "rr"], extras={
            "headding": {"ja": "RTを操作できる役職を設定します。", "en": "..."},
            "parent": "RT"
        }
    )
    async def rtrole(self, ctx):
        """!lang ja
        --------
        指定したコマンドを特定の役職を持っている人しか実行できないようにします。  
        `rt!rtrole`で現在設定されているRTロールのリストを表示します。

        Aliases
        -------
        rtロール, りつロール, rr

        Notes
        -----
        もし全てのコマンドを特定の役職を持っている人しか実行できないようにしたい場合は、`RT-`が名前の最初にある役職を作れば良いです。  
        例：`RT-操作権限`

        !lang en
        --------
        ..."""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    title="RT Role List",
                    description="\n".join(
                        f"{data['role_name']}：{data['commands']}`"
                        for data in self.data[str(ctx.guild.id)].values()
                        if data
                    ), color=self.bot.colors["normal"]
                )
            )

    @rtrole.command("set", aliases=["設定", "s"])
    @commands.has_permissions(administrator=True)
    async def set_(self, ctx, role: discord.Role, *, commands):
        """!lang ja
        --------
        RTロールを設定します。

        Parameters
        ----------
        role : 役職の名前またはメンション
            設定するRTロールの名前かメンションです。
        commands : str
            その役職を持っていないと実行できないコマンドの名前のです。(空白で複数指定できます。)

        Examples
        --------
        `rt!rtrole set ping-info専門の人 ping info`  
        pingとinfoコマンドを`ping-info専門の人`の役職を持っていないと実行できないようにします。

        !lang en
        --------
        ..."""
        if len(self.data[str(ctx.guild.id)]) <= 50:
            self.data[str(ctx.guild.id)][str(role.id)] = {
                "commands": commands, "role_name": role.name
            }
            await self.save()
            await ctx.reply("Ok")
        else:
            await ctx.reply("50個まで設定可能です。")

    @rtrole.command(aliases=["del", "rm", "remove", "削除"])
    @commands.has_permissions(administrator=True)
    async def delete(self, ctx, *, role: Union[discord.Role, str]):
        """!lang ja
        --------
        `rt!rtrole set`の逆です。

        Parameters
        ----------
        role : 役職のメンションか名前
            RTロールで設定した削除したいRTロールの役職の名前です。

        Aliases
        -------
        del, rm, remove, 削除

        !lang en
        --------
        ..."""
        if self.data[(gid := str(ctx.guild.id))]:
            removed = False
            if isinstance(role, str):
                for rid in list(self.data[gid].keys()):
                    if self.data[gid][rid].get("role_name", "") == role:
                        del self.data[gid][rid]
                        removed = True
            else:
                try:
                    del self.data[gid][str(role.id)]
                except KeyError:
                    pass
                else:
                    remoevd = True

            if removed:
                await self.save()
                await ctx.reply("Ok")
            else:
                await ctx.reply("その役職は設定されていません。")


def setup(bot: commands.AutoShardedBot):
    bot.add_cog(RTRole(bot))