from db.models import User, SentEmail
from extension import db


class UserManager:
    def add_user(self, email, position, location, job_type):
        user = User(email=email, position=position, location=location, job_type=job_type)
        if not self.user_exists(email, position, location):
            db.session.add(user)
            db.session.commit()

    def delete_user(self, email, position, location):
        user = self.user_exists(email=email, position=position, location=location)
        if user:
            db.session.delete(user)
            db.session.commit()

    def user_exists(self, email, position, location):
        return (User.query
                .filter_by(email=email, position=position, location=location).one_or_none())

    def get_new_users(self):
        return User.query.filter_by(is_new=True).all()

    def mark_user_as_not_new(self, email):
        user = User.query.filter_by(email=email).one_or_none()
        if user:
            user.is_new = False
            db.session.commit()

    def get_all_users(self):
        return User.query.all()


class UserEmailManager:
    def add_sent_email(self, email, job_url, position, location):
        user = SentEmail(email=email, job_url=job_url, position=position, location=location)
        db.session.add(user)
        db.session.commit()

    def is_sent(self, email, job_url, position, location):
        return SentEmail.query.filter_by(email=email, job_url=job_url, position=position,
                                         location=location).count() > 0
