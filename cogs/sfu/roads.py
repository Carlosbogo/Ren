"""SFU Utilities.

- Web cameras: see road conditions in realtime.
- Campus report: fetched from the Road Report API.
"""
from io import BytesIO
import datetime
import json
import requests
from bs4 import BeautifulSoup
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands.context import Context

from .base import SFUBase

WEBCAM_AQPOND = (
    "http://ns-webcams.its.sfu.ca/public/images/aqn-current.jpg"
    "?nocache=1&update=15000&timeout=1800000"
)
WEBCAM_BRH = "http://ns-webcams.its.sfu.ca/public/images/brhroof-current.jpg?nocache=1"
WEBCAM_GAGLARDI = (
    "http://ns-webcams.its.sfu.ca/public/images/gaglardi-current.jpg"
    "?nocache=0.8678792633247998&update=15000&timeout=1800000&offset=4"
)
WEBCAM_SBH = "http://ns-webcams.its.sfu.ca/public/images/sbhroof-current.jpg?nocache=1"
WEBCAM_SUB = (
    "http://ns-webcams.its.sfu.ca/public/images/aqsw-current.jpg"
    "?nocache=0.3346598630889852&update=15000&timeout=1800000"
)
WEBCAM_SUR = "https://cosmos.surrey.ca/TrafficCameraImages/enc_102_cityparkway_cam1.jpg"
WEBCAM_TFF = (
    "http://ns-webcams.its.sfu.ca/public/images/terryfox-current.jpg"
    "?nocache=1&update=15000&timeout=1800000"
)
WEBCAM_TRN = (
    "http://ns-webcams.its.sfu.ca/public/images/towern-current.jpg"
    "?nocache=1&update=15000&timeout=1800000"
)
WEBCAM_TRS = (
    "http://ns-webcams.its.sfu.ca/public/images/towers-current.jpg"
    "?nocache=0.9550930672504077&update=15000&timeout=1800000"
)
WEBCAM_UDN = (
    "http://ns-webcams.its.sfu.ca/public/images/udn-current.jpg"
    "?nocache=1&update=15000&timeout=1800000&offset=4"
)
WEBCAM_WMC = (
    "http://ns-webcams.its.sfu.ca/public/images/wmcroof-current.jpg"
    "?nocache=1&update=15000&timeout=1800000"
)

ROAD_API = "http://www.sfu.ca/security/sfuroadconditions/api/3/current"

CAMPUSES = "campuses"
BUR = "burnaby"
SUR = "surrey"
VAN = "vancouver"
ROADS = "roads"
STATUS = "status"
ANNOUNCE = "announcements"


class SFURoads(SFUBase):
    """Various SFU Utilities."""

    def __init__(self, bot: Red):
        super().__init__(bot)
        self.cameras = {
            "aqpond": WEBCAM_AQPOND,
            "brh": WEBCAM_BRH,
            "gag": WEBCAM_GAGLARDI,
            "sbh": WEBCAM_SBH,
            "sub": WEBCAM_SUB,
            "sur": WEBCAM_SUR,
            "tff": WEBCAM_TFF,
            "trn": WEBCAM_TRN,
            "trs": WEBCAM_TRS,
            "udn": WEBCAM_UDN,
            "wmc": WEBCAM_WMC,
        }
        # We need a custom header or else we get a HTTP 403 Unauthorized
        self.headers = {"User-agent": "Mozilla/5.0"}

        # Add commands to the sfu group defined in the base class
        self.camCommand = commands.Command(self.cam, name="cam")
        self.sfuGroup.add_command(self.camCommand)
        self.sfuGroup.add_command(commands.Command(self.report, name="report"))

    @commands.guild_only()
    async def cam(self, ctx: Context, cam: str = ""):
        """Show a SFU webcam image.

        Parameters:
        -----------
        cam: str
            One of the following short strings:
            aqpond: AQ Pond
            brh:    Barbara Rae Housing (Burnaby Residence)
            gag:    Gaglardi intersection
            sbh:    Shadbolt Housing (Burnaby Residence)
            sub:    AQ overlooking student union building
            sur:    Surrey Central intersection
            tff:    Terry Fox Field
            trn:    Tower Road North
            trs:    Tower Road South
            udn:    University Drive North
            wmc:    West Mall Centre (WMC) Roof
        """
        await ctx.trigger_typing()

        camera = self.cameras.get(cam.lower(), "help")
        if camera == "help":
            await self.bot.send_help_for(ctx, self.camCommand)
            return

        try:
            fetchedData = requests.get(camera, headers=self.headers)
            fetchedData.raise_for_status()
        except requests.exceptions.HTTPError:
            await ctx.send(":warning: This webcam is currently unavailable!")
            # self.logger.error(exc_info=True)
            return

        if not fetchedData.content:
            # Make sure we don't fetch a zero byte file
            await ctx.send(":warning: This webcam is currently unavailable!")
            return

        camPhoto = discord.File(BytesIO(fetchedData.content), filename="cam.jpg")
        await ctx.send(file=camPhoto)

    @commands.guild_only()
    async def report(self, ctx: Context):
        """Show the SFU Campus Report."""
        fetchedData = requests.get(ROAD_API)
        results = json.loads(fetchedData.content)

        embed = discord.Embed()
        embed.title = "SFU Campus Report"

        # We need to use BeautifulSoup to parse the HTML within the JSON.
        if results[CAMPUSES][BUR][ANNOUNCE]:
            announce = BeautifulSoup(results[CAMPUSES][BUR][ANNOUNCE], "html.parser").get_text()
            roads = results[CAMPUSES][BUR][ROADS][STATUS]
            burnAnnounce = "**__Roads__**:\n{}\n\n**__Announcements__**:" "\n{}".format(
                roads, announce
            )
        else:
            burnAnnounce = "No updates."

        if results[CAMPUSES][SUR][ANNOUNCE]:
            surreyAnnounce = BeautifulSoup(
                results[CAMPUSES][SUR][ANNOUNCE], "html.parser"
            ).get_text()
        else:
            surreyAnnounce = "No updates."

        if results[CAMPUSES][VAN][ANNOUNCE]:
            vanAnnounce = BeautifulSoup(results[CAMPUSES][VAN][ANNOUNCE], "html.parser").get_text()
        else:
            vanAnnounce = "No updates."

        embed.add_field(name="Burnaby", value=burnAnnounce)
        embed.add_field(name="Vancouver", value=vanAnnounce)
        embed.add_field(name="Surrey", value=surreyAnnounce)

        lastUpdated = datetime.datetime.fromtimestamp(results["lastUpdated"] / 1000).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        embed.set_footer(text="This report was last updated on {}".format(lastUpdated))
        await ctx.send(embed=embed)
