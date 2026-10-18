import discord
import sqlite3

#----------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------

def member_already_registered(discord_id):

    connection = sqlite3.connect(
        "gwcbot.db",
        timeout=10
    )

    connection.execute(
        "PRAGMA busy_timeout = 10000"
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT member_id
        FROM Members
        WHERE discord_id = ?
        """,
        (discord_id,)
    )

    member = cursor.fetchone()

    connection.close()

    return member is not None

def clean_optional(value):
    value = value.strip()

    if value == "" or value.lower() == "n/a":
        return None

    return value


def save_member_to_database(registration_data):

    connection = None

    try:
        connection = sqlite3.connect(
            "gwcbot.db",
            timeout=10 #wait 10seconds before crash
        )

        # Wait briefly if another operation is using the database
        connection.execute("PRAGMA busy_timeout = 10000")

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO Members (
                discord_id,
                full_name,
                member_dob,
                ucf_email,
                major,
                phone_number,
                member_bio,
                additional_info
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registration_data["discord_id"],
                registration_data["full_name"],
                registration_data["dob"],
                registration_data["ucf_email"],
                registration_data["major"],
                registration_data["phone_number"],
                registration_data["bio"],
                registration_data["additional_info"]
            )
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:
        return False

    except sqlite3.OperationalError as error:
        print("DATABASE ERROR:", error)
        return None

    finally:
        if connection is not None:
            connection.close()

# --------------------------------------------------
# REGISTRATION — PART 2 OF 2
# --------------------------------------------------

class Part2Modal(
    discord.ui.Modal,
    title="Member Registration — Part 2 of 2"
):

    def __init__(self, registration_data, user_id):
        super().__init__()

        self.registration_data = registration_data
        self.user_id = user_id

    bio = discord.ui.TextInput(
        label="Would you like to give us a bio?",
        placeholder="Tell us a little about yourself!",
        required=False,
        style=discord.TextStyle.paragraph
    )

    additional_info = discord.ui.TextInput(
        label="Anything else you'd like us to know?",
        placeholder="Pronouns or anything else important to you!",
        required=False,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "This registration belongs to another member.",
                ephemeral=True
            )

            return

        self.registration_data["bio"] = clean_optional(
            self.bio.value
        )

        self.registration_data["additional_info"] = clean_optional(
            self.additional_info.value
        )

        print()
        print("FINAL REGISTRATION:")
        print(self.registration_data)
        print()

        # Save completed registration
        saved = save_member_to_database(
            self.registration_data
        )

        if saved is False:

            await interaction.response.send_message(
                "❌ **Error: Member already registered!**",
                ephemeral=True,
                delete_after=300
            )

            return

        if saved is None:

            await interaction.response.send_message(
                "⚠️ **Database is currently busy. Please try again in a moment.**",
                ephemeral=True,
                delete_after=300
            )

            return

        await interaction.response.send_message(
            "🎉 Member registration complete! "
            "Thank you for registering with Girls Who Code @ UCF!",
            ephemeral=True,
            delete_after=300
        )
# --------------------------------------------------
# CONTINUE TO PART 2 BUTTON
# --------------------------------------------------

class ContinueRegistrationView(discord.ui.View):

    def __init__(self, registration_data, user_id):
        super().__init__(timeout=300)

        self.registration_data = registration_data
        self.user_id = user_id

    @discord.ui.button(
        label="Continue Registration",
        style=discord.ButtonStyle.secondary # grey button
    )
    async def continue_registration(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # Prevent another member from continuing
        # somebody else's registration
        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "This registration belongs to another member.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            Part2Modal(
                self.registration_data,
                self.user_id
            )
        )


# --------------------------------------------------
# REGISTRATION — PART 1 OF 2
# --------------------------------------------------

class Part1Modal(
    discord.ui.Modal,
    title="Member Registration — Part 1 of 2"
):

    def __init__(self, user_id):
        super().__init__()

        self.user_id = user_id

        # One dictionary holds the entire registration
        self.registration_data = {
            "discord_id": user_id
        }

    name = discord.ui.TextInput(
        label="What is your first and last name?",
        placeholder="Example: Gabriela Palitot",
        required=True
    )

    dob = discord.ui.TextInput(
        label="What is your date of birth?",
        placeholder="Example: 12/19/1998",
        required=False
    )

    ucf_email = discord.ui.TextInput(
        label="What is your UCF Email?",
        placeholder="Example: you123456@ucf.edu or N/A",
        required=False
    )

    major = discord.ui.TextInput(
        label="What is your major?",
        placeholder="Example: Computer Science",
        required=False
    )

    phone_number = discord.ui.TextInput(
        label="Would you like to share your phone number?",
        placeholder="Example: 123-456-7890 or N/A",
        required=False
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        # Make sure the correct member submitted it
        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "This registration belongs to another member.",
                ephemeral=True
            )

            return

        # Save Part 1 answers
        self.registration_data["full_name"] = (
            self.name.value.strip()
        )

        self.registration_data["dob"] = clean_optional(
            self.dob.value
        )

        self.registration_data["ucf_email"] = clean_optional(
            self.ucf_email.value
        )

        self.registration_data["major"] = clean_optional(
            self.major.value
        )

        self.registration_data["phone_number"] = clean_optional(
            self.phone_number.value
        )

        print("PART 1:")
        print(self.registration_data)

        await interaction.response.send_message(
            "✅ Part 1 saved! Click below to finish your registration.",
            view=ContinueRegistrationView(
                self.registration_data,
                self.user_id
            ),
            ephemeral=True,
            delete_after=300
        )


# --------------------------------------------------
# COMPLETE REGISTRATION BUTTON
# --------------------------------------------------

class RegistrationView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)

        self.user_id = user_id

    @discord.ui.button(
        label="Start Registration 🤍",
        style=discord.ButtonStyle.success  # green button
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # Make sure this button belongs to this user
        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "This registration button belongs to another member.",
                ephemeral=True
            )

            return

        # Check database before opening registration
        if member_already_registered(interaction.user.id):

            await interaction.response.send_message(
                "❌ **Error: Member already registered!**",
                ephemeral=True,
                delete_after=300
            )

            return

        # User is not registered yet, so open Part 1
        await interaction.response.send_modal(
            Part1Modal(self.user_id)
        )
