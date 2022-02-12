# RT Lib - Typed

from typing import Union, Dict, List

from discord.ext import commands

from aiohttp import ClientSession
from aiomysql import Pool

from .mysql_manager import MySQLManager
from data import data, Colors, is_admin
from .rtc import ExtendedRTC


class RT(commands.AutoShardedBot):
    mysql: MySQLManager
    pool: Pool
    test: bool
    data: data # type: ignore
    admins: List[int]
    session: ClientSession
    secret: dict
    is_admin: is_admin # type: ignore
    colors: dict
    Colors: Colors
    rtc: ExtendedRTC

    def print(self, *args, **kwargs) -> None:
        return print(f"[Backend]", *args, **kwargs)

    def get_ip(self) -> str:
        return "localhost" if self.test else "146.59.153.178"

    def get_url(self) -> str:
        return f"http://{self.get_ip()}"

    async def close(self) -> None:
        self.print("Closing...")
        self.dispatch("close", self.loop)
        await super().close()
        self.print("Bye")

    def get_website_url(self) -> str:
        return "http://localhost/" if self.test else "https://rt-bot.com/"


sendableString = Union[str, Dict[str, str]]