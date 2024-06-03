import discord

import os
from dotenv import load_dotenv
import random

from programClassifier import classify_program
from schoolClassifier import classify_school
from util import generate_tags

from embed import decision_verification, deletion_verification, decision_post, admission_statistics_post
from spreadsheet import get_applicant_years, get_sheet_and_row_by_message_id, add_to_spreadsheet, stats, delete_row_by_row_num, delete_decision_private

PROGRAM_CONFIDENCE_THRESHOLD = 10     # If program classification confidence is below this value, will not use classified value
SCHOOL_SIMILARITY_THRESHOLD = 55      # If school fuzzy match similarity is below this value, will not use matched value

"""
Load environment variables
"""
load_dotenv()  
bot = discord.Bot()
applicant_years = get_applicant_years()


"""
Create bot instance
"""
@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for /decisions"))


"""
Displays the bot's ping
"""
@bot.command(name="ping", description="Ping!")
async def ping(ctx):
    bot_latency = round(bot.latency*100)
    await ctx.respond(f"Pong!    ({bot_latency} ms)")


"""
Adds a decision to the spreadsheet after moderators approve
Takes School, Program, Status, Average, Date, Applicant type, Comments/Other as parameters
"""
@bot.command(name="decision", description="Record a university's decision to the spreadsheet.")
async def decision(
    ctx,
    school: discord.Option(str, description="The school you received a decision for."),                                                     # type: ignore
    program: discord.Option(str, description="The program you received a decision for."),                                                   # type: ignore
    status: discord.Option(str, description="The decision that was made.", choices=["Accepted", "Rejected", "Waitlisted", "Deferred"] ),    # type: ignore
    average: discord.Option(str, description="Your current top 6 average."),                                                                # type: ignore
    date: discord.Option(str, description="The date the decision was made."),                                                               # type: ignore
    applicant_type: discord.Option(str, description="Type of applicant.", choices=["101", "105D", "105F"] ),                                # type: ignore
    anonymous: discord.Option(bool, description="Select True appear anonymous on our records.", choices=[True, False], default=False),      # type: ignore
    other: discord.Option(str, required=False, default=None)                                                                                # type: ignore                 
):
    # Stop Timeouts
    await ctx.defer()

    # Create embed
    decision_verification_embed = await decision_verification(ctx, school, program, status, average, date, applicant_type, anonymous, other)

    # Send verification embed to #mod-queue channel with buttons
    mod_queue = bot.get_channel(int(os.environ.get("MOD_QUEUE")))
    await mod_queue.send(embed=decision_verification_embed, view=DecisionVerificationButtons())

    await ctx.respond("Information sent to moderators for review.  Check the decisions channel for updates.", ephemeral=True)

"""
Buttons that go under the decision verification embed for moderators
Approve allows the message to be sent to the decisions channel, Delete rejects the decision (troll/mistake)
"""
class DecisionVerificationButtons(discord.ui.View):

    ''' Approve Button - send decision to decisions channel to display if pressed '''
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def button_callback(self, button, interaction):
        await interaction.response.defer()      # Stop button click errors

        embed_fields = interaction.message.embeds[0].fields
        
        user_name, user_id, school, program, status, average, date, applicant_type = [embed_fields[i].value for i in range(8)]
        user = await bot.fetch_user(user_id)

        anonymous = True if "(Anonymous)" in user_name else False

        # Check if other is empty
        try:
            other = embed_fields[8].value
        except IndexError:
            other = None

        decision_display_embed = await decision_post(user, school, program, status, average, date, applicant_type, anonymous, other)

        # Send the decision display embed to the decisions channel
        decisions_log = bot.get_channel(int(os.environ.get("DECISIONS_LOG")))

        if not anonymous:
            message = await decisions_log.send(user.mention, embed=decision_display_embed)
        else:
            message = await decisions_log.send(embed=decision_display_embed)

        # React with random emoji to embed if accepted
        if status == "Accepted":
            await message.add_reaction(random.choice(["🤩", "🥳", "🎉", "🎊", "✨", "💯", "‼", "🔥"]))
        
        # Classify university and program if they meet the threshold
        classified_school = classify_school(school)[0] if classify_school(school)[1] > SCHOOL_SIMILARITY_THRESHOLD else school.lower()
        classified_program = classify_program(program)[0] if classify_program(program)[1] > PROGRAM_CONFIDENCE_THRESHOLD else program.lower()

        tags = generate_tags(classified_school, classified_program)

        # Add to spreadsheet
        await add_to_spreadsheet(user, school, program, status, average, date, applicant_type, anonymous, other, tags, message.id)

        # Delete the verification message
        try:
            await interaction.message.delete()
        except discord.errors.NotFound:
            pass

    ''' Reject button - delete decision if pressed '''
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def second_button_callback(self, button, interaction):
        await interaction.message.delete()
        

