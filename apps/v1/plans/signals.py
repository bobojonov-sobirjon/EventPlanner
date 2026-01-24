from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Plan, PlanUser


@receiver(post_save, sender=Plan)
def ensure_creator_approved(sender, instance, created, **kwargs):
    """
    Signal handler to ensure that the plan creator always has APPROVED status.
    This runs whenever a Plan is saved, but only creates/updates PlanUser for new plans.
    """
    if created:
        # Plan yangi yaratilgan bo'lsa, creator uchun PlanUser yaratish yoki yangilash
        plan_user, plan_user_created = PlanUser.objects.get_or_create(
            plan=instance,
            user=instance.user,
            defaults={
                'status': PlanUser.Status.APPROVED
            }
        )
        # Agar PlanUser allaqachon mavjud bo'lsa, status'ni APPROVED qilish (creator har doim APPROVED bo'lishi kerak)
        if not plan_user_created:
            plan_user.status = PlanUser.Status.APPROVED
            plan_user.save(update_fields=['status', 'updated_at'])
