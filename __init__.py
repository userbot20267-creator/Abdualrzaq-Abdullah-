"""
📦 Handlers Package - تسجيل جميع الـ Handlers
"""


def register_all_handlers(app):
    """تسجيل جميع handlers في التطبيق"""
    from handlers.start import register_start_handlers
    from handlers.channels import register_channel_handlers
    from handlers.content import register_content_handlers
    from handlers.quiz_poll import register_quiz_poll_handlers
    from handlers.ai_handler import register_ai_handlers
    from handlers.queue_handler import register_queue_handlers
    from handlers.schedule import register_schedule_handlers
    from handlers.post_now import register_post_now_handlers
    from handlers.admin import register_admin_handlers

    register_start_handlers(app)
    register_channel_handlers(app)
    register_content_handlers(app)
    register_quiz_poll_handlers(app)
    register_ai_handlers(app)
    register_queue_handlers(app)
    register_schedule_handlers(app)
    register_post_now_handlers(app)
    register_admin_handlers(app)