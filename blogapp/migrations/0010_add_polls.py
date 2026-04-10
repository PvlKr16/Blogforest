from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('blogapp', '0009_post_and_quote_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(verbose_name='Question')),
                ('is_anonymous', models.BooleanField(default=False, verbose_name='Anonymous poll')),
                ('multiple_choice', models.BooleanField(default=False, verbose_name='Multiple answers allowed')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('blog', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='poll',
                    to='blogapp.blog',
                    verbose_name='Topic',
                )),
            ],
            options={'verbose_name': 'Poll', 'verbose_name_plural': 'Polls'},
        ),
        migrations.CreateModel(
            name='PollOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=500, verbose_name='Option text')),
                ('order', models.PositiveIntegerField(default=0)),
                ('poll', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='options',
                    to='blogapp.poll',
                )),
            ],
            options={'verbose_name': 'Poll option', 'verbose_name_plural': 'Poll options', 'ordering': ['order', 'id']},
        ),
        migrations.CreateModel(
            name='PollVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voted_at', models.DateTimeField(auto_now_add=True)),
                ('option', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='votes',
                    to='blogapp.polloption',
                )),
                ('poll', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='votes',
                    to='blogapp.poll',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='poll_votes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Poll vote', 'verbose_name_plural': 'Poll votes'},
        ),
        migrations.AddConstraint(
            model_name='pollvote',
            constraint=models.UniqueConstraint(
                fields=['poll', 'user', 'option'],
                name='unique_poll_user_option',
            ),
        ),
    ]
