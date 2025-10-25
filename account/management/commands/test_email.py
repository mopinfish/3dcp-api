from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Test email configuration'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Recipient email address')

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        try:
            send_mail(
                subject='テストメール - 3DCP',
                message='これはテストメールです。メール設定が正しく動作しています。',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ テストメールを {recipient} に送信しました')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ メール送信エラー: {str(e)}')
            )