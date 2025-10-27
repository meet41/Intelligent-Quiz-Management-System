from django.db import models
from django.contrib.auth.models import User
from PIL import Image
import os
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        # Check if this is a new profile without an image
        if not self.image:
            self.image = None

        super().save(*args, **kwargs)

        if self.image:
            try:
                # Only process the image if it exists on disk
                img_path = self.image.path
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    if img.height > 300 or img.width > 300:
                        output_size = (300, 300)
                        img.thumbnail(output_size)
                        img.save(img_path)
            except Exception as e:
                print(f"Error processing profile image: {e}")
                # Reset image field if file doesn't exist
                if not os.path.exists(self.image.path):
                    self.image = None
                    self.save(update_fields=['image'])

    @property
    def image_url(self):
        if self.image and hasattr(self.image, 'url') and os.path.exists(self.image.path):
            return self.image.url
        # Return a static fallback image
        return os.path.join(settings.STATIC_URL, 'img/default-profile.png')
