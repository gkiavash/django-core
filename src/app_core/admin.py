from django.contrib import admin


class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'uuid',
        'name',
        'modified',
        'state',
        'runtime_state',
        'backend_id',
        # 'error_message',
    )
    # search_fields = ('uuid', )
    readonly_fields = ('uuid',)
