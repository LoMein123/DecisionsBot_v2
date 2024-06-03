import discord
import datetime
import random

DECISION_COLORS = {
    "Accepted" : 0x1DBF38,      # Accepted   - Light Green
    "Rejected" : 0xB30012,      # Rejected   - Red
    "Waitlisted" : 0xFF7B00,    # Waitlisted - Orange
    "Deferred" : 0xEBEB07,      # Deferred   - Yellow
    "Delete" : 0x961f02,        # Deletion   - Brown
    "Statistics" : 0x0c71e0     # Statistics - Blue
}

"""
Creates and returns an embed object for moderators to verify decisions
"""
async def decision_verification(ctx, school, program, status, average, date, applicant_type, anonymous, other):

    embed = discord.Embed(
        title="Decision Verification Required",
        colour=DECISION_COLORS[str(status)],
        timestamp=datetime.datetime.utcnow()
        )

    embed.set_thumbnail(url=ctx.author.avatar.url)

    if anonymous:
        embed.add_field(name="User", value=f"{ctx.author.mention} (Anonymous)", inline=True)
    else:
        embed.add_field(name="User", value=ctx.author.mention, inline=True)

    embed.add_field(name="User ID", value=ctx.author.id, inline=True)
    embed.add_field(name="School", value=school, inline=True)
    embed.add_field(name="Program",  value=program, inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Average", value=average, inline=True)
    embed.add_field(name="Decision Made On", value=date, inline=True)
    embed.add_field(name="101/105", value=applicant_type, inline=True)

    if other is not None:
        embed.add_field(name="Other", value=other, inline=True)

    return embed


"""
Creates and returns an embed object for moderators to verify decision deletions
"""
async def deletion_verification(user, school, program, status, average, applicant_year, row, message_id):

    embed = discord.Embed(
        title="Deletion Verification Required",
        colour=DECISION_COLORS["Delete"], # Brown for decision deletion
        timestamp=datetime.datetime.utcnow()
        )

    embed.set_thumbnail(url=user.avatar.url)

    embed.add_field(name="User", value=user.mention, inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="School", value=school, inline=True)
    embed.add_field(name="Program",  value=program, inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Average", value=average, inline=True)
    embed.add_field(name="Applicant Year", value=applicant_year, inline=True)
    embed.add_field(name="Row Number", value=row, inline=True)
    embed.add_field(name="Message ID", value=message_id, inline=True)

    return embed


"""
Creates and returns an embed object to display university decisions
"""
async def decision_post(user, school, program, status, average, date, applicant_type, anonymous, other):

    school_program = school + " - " + program

    embed = discord.Embed(
        title=school_program,
        colour=DECISION_COLORS[status],
        timestamp=datetime.datetime.utcnow()
        )

    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Average", value=average, inline=True)
    embed.add_field(name="Decision Made On", value=date, inline=True)
    embed.add_field(name="101/105", value=applicant_type, inline=True)

    if other is not None:
        embed.add_field(name="Other", value=other, inline=True)

    if anonymous:
        # Set random default pfp as embed thumbnail
        embed.description = "Anonymous"
        embed.set_thumbnail(url=f'https://archive.org/download/discordprofilepictures/discord{random.choice(["blue", "green", "grey", "red", "yellow"])}.png')  
    else:
        embed.description = user.name
        embed.set_thumbnail(url=user.avatar.url) 

    return embed


"""
Creates and returns an embed object for to display admission statistics
"""
def admission_statistics_post(school, program, applicant_year, stat_info, label_found, tags):

    # calculated applicant year is bandaid fix for ALL
    average, median, sample_size, calculated_applicant_year, filename = stat_info.values()

    embed = discord.Embed(
        title=f"101 Admission averages for {school} {program} for {calculated_applicant_year}",
        description=f"Average: {average}\nMedian: {median}\nSample Size: {sample_size}",
        colour=DECISION_COLORS["Statistics"], # Blue for admission statistics
        timestamp=datetime.datetime.utcnow()
        )

    if int(sample_size) > 1:
        embed.set_image(url=f"attachment://{filename}")

    # Create footer
    search_info = ""

    if label_found == False:
        search_info += f"Could not classify program. "

    search_info += f"Searched for: {tags}.  **Disclaimer: This information is not representitive of all applicants."
    embed.set_footer(text=search_info)

    return embed