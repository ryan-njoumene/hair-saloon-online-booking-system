"""Report class for managing feedback reports in the application."""

from models.database import db


class Report:
    """Base class representing a feedback report in the system."""

    def __init__(self, report_id, appointment_id, status,
                 feedback_client, feedback_professional, date_report=None):
        """
        Initialize a new Report instance.

        Args:
            report_id (int): Unique identifier for the report.
            appointment_id (int): ID of the associated appointment.
            status (str): Current status of the report (e.g., open, closed).
            feedback_client (str): Client's feedback text.
            feedback_professional (str): Professional's response text.
            date_report (datetime, optional): Date the report was created.
        """
        self.report_id = report_id
        self.appointment_id = appointment_id
        self.status = status
        self.feedback_client = feedback_client
        self.feedback_professional = feedback_professional
        self.date_report = date_report

    @staticmethod
    def create(data):
        """
        Create a new report entry in the database.

        Args:
            data (dict): Dictionary containing report details.

        Returns:
            int: ID of the newly created report.
        """
        # Prepare report data for insertion, defaulting status if unspecified
        report_data = {
            "appointment_id": data.get("appointment_id"),
            "status": data.get("status", "Unknown"),
            "feedback_client": data.get("feedback_client"),
            "feedback_professional": data.get("feedback_professional", None)
        }

        return db.add_report(report_data)

    @staticmethod
    def get_report_by_id(report_id):
        """
        Retrieve a report from the database by its ID.

        Args:
            report_id (int): Unique identifier of the report.

        Returns:
            Report: Report instance if found, otherwise None.
        """
        # Retrieve report data from the database by ID
        row = db.get_report_by_id(report_id)
        return Report(*row) if row else None

    @staticmethod
    def get_report_by_appointment(appointment_id):
        """
        Retrieve a report based on associated appointment ID.

        Args:
            appointment_id (int): Unique identifier of the appointment.

        Returns:
            Report: Report instance if found, otherwise None.
        """
        # Retrieve report data from database by appointment ID
        row = db.get_report_by_appointment(appointment_id)
        return Report(*row) if row else None

    @staticmethod
    def get_all_report(appointment_id=None):
        """
        Retrieve all reports from the database.

        Args:
            appointment_id (int, optional): Currently unused parameter.

        Returns:
            list: List of Report instances, or None if no reports exist.
        """
        # Fetch all report entries from the database
        reports_list = []
        all_rows = db.get_all_report()

        # Create Report instances for each retrieved row
        for row in all_rows:
            reports_list.append(Report(*row))

        return reports_list if reports_list else None
