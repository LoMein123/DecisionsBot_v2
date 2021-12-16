import discord
import gspread
from spreadsheet import pull_channel
from dotenv import load_dotenv
import os
import interactions
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option, create_choice
from embed import create_embed, add_field

load_dotenv()

# Intents
intents = discord.Intents().default()
intents.members = True
intents.reactions = True

# Bot Instance
client = discord.Client(intents=intents)
slash = SlashCommand(client, sync_commands=True)

# Service Account
service_account = gspread.service_account(f"{os.getcwd()}/service_account.json")


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # await pull_channel(client, 846891548171173928)


@slash.slash(
    name="decision",
    description="Record a decision.",
    guild_ids=[int(os.environ.get("GUILD"))],
    options=[
        create_option(
            name="school",
            description="The school that a decision was made for.",
            option_type=3,
            required=True,
        ),
        create_option(
            name="program",
            description="The program you applied to.",
            option_type=3,
            required=True,
        ),
        create_option(
            name="status",
            description="Decision Type",
            option_type=3,
            required=True,
            choices=[
                create_choice(name="Accepted", value="Accepted"),
                create_choice(name="Rejected", value="Rejected"),
                create_choice(name="Waitlisted", value="Waitlisted"),
                create_choice(name="Deferred", value="Deferred"),
            ],
        ),
        create_option(
            name="average",
            description="Your top 6 average",
            option_type=3,
            required=True,
        ),
        create_option(
            name="date",
            description="The date you were given a decision.",
            option_type=3,
            required=True,
        ),
        create_option(
            name="type",
            description="Applicant Type",
            option_type=3,
            required=True,
            choices=[
                create_choice(name="101 (Ontario)", value="101"),
                create_choice(name="105 (International)", value="105F"),
                create_choice(name="105 (Domestic -> Not Ontario)", value="105D"),
            ],
        ),
        create_option(
            name="other",
            description="Other information you want to provide",
            option_type=3,
            required=False,
        ),
    ],
)
async def _decision(ctx, school, program, status, average, date, type, other=None):

    colour = "magenta"
    if status == "Accepted":
        colour = "light_green"
    elif status == "Waitlisted":
        colour = "orange"
    elif status == "Deferred":
        colour = "yellow"
    elif status == "Rejected":
        colour = "red"

    embed = create_embed("Decision Verification Required", "", colour)
    add_field(embed, "User", ctx.author.mention, True)
    add_field(embed, "User ID", ctx.author.id, True)
    add_field(embed, "School", school, True)
    add_field(embed, "Program", program, True)
    add_field(embed, "Status", status, True)
    add_field(embed, "Average", average, True)
    add_field(embed, "Decision Made On", date, True)
    add_field(embed, "101/105", type, True)
    if other:
        add_field(embed, "Other", other, True)
    else:
        add_field(embed, "Other", "None", True)

    mod_queue = client.get_channel(int(os.environ.get("MOD_QUEUE")))
    message = await mod_queue.send(embed=embed)

    for emoji in ["✅", "❌"]:
        await message.add_reaction(emoji)

    await ctx.send("Information send to moderators for review.")


@client.event
async def on_raw_reaction_add(ctx):
    if ctx.member.bot:
        return

    message = await client.get_channel(ctx.channel_id).fetch_message(ctx.message_id)

    if int(os.environ.get("MOD_QUEUE")) != int(ctx.channel_id):
        return

    message_embeds = message.embeds[0]

    if message_embeds.title != "Decision Verification Required":
        return

    other = None

    if ctx.emoji.name == "❌":
        await message.delete()
        return
    elif ctx.emoji.name == "✅":
        embeds = message_embeds.fields
        user_id = embeds[1].value
        school = embeds[2].value
        program = embeds[3].value
        status = embeds[4].value
        average = embeds[5].value
        date_of_decision = embeds[6].value
        app_type = embeds[7].value
        other = embeds[8].value

    if other == "None":
        other = None

    user = client.get_user(int(user_id))

    program_school = f"{school} - {program}"

    colour = "orange"
    if status == "Accepted":
        colour = "light_green"
    elif status == "Waitlisted":
        colour = "orange"
    elif status == "Deferred":
        colour = "yellow"
    elif status == "Rejected":
        colour = "red"

    embed = create_embed(
        f"{program_school}", f"{user.name}#{user.discriminator}", colour
    )
    add_field(embed, "Status", status, True)
    add_field(embed, "Average", average, True)
    add_field(embed, "Decision Made On", date_of_decision, True)
    add_field(embed, "Applicant Type", app_type, True)
    if other is not None:
        add_field(embed, "Other", other, True)
    embed.set_thumbnail(url=user.avatar_url)

    channel = client.get_channel(int(os.environ.get("DECISIONS_CHANNEL")))
    sheet = service_account.open_by_key(os.environ.get("SHEETS_KEY")).worksheet(
        "Decisions"
    )

    await channel.send(f"{user.mention}", embed=embed)

    user_str = f"{user.name}#{user.discriminator}"

    # Adding to worksheet
    wsheet_list = [
        status,
        school,
        program,
        average,
        date_of_decision,
        app_type,
        user_str,
    ]
    if other is not None:
        wsheet_list.append(other)

    sheet.append_row(wsheet_list)

    await message.delete()


client.run(os.environ.get("BOT_TOKEN"))
