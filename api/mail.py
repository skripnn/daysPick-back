class Mail:

    @classmethod
    def get_sender(cls, name=None):
        if not name:
            name = 'no-reply'
        return f'DaysPick <{name}@dayspick.ru>'

    @classmethod
    def send(cls, theme=None, body=None, sender=None, to=None):
        from django.core.mail import send_mail
        if isinstance(to, str):
            to = [to]
        try:
            send_mail(theme, body, cls.get_sender(sender), to)
        except Exception as e:
            print(f'SEND MAIL ERROR: {e}')
