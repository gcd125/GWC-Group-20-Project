import sqlite3
import os


print(os.path.abspath("gwcbot.db"))

connection = sqlite3.connect("gwcbot.db")
cursor = connection.cursor()

cursor.execute("""
    SELECT
        member_id,
        member_role,
        discord_id,
        full_name,
        member_dob,
        ucf_email,
        major,
        phone_number,
        member_bio,
        additional_info,
        member_status,
        points_balance
    FROM Members
""")

members = cursor.fetchall()
print("Members found:", members)

for member in members:
    print(member)

connection.close()