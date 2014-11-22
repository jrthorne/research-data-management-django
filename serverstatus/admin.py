from django.contrib import admin
from models import *
############################################
class serverAdmin(admin.ModelAdmin):
    list_display = ['name', 'status']
# end ServerAdmin

############################################
class rds_logAdmin(admin.ModelAdmin):
    list_display    = ['run_date', 'plan', 'space', 'import_file_name']
    list_filter     = ['plan']
    list_per_page   = 20

############################################
class rdmp_infoAdmin(admin.ModelAdmin):
    list_display    = ['rdmp_id', 'estimated_volume', 'storage_namespace']
    list_per_page   = 20

############################################
class user_access_admin(admin.ModelAdmin):
    list_display    = ['zid', 'first_access', 'last_access']
    list_filter     = ['first_access', 'last_access']
    list_per_page   = 20
    
############################################
# Register your models here.
admin.site.register(Server, serverAdmin)
admin.site.register(Check)
admin.site.register(Rds_log, rds_logAdmin)
admin.site.register(Rdmp_info, rdmp_infoAdmin)
admin.site.register(User_access, user_access_admin)