"""
Delete a decision from spreadsheet and decisions channel
Takes applicant year and message id as parameter
If anonymous, does not delete
"""
@bot.command(name="delete", description="Request deletion for one of your decisions from the spreadsheet and channel.")
async def delete(
    ctx,
    message_id: discord.Option(str, description="Message ID of your decision. Must not be anonymous.")                                  # type: ignore
):
    # Find decision in decisions channel/check if anonymous
    try:
        decisions_log = bot.get_channel(int(os.environ.get("DECISIONS_LOG")))
        decision_embed_message = await decisions_log.fetch_message(message_id)

        if decision_embed_message.mentions[0].id != ctx.author.id:
            await ctx.respond("You cannot delete someone else's decision.", ephemeral=True)
            return
        
    except discord.errors.NotFound: 
        await ctx.respond("Decision not found.", ephemeral=True)
        return
    except IndexError:
        await ctx.respond("You cannot delete an anonymous decision.", ephemeral=True)
        return

    embed_fields = decision_embed_message.embeds[0].fields

    user = ctx.author
    school_program = decision_embed_message.embeds[0].title
    school = school_program.split(" - ",1)[0]
    program = school_program.split(" - ",1)[1]
    status = embed_fields[0].value
    average = embed_fields[1].value
    applicant_year, row = get_sheet_and_row_by_message_id(message_id)

    if row is None:
        await ctx.respond("Decision not found.", ephemeral=True)
        return

    # Create embed
    deletion_verification_embed = await deletion_verification(user, school, program, status, average, applicant_year, row, message_id)

    # Send verification embed to #mod-queue channel with buttons
    mod_queue = bot.get_channel(int(os.environ.get("MOD_QUEUE")))
    await mod_queue.send(embed=deletion_verification_embed, view=DeletionVerificationButtons())

    await ctx.respond("Request sent to moderators for review.  You will receive a direct message upon deletion.", ephemeral=True)

"""
Buttons that go under the deletion verification embed for moderators
Approve deletes the decision from the spreadsheet and the corresponding message in the decisions channel, Delete rejects the request (mistake)
"""
class DeletionVerificationButtons(discord.ui.View):

    ''' Approve Button - delete decision in spreadsheet and decisions channel if pressed '''
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def button_callback(self, button, interaction):
        await interaction.response.defer()      # Stop button click errors

        embed_fields = interaction.message.embeds[0].fields
        
        user_id = embed_fields[1].value
        user = await bot.fetch_user(user_id)
        applicant_year = embed_fields[6].value
        row = embed_fields[7].value
        message_id = embed_fields[8].value

        # Delete entry from public spreadsheet
        await delete_row_by_row_num(applicant_year, row)

        # Update entry on private spreadsheet
        await delete_decision_private(message_id)

        # Delete the decision display embed message
        decisions_log = bot.get_channel(int(os.environ.get("DECISIONS_LOG")))
        decision_embed_message = await decisions_log.fetch_message(message_id)
        await decision_embed_message.delete()
        await interaction.message.delete()

        # DM User
        await user.send(f"**{bot.get_guild(int(os.environ.get('SERVER_ID'))).name}**: Decision deleted (Year: {applicant_year}, Decision ID: {message_id}).")


    ''' Reject button - delete request if pressed '''
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def second_button_callback(self, button, interaction):
        await interaction.message.delete()


"""
Query statistics from the spreadsheet
Takes School, Program, Applicant Type, Admission year as parameters
"""
@bot.command(name="statistics", description="See admission statistics for a program (101 only).")
async def statistics(
    ctx,
    school: discord.Option(str, description="The school that you want to see admission statistics for."),                               # type: ignore
    program: discord.Option(str, description="The program you want to see admission statistics for."),                                  # type: ignore
    applicant_year: discord.Option(str, description="Applicant Year", choices=applicant_years+["ALL"]),                                 # type: ignore
):
    # Stop timeouts
    await ctx.defer()

    # Classify university and program if they meet the threshold
    classified_school = classify_school(school)[0] if classify_school(school)[1] > SCHOOL_SIMILARITY_THRESHOLD else school.lower()
    classified_program = classify_program(program)[0] if classify_program(program)[1] > PROGRAM_CONFIDENCE_THRESHOLD else program.lower()
    label_found = True if classify_program(program)[1] > PROGRAM_CONFIDENCE_THRESHOLD and classify_school(school)[1] > SCHOOL_SIMILARITY_THRESHOLD else False

    tags = generate_tags(classified_school, classified_program)

    # Get stats data
    stat_info = await stats(school, program, applicant_year, tags)

    # Check if no data
    if stat_info is None:
        await ctx.respond(f"No data found. Searched for {tags}.")
        return

    # Create embed
    statistics_embed = admission_statistics_post(school, program, applicant_year, stat_info, label_found, tags)
    histogram = discord.File(stat_info["filename"])

    # Do not show graph if sample size is less than 1
    if stat_info["sample size"] > 1:
        await ctx.respond(embed=statistics_embed, file=histogram)
    else:
        await ctx.respond(embed=statistics_embed)


"""Run Bot"""
bot.run(os.getenv('TOKEN'))