# Generated migration for Explanation model and Answer.explanation field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Quizez', '0009_alter_aiquestiondraft_provider'),
    ]

    operations = [
        migrations.CreateModel(
            name='Explanation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary', models.TextField(blank=True)),
                ('resources', models.JSONField(default=list, help_text='List of {title, url} links')),
                ('provider', models.CharField(blank=True, max_length=32)),
                ('helpful', models.PositiveIntegerField(default=0)),
                ('not_helpful', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='explanations', to='Quizez.question')),
            ],
        ),
        migrations.AddIndex(
            model_name='explanation',
            index=models.Index(fields=['question', 'created_at'], name='Quizez_expl_questio_idx'),
        ),
        migrations.AddField(
            model_name='answer',
            name='explanation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='answers', to='Quizez.explanation'),
        ),
    ]
