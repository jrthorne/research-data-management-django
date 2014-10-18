from django.contrib import admin
from models import *

class ServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'status']
# end ServerAdmin

class RDSlogAdmin(admin.ModelAdmin):
    list_display = ['run_date', 'plan', 'import_file_name']
    list_filter = ['plan']
    list_per_page = 20

# Register your models here.
admin.site.register(Server, ServerAdmin)
admin.site.register(Check)
admin.site.register(RDSlog, RDSlogAdmin)
