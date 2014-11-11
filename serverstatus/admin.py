from django.contrib import admin
from models import *

class ServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'status']
# end ServerAdmin

class RDSlogAdmin(admin.ModelAdmin):
    list_display = ['id', 'run_date', 'plan', 'space', 'import_file_name']
    list_filter = ['plan']
    list_per_page = 20

class Rdmp_infoAdmin(admin.ModelAdmin):
    list_display = ['id', 'rdmp_id', 'estimated_volume', 'storage_namespace']
    list_per_page = 20
    
# Register your models here.
admin.site.register(Server, ServerAdmin)
admin.site.register(Check)
admin.site.register(RDSlog, RDSlogAdmin)
admin.site.register(Rdmp_info, Rdmp_infoAdmin)
