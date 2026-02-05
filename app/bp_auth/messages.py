"""User class for the application."""
from models.database import db


class Message():
    """
    Base class for all Messages in the system.

    This class represents a message and stores various details about the content of the message,
    the time when it was sent, at which group_chat the message is part of and the members of the group_chat.

    Attributes:
        message_id (int): Unique identifier for the message.
        group_name (str): name identifier of a group chat.
        members (str): usernames of the members of the group chat.
        sender_id (int): user_id of the sender of the message.
        sender_username (str): user_name of the sender of the message.
        time_sent (datetime): Timestamp of when the message was sent.
        contents (str): content of the message sent to the group chat.
    """



    def __init__(self, message_id, group_name, members, sender_id, sender_username, time_sent, contents):
        """
        Initialize a new Message object with provided information.

        Args:
            message_id (int): Unique identifier for the message.
            group_name (str): name identifier of a group chat.
            members (str): usernames of the members of the group chat.
            sender_id (int): user_id of the sender of the message.
            sender_username (str): user_name of the sender of the message.
            time_sent (datetime): Timestamp of when the message was sent.
            contents (str): content of the message sent to the group chat.
        """
        self.message_id = message_id
        self.group_name = group_name
        self.members = members
        self.sender_id = sender_id
        self.sender_username = sender_username
        self.time_sent = time_sent
        self.contents = contents



    @staticmethod
    def create(data):
        """
        Create a new message in the database.

        creates the message in the database and set the default values for the timestamp
        that represent the time when the message was sent.

        Args:
            data (dict): Dictionary containing user data such as group_name, members, 
                         sender_id, sender_username, contents.

        Returns:
            object: The newly created message record from the database.
        """

        message_data = {
            "group_name": data["group_name"],
            "members": data["members"],
            "sender_id": data["sender_id"],
            "sender_username": data["sender_username"],
            "contents": data["contents"]
        }

        # Call the database method to create the message and return the result
        return db.create_message(message_data)




    @staticmethod
    def get_message_by_id(message_id):
        """
        Retrieve a message by their ID.

        Args:
            message_id (int): The ID of the message to retrieve.

        Returns:
            Message: The message object if found, or None if not found.
        """
        # TODO: Change based on how db methods are implemented
        row = db.get_message_by_id(message_id)
        return Message(*row) if row else None


    @staticmethod
    def get_messages_by_group_name(group_name):
        """
        Get all messages of a specific group_name.

        Args:
            group_name (str): The group name/ group chat (identifier) to retrieve (e.g., 'rix_andrew', 'funtime2025').

        Returns:
            list: A list of Messages objects matching the given group_name.
        """
        rows = db.get_messages_by_group_name(group_name)
        return [{"sender_username": r[0], "contents": r[1], "time_sent": r[2], "members": r[3]} for r in rows]


    @staticmethod
    def get_group_name_by_member(member):
        """
        Get all group_name of a specific member.

        Args:
            member (str): The username of a user to retrieve (e.g., 'rix', 'andrew').

        Returns:
            list: A list of Group_Names matching the given member.
        """
        rows = db.get_group_name_by_member(member)
        group_list = []

        for row in rows:
            group_list.append(row)
    
        return group_list
